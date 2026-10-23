"""Relatório de Preservação e Integridade em PDF.

Estrutura pensada para quem lê, não para quem processa:

    Capa (com o resultado geral)
    Resumo + "Como ler este relatório"
    1. Caso e origem dos arquivos
    2. Integridade e data (carimbo de tempo, como conferir, recorte)
    3. Conferência dos prints
    4. Mensagens
    5. Metodologia aplicada (passo a passo, ferramentas, limitações,
       glossário e aviso)
    Apêndices: arquivos e impressões digitais; registro das operações
"""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    CondPageBreak,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from lexproof import __version__
from lexproof.reports.text import local_time, person_name, safe_text

logger = logging.getLogger("lexproof.reports.pdf")

# Compatibilidade com quem importava daqui.
_safe = safe_text
_fmt_local = local_time

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 2.2 * cm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN

INK = colors.HexColor("#1f2430")
MUTED = colors.HexColor("#5f6368")
LINE = colors.HexColor("#dfe3ea")
SURFACE = colors.HexColor("#f5f7fb")
PRIMARY = colors.HexColor("#1a237e")
PRIMARY_SOFT = colors.HexColor("#e8eaf6")
OK = colors.HexColor("#2e7d32")
OK_SOFT = colors.HexColor("#e8f5e9")
WARN = colors.HexColor("#9a5b00")
WARN_SOFT = colors.HexColor("#fff4e5")
BAD = colors.HexColor("#c62828")
BAD_SOFT = colors.HexColor("#fdecea")
KINDS = {
    "ok": (OK, OK_SOFT), "warn": (WARN, WARN_SOFT), "bad": (BAD, BAD_SOFT),
    "info": (PRIMARY, PRIMARY_SOFT), "neutral": (MUTED, SURFACE),
}

DISCLAIMER = (
    "Documento gerado automaticamente por software. Não constitui laudo pericial, "
    "ata notarial nem certificação de autenticidade. Registra o processamento "
    "realizado e permite sua verificação independente."
)

# Resultado de cada balão: (etiqueta, tipo de cor)
STATUS_PILL = {
    "confere": ("CONFERE", "ok"),
    "confere_sem_horario": ("CONFERE*", "ok"),
    "nao_conferido": ("NÃO CONFERIDO", "neutral"),
    "horario_divergente": ("HORÁRIO DIFERENTE", "bad"),
    "data_divergente": ("DATA DIFERENTE", "bad"),
    "texto_divergente": ("TEXTO DIFERENTE", "bad"),
    "nao_encontrada": ("NÃO ENCONTRADA", "bad"),
}

_FONT = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_FONT_MONO = "Courier"


def _register_fonts() -> None:
    """Noto Sans quando instalada (acentos e símbolos melhores); senão Helvetica."""
    global _FONT, _FONT_BOLD, _FONT_MONO
    base = Path("/usr/share/fonts/noto")
    files = {
        "LP-Sans": base / "NotoSans-Regular.ttf",
        "LP-Sans-Bold": base / "NotoSans-Bold.ttf",
        "LP-Sans-Italic": base / "NotoSans-Italic.ttf",
        "LP-Mono": base / "NotoSansMono-Regular.ttf",
    }
    if not all(f.exists() for f in files.values()):
        return
    try:
        for name, path in files.items():
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(path)))
        pdfmetrics.registerFontFamily(
            "LP-Sans", normal="LP-Sans", bold="LP-Sans-Bold", italic="LP-Sans-Italic",
            boldItalic="LP-Sans-Bold",
        )
        _FONT, _FONT_BOLD, _FONT_MONO = "LP-Sans", "LP-Sans-Bold", "LP-Mono"
    except Exception as exc:  # fonte corrompida: segue com Helvetica
        logger.warning("Noto Sans indisponível: %s", exc)


def _esc(text: Any) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _styles() -> dict[str, ParagraphStyle]:
    def st(name: str, **kw: Any) -> ParagraphStyle:
        base = dict(fontName=_FONT, fontSize=9.5, leading=13.5, textColor=INK, alignment=TA_LEFT)
        base.update(kw)
        return ParagraphStyle(name, **base)

    return {
        "cover_title": st("cover_title", fontName=_FONT_BOLD, fontSize=24, leading=29, textColor=colors.white),
        "cover_sub": st("cover_sub", fontSize=11, leading=15, textColor=colors.HexColor("#c5cae9")),
        "h1": st("h1", fontName=_FONT_BOLD, fontSize=16, leading=20, textColor=PRIMARY),
        "h2": st("h2", fontName=_FONT_BOLD, fontSize=11.5, leading=15, textColor=INK, spaceBefore=6, spaceAfter=4),
        "lead": st("lead", fontSize=10, leading=14.5, textColor=MUTED, spaceAfter=8),
        "body": st("body", spaceAfter=5),
        "small": st("small", fontSize=8, leading=11, textColor=MUTED),
        "cell": st("cell", fontSize=8, leading=10.5),
        "cell_head": st("cell_head", fontName=_FONT_BOLD, fontSize=7.5, leading=10, textColor=PRIMARY),
        "label": st("label", fontName=_FONT_BOLD, fontSize=8, leading=11, textColor=MUTED),
        "mono": st("mono", fontName=_FONT_MONO, fontSize=7.5, leading=10.5),
        "callout_title": st("callout_title", fontName=_FONT_BOLD, fontSize=9.5, leading=13),
        "pill": st("pill", fontName=_FONT_BOLD, fontSize=7, leading=9, alignment=TA_CENTER),
        "step_no": st("step_no", fontName=_FONT_BOLD, fontSize=10, leading=13, textColor=colors.white, alignment=TA_CENTER),
    }


class _NumberedCanvas(rl_canvas.Canvas):
    """Canvas que conhece o total de páginas ("Página 3 de 12")."""

    footer_title = ""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._pages: list[dict[str, Any]] = []

    def showPage(self) -> None:  # noqa: N802
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._pages)
        for state in self._pages:
            self.__dict__.update(state)
            self._footer(total)
            super().showPage()
        super().save()

    def _footer(self, total: int) -> None:
        self.saveState()
        self.setStrokeColor(LINE)
        self.setLineWidth(0.6)
        self.line(MARGIN, 1.55 * cm, PAGE_WIDTH - MARGIN, 1.55 * cm)
        self.setFillColor(MUTED)
        self.setFont(_FONT, 7.5)
        if self._pageNumber > 1:
            self.drawString(MARGIN, 1.15 * cm, f"Relatório de Preservação e Integridade · {self.footer_title}"[:110])
            self.drawRightString(PAGE_WIDTH - MARGIN, 1.15 * cm, f"Página {self._pageNumber} de {total}")
        self.setFont(_FONT, 6.3)
        first, _, second = DISCLAIMER.partition(" Registra")
        self.drawCentredString(PAGE_WIDTH / 2, 0.8 * cm, first)
        self.drawCentredString(PAGE_WIDTH / 2, 0.5 * cm, "Registra" + second)
        self.restoreState()


class PDFReportGenerator:
    """Gera o Relatório de Preservação e Integridade."""

    def __init__(self) -> None:
        _register_fonts()
        self.S = _styles()

    # ------------------------------------------------------------------ #
    # Componentes
    # ------------------------------------------------------------------ #

    def _p(self, text: str, style: str = "body") -> Paragraph:
        return Paragraph(text, self.S[style])

    def _section(self, story: list[Any], number: str, title: str, lead: str) -> None:
        story.append(CondPageBreak(6 * cm))
        badge = Table([[self._p(number, "step_no")]], colWidths=[0.9 * cm], rowHeights=[0.9 * cm])
        badge.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ]))
        head = Table([[badge, self._p(title, "h1")]], colWidths=[1.3 * cm, CONTENT_WIDTH - 1.3 * cm])
        head.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story += [head, Spacer(1, 0.25 * cm), self._p(lead, "lead")]

    def _callout(self, kind: str, text: str, title: str = "") -> Table:
        fg, bg = KINDS[kind]
        content: list[Any] = []
        if title:
            content.append(Paragraph(f'<font color="{fg.hexval()}">{title}</font>', self.S["callout_title"]))
        content.append(self._p(text))
        t = Table([[content]], colWidths=[CONTENT_WIDTH])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("LINEBEFORE", (0, 0), (0, -1), 3, fg),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        return t

    def _pill(self, text: str, kind: str) -> Table:
        fg, bg = KINDS[kind]
        t = Table([[Paragraph(f'<font color="{fg.hexval()}">{_esc(text)}</font>', self.S["pill"])]])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("ROUNDEDCORNERS", [6, 6, 6, 6]),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    def _kv(self, rows: list[tuple[str, Any]], label_width: float = 4.6 * cm, width: float = CONTENT_WIDTH) -> Table:
        data = [[self._p(_esc(k), "label"), v if not isinstance(v, str) else self._p(v, "cell")] for k, v in rows]
        t = Table(data, colWidths=[label_width, width - label_width])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ]))
        return t

    def _table(self, header: list[str], rows: list[list[Any]], widths: list[float]) -> Table:
        data = [[self._p(_esc(h), "cell_head") for h in header]]
        for row in rows:
            data.append([c if not isinstance(c, str) else self._p(c, "cell") for c in row])
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_SOFT),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SURFACE]),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, PRIMARY),
            ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    def _commands(self, lines: list[str]) -> Table:
        t = Table([[self._p("<br/>".join(_esc(x) for x in lines), "mono")]], colWidths=[CONTENT_WIDTH])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f3f4")),
            ("BOX", (0, 0), (-1, -1), 0.4, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return t

    def _thumb(self, path: Path, max_w: float, max_h: float) -> Any:
        try:
            from PIL import Image as PILImage

            with PILImage.open(path) as im:
                w, h = im.size
            scale = min(max_w / w, max_h / h)
            img = Image(str(path), width=w * scale, height=h * scale)
            frame = Table([[img]])
            frame.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, LINE), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
            return frame
        except Exception as exc:
            return self._p(f"Miniatura indisponível ({_esc(exc)})", "small")

    # ------------------------------------------------------------------ #
    # Resultado geral (capa e resumo)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _problems(d: dict[str, Any]) -> list[str]:
        checks = d.get("screenshot_checks") or []
        st = d.get("stitch")
        out = []
        if any(not c.all_ok for c in checks):
            out.append("divergência entre prints e conversa")
        if st is not None and st.order and st.needs_attention(bool(checks)):
            out.append("lacuna ou contradição entre prints")
        if any(not e.verified for e in d.get("emails") or []):
            out.append("e-mail sem assinatura válida")
        if any(not c.ok for c in d.get("contacts") or []):
            out.append("perfil de contato divergente")
        return out

    def _verdict(self, d: dict[str, Any]) -> tuple[str, str, str]:
        problems = self._problems(d)
        seal = d.get("seal")
        if problems:
            return "bad", "Há pontos a examinar", "Encontrado: " + "; ".join(problems) + "."
        if seal is None or seal.timestamp is None:
            return "warn", "Sem divergências, mas sem carimbo de tempo", (
                "A data da preservação não está atestada por terceiro.")
        return "ok", "Sem divergências", "Tudo o que foi conferido está coerente."

    # ------------------------------------------------------------------ #
    # Geração
    # ------------------------------------------------------------------ #

    def generate(self, case_data: dict[str, Any], output_path: Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        meta = case_data.get("metadata", {})
        title = str(meta.get("title") or "Caso de Preservação")
        doc = SimpleDocTemplate(
            str(output_path), pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN, topMargin=1.8 * cm, bottomMargin=2.1 * cm,
            title=f"Relatório de Preservação e Integridade - {title}", author="LexProof",
        )
        story: list[Any] = []
        self._cover(story, case_data)
        self._summary(story, case_data)
        self._case(story, case_data)
        self._integrity(story, case_data)
        self._prints(story, case_data)
        self._messages(story, case_data)
        self._methodology(story, case_data)
        self._appendices(story, case_data)

        canvas_cls = type("_Canvas", (_NumberedCanvas,), {"footer_title": safe_text(title)})
        doc.build(story, canvasmaker=canvas_cls)
        logger.info("Relatório de preservação gerado: %s", output_path)
        return output_path

    # ------------------------------------------------------------------ #
    # Capa
    # ------------------------------------------------------------------ #

    def _cover(self, story: list[Any], d: dict[str, Any]) -> None:
        meta = d.get("metadata", {})
        band = Table([[[
            self._p("RELATÓRIO DE PRESERVAÇÃO<br/>E INTEGRIDADE", "cover_title"),
            Spacer(1, 0.3 * cm),
            self._p("Registro do recebimento e da conferência de conversas do WhatsApp, "
                    "verificável de forma independente", "cover_sub"),
        ]]], colWidths=[CONTENT_WIDTH])
        band.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
            ("LEFTPADDING", (0, 0), (-1, -1), 22),
            ("TOPPADDING", (0, 0), (-1, -1), 26),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 26),
            ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ]))
        story += [Spacer(1, 1.2 * cm), band, Spacer(1, 1.0 * cm)]

        seal = d.get("seal")
        stamped = seal is not None and seal.timestamp is not None
        rows = [
            ("Caso", _esc(safe_text(meta.get("title", "-")))),
            ("Responsável pela preservação", _esc(safe_text(meta.get("examiner", "-")))),
        ]
        if meta.get("received_via"):
            rows.append(("Origem dos arquivos", _esc(meta["received_via"])))
        rows += [
            ("Preservado em", local_time(seal.timestamp.gen_time, with_utc=False) + " (carimbo de tempo)"
             if stamped else local_time(datetime.now(timezone.utc), with_utc=False) + " (sem carimbo)"),
            ("Número do relatório", _esc(meta.get("case_id", "-"))),
            ("Versão do LexProof", __version__),
        ]
        story += [self._kv(rows, label_width=5.2 * cm), Spacer(1, 1.0 * cm)]

        kind, head, text = self._verdict(d)
        fg, bg = KINDS[kind]
        verdict = Table([[
            [Paragraph(f'<font color="{fg.hexval()}">RESULTADO</font>', self.S["label"]),
             Paragraph(f'<font color="{fg.hexval()}" size="15"><b>{head}</b></font>', self.S["body"]),
             Spacer(1, 0.15 * cm), self._p(text)],
        ]], colWidths=[CONTENT_WIDTH])
        verdict.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX", (0, 0), (-1, -1), 1, fg),
            ("ROUNDEDCORNERS", [8, 8, 8, 8]),
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ]))
        story += [verdict, Spacer(1, 1.2 * cm), self._p(
            "Os detalhes de cada conferência estão nas Seções 1 a 4. Como o trabalho foi feito, "
            "e o que este relatório não afirma, estão na Seção 5.", "small"), PageBreak()]

    # ------------------------------------------------------------------ #
    # Resumo
    # ------------------------------------------------------------------ #

    def _summary(self, story: list[Any], d: dict[str, Any]) -> None:
        story += [self._p("Resumo", "h1"), Spacer(1, 0.2 * cm),
                  self._p("O que este relatório registra, em poucas linhas.", "lead")]
        for kind, title, text in self._summary_points(d):
            story += [self._callout(kind, text, title), Spacer(1, 0.2 * cm)]

        story += [Spacer(1, 0.4 * cm), self._p("Como ler este relatório", "h2")]
        guide = [
            ("Impressão digital (SHA-256)",
             "Código calculado a partir do conteúdo de um arquivo. Se um único byte mudar, o "
             "código muda por completo. Por isso ele identifica o arquivo exato que foi recebido."),
            ("Carimbo de tempo",
             "Uma entidade independente (Autoridade de Carimbo do Tempo) assina as impressões "
             "digitais com a data e a hora. Isso prova que os arquivos já existiam, exatamente "
             "assim, naquele momento. Ela recebe só os códigos, nunca o conteúdo."),
            ("Conferência dos prints",
             "Cada mensagem visível nos prints é lida e procurada na conversa exportada do "
             "WhatsApp (e nos demais prints). Diferenças de texto, data, hora ou ordem são apontadas."),
        ]
        rows = [[self._p(f"<b>{t}</b>", "cell"), self._p(x, "cell")] for t, x in guide]
        t = Table(rows, colWidths=[4.4 * cm, CONTENT_WIDTH - 4.4 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SURFACE),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story += [t, PageBreak()]

    def _summary_points(self, d: dict[str, Any]) -> list[tuple[str, str, str]]:
        points: list[tuple[str, str, str]] = []
        seal = d.get("seal")
        if seal is not None:
            received = sum(1 for _, rel in seal.files if not rel.startswith("preservacao/"))
            if seal.timestamp is not None:
                points.append(("ok", "Arquivos registrados e carimbados",
                    f"{received} arquivo(s) recebido(s) tiveram a impressão digital registrada e "
                    f"carimbada por terceiro em <b>{local_time(seal.timestamp.gen_time, with_utc=False)}</b>. "
                    f"Qualquer pessoa pode conferir que não mudaram desde então (Seção 2)."))
            else:
                points.append(("warn", "Carimbo de tempo não obtido",
                    f"{received} arquivo(s) tiveram a impressão digital registrada, mas a data da "
                    f"preservação não está atestada por terceiro (Seção 2)."))
        for em in d.get("emails") or []:
            if em.verified:
                points.append(("ok", "Origem atestada pelo provedor de e-mail",
                    f"O e-mail de <b>{_esc(safe_text(em.sender))}</b> trouxe {len(em.attachments)} "
                    f"anexo(s) com assinatura válida de <b>{_esc(em.aligned_signature.domain)}</b>: os "
                    f"anexos são os mesmos que saíram dessa conta (Seção 1)."))
            else:
                points.append(("bad", "E-mail sem assinatura válida",
                    f"{_esc(em.eml_path.name)} não comprova a origem dos anexos (Seção 1)."))
        for link in d.get("contacts") or []:
            p = link.profile
            if link.ok:
                points.append(("ok", "Contato identificado",
                    f"<b>{_esc(person_name(p.name))}</b> corresponde ao número <b>{_esc(p.phone)}</b>, "
                    f"conforme o print do perfil (Seção 3)."))
            else:
                points.append(("bad", "Perfil de contato divergente",
                    f"O perfil {_esc(person_name(p.name)) or '?'} ({_esc(p.phone)}) não confere com o "
                    f"contato da conversa (Seção 3)."))
        ex = d.get("excerpt")
        if ex is not None:
            fate = ("o restante foi apagado, ficando só a impressão digital do arquivo completo"
                    if ex.discarded else "a conversa completa ficou guardada, lacrada, fora do relatório")
            points.append(("info", "Conversa limitada a um período",
                f"De {ex.start:%d/%m/%Y} a {ex.end:%d/%m/%Y} ({ex.kept_messages} de "
                f"{ex.total_messages} mensagens); {fate} (Seção 2)."))
        checks = d.get("screenshot_checks") or []
        if checks:
            total = sum(c.total for c in checks)
            confirmed = sum(c.confirmed for c in checks)
            bad = [c for c in checks if not c.all_ok]
            if bad:
                names = ", ".join(_esc(c.reading.path.name) for c in bad)
                points.append(("bad", "Há divergências nos prints",
                    f"{confirmed} de {total} mensagens visíveis conferem com a conversa exportada. "
                    f"Examinar: {names} (Seção 3)."))
            else:
                points.append(("ok", "Prints conferem com a conversa",
                    f"As <b>{total} mensagens</b> visíveis em {len(checks)} print(s) conferem com a "
                    f"conversa exportada em texto, data e hora (Seção 3)."))
        st = d.get("stitch")
        if st is not None and st.order and not checks:
            if st.all_ok:
                points.append(("ok", "Prints se encadeiam",
                    f"Sem exportação, os {len(st.order)} prints foram conferidos entre si: sem "
                    f"lacunas nem contradições (Seção 3)."))
            else:
                points.append(("bad", "Prints conferidos entre si: pontos a examinar",
                    f"{len(st.gaps)} lacuna(s), {len(st.contradictions)} contradição(ões) e "
                    f"{len(st.warnings)} incoerência(s) entre os {len(st.order)} prints (Seção 3)."))
        if not points:
            points.append(("neutral", "Nada a conferir", "Nenhum arquivo reconhecido."))
        return points

    # ------------------------------------------------------------------ #
    # 1. Caso e origem
    # ------------------------------------------------------------------ #

    def _case(self, story: list[Any], d: dict[str, Any]) -> None:
        meta = d.get("metadata", {})
        self._section(story, "1", "Caso e origem dos arquivos",
                      "Quem preservou, de onde vieram os arquivos e o que foi recebido.")
        rows = [
            ("Caso", _esc(safe_text(meta.get("title", "-")))),
            ("Responsável pela preservação", _esc(safe_text(meta.get("examiner", "-")))),
        ]
        if meta.get("received_via"):
            rows.append(("Origem dos arquivos", _esc(meta["received_via"])))
        rows.append(("Número do relatório", _esc(meta.get("case_id", "-"))))
        story += [self._kv(rows), Spacer(1, 0.4 * cm)]

        seal = d.get("seal")
        if seal is not None:
            received = [(digest, rel) for digest, rel in seal.files if not rel.startswith("preservacao/")]
            story.append(self._p("Arquivos recebidos", "h2"))
            story.append(self._table(
                ["Arquivo", "Impressão digital (SHA-256)"],
                [[_esc(Path(rel).name), self._p(digest, "mono")] for digest, rel in received],
                [6.5 * cm, CONTENT_WIDTH - 6.5 * cm],
            ))
            story.append(Spacer(1, 0.4 * cm))

        for em in d.get("emails") or []:
            story.append(KeepTogether(self._email_block(em)))
            story.append(Spacer(1, 0.3 * cm))

    def _email_block(self, em: Any) -> list[Any]:
        sig = em.aligned_signature or (em.signatures[0] if em.signatures else None)
        if em.verified:
            pill = self._pill(f"ASSINATURA VÁLIDA · {sig.domain}", "ok")
        elif sig is not None and sig.valid:
            pill = self._pill(f"ASSINADO POR OUTRO DOMÍNIO · {sig.domain}", "bad")
        else:
            pill = self._pill("SEM ASSINATURA VÁLIDA", "bad")
        rows = [
            ("Remetente", _esc(safe_text(em.sender))),
            ("Destinatário", _esc(safe_text(em.to))),
            ("Enviado em", local_time(em.date) if em.date else "-"),
            ("Assunto", _esc(safe_text(em.subject)) or "-"),
            ("Assinatura do provedor (DKIM)", pill),
            ("Anexos", ", ".join(_esc(a.name) for a in em.attachments) or "-"),
        ]
        out: list[Any] = [self._p(f"E-mail recebido: {_esc(em.eml_path.name)}", "h2"), self._kv(rows)]
        out.append(Spacer(1, 0.15 * cm))
        if em.verified:
            out.append(self._p(
                "O servidor do remetente assinou a mensagem, anexos incluídos. Assinatura válida "
                "significa que remetente, data, assunto e anexos estão exatamente como saíram dali. "
                "A chave pública do provedor, consultada no momento da preservação, foi arquivada em "
                "preservacao/dkim-chaves.txt (dentro do carimbo), para que a conferência possa ser "
                "refeita mesmo depois que o provedor trocar a chave.", "small"))
        else:
            out.append(self._callout("bad",
                "Sem assinatura válida do domínio do remetente, o e-mail não comprova a origem dos "
                "anexos. Isso acontece quando ele foi encaminhado, salvo de forma diferente do "
                "original (\"Baixar original\" no Gmail) ou alterado."))
        return out

    # ------------------------------------------------------------------ #
    # 2. Integridade e data
    # ------------------------------------------------------------------ #

    def _integrity(self, story: list[Any], d: dict[str, Any]) -> None:
        seal = d.get("seal")
        self._section(story, "2", "Integridade e data",
                      "Prova de que os arquivos não mudaram desde a preservação, e como qualquer "
                      "pessoa pode conferir isso sem depender do LexProof.")
        if seal is None:
            story.append(self._callout("warn", "Esta preservação não gerou manifesto nem carimbo de tempo."))
            return
        ts = seal.timestamp
        rows = [("Manifesto", f"{seal.seal_dir.name}/{seal.manifest_path.name} (lista das impressões digitais)"),
                ("Impressão digital do manifesto", self._p(seal.manifest_sha256, "mono"))]
        if ts is not None:
            rows += [("Carimbo emitido por", _esc(ts.tsa_url)),
                     ("Horário atestado", local_time(ts.gen_time)),
                     ("Número de série", _esc(ts.serial))]
        story += [self._kv(rows), Spacer(1, 0.3 * cm)]
        if ts is not None:
            story.append(self._callout("ok",
                f"Os arquivos listados no manifesto já existiam, exatamente como estão, em "
                f"<b>{local_time(ts.gen_time, with_utc=False)}</b>. Qualquer alteração posterior, mesmo "
                f"de um único byte, faz a conferência abaixo falhar.", "O que o carimbo prova"))
        else:
            story.append(self._callout("warn",
                f"Carimbo de tempo não obtido{': ' + _esc(seal.timestamp_error) if seal.timestamp_error else ''}. "
                f"O manifesto comprova a integridade a partir do momento em que for entregue a um "
                f"terceiro, mas não a data desta preservação.", "Sem carimbo de tempo"))

        story += [Spacer(1, 0.3 * cm), self._p("Como qualquer pessoa confere", "h2"), self._p(
            "A pasta <b>preservacao</b> do caso contém o manifesto, o carimbo, os certificados públicos "
            "da autoridade de carimbo e o arquivo COMO_VERIFICAR.txt. Com um terminal aberto na pasta "
            "do caso:")]
        cmds = ["# 1. os arquivos são os mesmos do manifesto (cada linha deve terminar em OK)",
                f"sha256sum -c preservacao/{seal.manifest_path.name}"]
        if ts is not None and seal.verify_command:
            cmds += ["", "# 2. o manifesto já existia na data do carimbo (deve responder Verification: OK)",
                     "cd preservacao", seal.verify_command]
        story += [self._commands(cmds), Spacer(1, 0.3 * cm)]

        ex = d.get("excerpt")
        if ex is not None:
            story += [self._p("Recorte do período de interesse", "h2"), self._p(
                f"O relatório foi limitado a <b>{ex.start:%d/%m/%Y} a {ex.end:%d/%m/%Y}</b> "
                f"({ex.kept_messages} de {ex.total_messages} mensagens). Como a exportação é "
                f"cronológica, essas mensagens são as linhas {ex.first_line} a {ex.last_line} do "
                f"arquivo, copiadas byte a byte. " + (
                    "Por privacidade, a conversa completa foi <b>apagada</b> da pasta do caso; "
                    "ficaram as impressões digitais do arquivo completo." if ex.discarded else
                    "A conversa completa está guardada, lacrada, na pasta do caso."))]
            rows = []
            if ex.source_zip:
                rows.append((f"ZIP completo ({_esc(ex.source_zip)})", self._p(ex.source_zip_sha256, "mono")))
            rows += [(f"Conversa completa ({_esc(ex.source_txt)})", self._p(ex.source_txt_sha256, "mono")),
                     (f"Recorte (linhas {ex.first_line} a {ex.last_line})", self._p(ex.excerpt_sha256, "mono"))]
            story += [self._kv(rows, label_width=6.5 * cm), Spacer(1, 0.2 * cm),
                      self._p("Quem tiver a conversa completa (o cliente ou um perito) confere que o recorte "
                              "é fiel, sem nada tirado do meio:"),
                      self._commands([ex.verify_command])]
            if ex.discarded:
                story += [Spacer(1, 0.2 * cm), self._callout("warn",
                    "Como o restante foi apagado, essa conferência depende de alguém ainda ter o arquivo "
                    "completo. Recomende ao cliente guardar a conversa no celular ou o arquivo exportado.")]
            if ex.retained_in:
                story += [Spacer(1, 0.2 * cm), self._callout("info",
                    f"O e-mail original ({_esc(ex.retained_in)}) contém a conversa completa como anexo e "
                    f"foi mantido, porque é a prova da origem dos arquivos.")]

    # ------------------------------------------------------------------ #
    # 3. Conferência dos prints
    # ------------------------------------------------------------------ #

    def _prints(self, story: list[Any], d: dict[str, Any]) -> None:
        checks = d.get("screenshot_checks") or []
        st = d.get("stitch")
        links = d.get("contacts") or []
        if not checks and (st is None or not st.order) and not links:
            return
        story.append(PageBreak())
        self._section(story, "3", "Conferência dos prints",
                      "Cada mensagem visível nos prints foi lida e confrontada com a conversa "
                      "exportada do WhatsApp e com os demais prints.")
        legend = Table([[self._pill("CONFERE", "ok"), self._p("texto, data e hora iguais", "small"),
                         self._pill("DIVERGE", "bad"), self._p("texto, data ou hora diferentes, ou mensagem inexistente", "small"),
                         self._pill("NÃO CONFERIDO", "neutral"), self._p("cortado demais no print", "small")]],
                       colWidths=[1.8 * cm, 3.2 * cm, 1.8 * cm, 4.6 * cm, 2.6 * cm, 2.6 * cm])
        legend.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
        story += [legend, Spacer(1, 0.15 * cm), self._p(
            "Acentos, pontuação e pequenos erros de leitura do OCR (uma letra trocada, palavras "
            "grudadas) não contam como diferença e ficam anotados. Números diferentes e palavras "
            "a mais, a menos ou trocadas sempre contam.", "small"), Spacer(1, 0.3 * cm)]

        for link in links:
            story.append(KeepTogether(self._contact_block(link)))
            story.append(Spacer(1, 0.3 * cm))
        for idx, chk in enumerate(checks, start=1):
            self._print_block(story, idx, chk)
        if st is not None and st.order and (len(st.order) > 1 or not checks):
            self._stitch_block(story, st, with_export=bool(checks))

    def _contact_block(self, link: Any) -> list[Any]:
        p = link.profile
        rows = [("Print do perfil", _esc(p.path.name)),
                ("Nome no perfil", _esc(person_name(p.name)) or "não identificado"),
                ("Número de telefone", f"<b>{_esc(p.phone)}</b>")]
        if link.matches_export is not None:
            rows.append(("Contato na conversa exportada",
                         self._pill(("CONFERE · " if link.matches_export else "DIFERENTE · ")
                                    + person_name(link.export_contact)[:50], "ok" if link.matches_export else "bad")))
        if link.matches_prints is not None:
            rows.append(("Contato no topo dos prints",
                         self._pill(("CONFERE · " if link.matches_prints else "DIFERENTE · ")
                                    + person_name(link.print_contact)[:50], "ok" if link.matches_prints else "bad")))
        thumb = self._thumb(p.path, 3.2 * cm, 6.5 * cm)
        side = Table([[thumb, self._kv(rows, label_width=4.2 * cm, width=CONTENT_WIDTH - 4.2 * cm)]],
                     colWidths=[4.0 * cm, CONTENT_WIDTH - 4.0 * cm])
        side.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        return [self._p("Identificação do contato", "h2"), self._p(
            "A conversa exportada e o topo dos prints mostram apenas o nome salvo na agenda do celular. "
            "A tela de perfil do contato mostra esse nome junto do número de telefone.", "small"),
            Spacer(1, 0.15 * cm), side]

    def _print_block(self, story: list[Any], idx: int, chk: Any) -> None:
        r = chk.reading
        ok = chk.all_ok
        status = self._pill(f"{chk.confirmed} DE {chk.total} CONFEREM", "ok" if ok else "bad")
        rows = [("Resultado", status),
                ("Tirado em", (local_time(r.captured_at, with_utc=False) + f" ({r.captured_at_source})")
                 if r.captured_at else "não identificado"),
                ("Contato no topo", _esc(person_name(r.contact)) or "não identificado")]
        if chk.contact_matches is False:
            rows.append(("Contato", self._pill(f"DIFERENTE DA CONVERSA ({person_name(chk.export_contact)})", "bad")))
        if chk.captured_after_messages is False:
            rows.append(("Momento do print", self._pill("ANTERIOR A MENSAGENS QUE EXIBE", "bad")))
        rows.append(("Ordem das mensagens", "a mesma da conversa exportada" if chk.order_ok
                     else self._pill("DIFERENTE DA EXPORTAÇÃO", "bad")))
        thumb = self._thumb(r.path, 3.6 * cm, 7.5 * cm)
        side = Table([[thumb, self._kv(rows, label_width=3.6 * cm, width=CONTENT_WIDTH - 4.4 * cm)]],
                     colWidths=[4.4 * cm, CONTENT_WIDTH - 4.4 * cm])
        side.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        story += [CondPageBreak(9 * cm), self._p(f"Print {idx} · {_esc(r.path.name)}", "h2"), side, Spacer(1, 0.25 * cm)]

        rows = []
        for n, c in enumerate(chk.checks, start=1):
            b = c.bubble
            label, kind = STATUS_PILL.get(c.status.value, (c.status.label.upper(), "neutral"))
            text = "(ligação)" if b.kind == "call" else ("(documento) " if b.kind == "document" else "") + safe_text(b.text)
            if b.date:
                day = b.date.strftime("%d/%m/%Y")
            elif c.message is not None:
                day = f"({c.message.timestamp:%d/%m/%Y})"
            else:
                day = "—"
            rows.append([
                str(n),
                day,
                b.time or "?",
                _esc(text[:160]),
                self._pill(label, kind),
                str(c.message.line_number) if c.message else "—",
            ])
        story.append(self._table(["#", "Data", "Hora", "Mensagem no print", "Resultado", "Linha"], rows,
                                 [0.6 * cm, 2.25 * cm, 1.1 * cm, CONTENT_WIDTH - 8.75 * cm, 3.4 * cm, 1.4 * cm]))
        notes = [(n, note) for n, c in enumerate(chk.checks, start=1) for note in c.notes
                 if "Data deduzida" not in note]
        if notes:
            story.append(Spacer(1, 0.1 * cm))
            for n, note in notes:
                story.append(self._p(f"Mensagem {n}: {_esc(safe_text(note))}", "small"))
        if any("Data deduzida" in note for c in chk.checks for note in c.notes):
            story.append(self._p("Datas entre parênteses vêm da conversa exportada, porque o separador de "
                                 "data não aparece acima da mensagem no print.", "small"))
        if chk.hidden_messages:
            lines = "<br/>".join(
                f"{m.timestamp:%d/%m/%Y %H:%M} · {_esc(safe_text(m.content)[:90])}" for m in chk.hidden_messages[:12])
            story += [Spacer(1, 0.15 * cm), self._callout("bad",
                f"Estão na conversa exportada entre mensagens que aparecem no print, mas não aparecem nele:<br/>{lines}",
                "Mensagens omitidas no print")]
        if chk.hidden_media:
            story.append(self._p(f"{chk.hidden_media} mídia(s) do mesmo trecho não foram conferidas "
                                 f"(o OCR não lê imagens dentro do print).", "small"))
        story.append(Spacer(1, 0.45 * cm))

    def _stitch_block(self, story: list[Any], st: Any, with_export: bool) -> None:
        story += [CondPageBreak(6 * cm), self._p("Prints conferidos entre si", "h2"), self._p(
            "Ao rolar a tela entre um print e outro, prints vizinhos repetem algumas mensagens. Os "
            "prints foram ordenados pelo conteúdo e cada um foi comparado com o seguinte.", "small"),
            Spacer(1, 0.15 * cm)]
        gap_after = {g.after_print for g in st.gaps}
        rows = []
        for n, r in enumerate(st.order, start=1):
            own = [m for m in st.messages if r.path.name in m.sources]
            if n == 1:
                seq = self._pill("INÍCIO", "neutral")
            elif r.path.name in gap_after:
                seq = self._pill("TRECHO NÃO PRINTADO ANTES", "neutral") if with_export else self._pill("LACUNA ANTES", "bad")
            else:
                seq = self._pill("CONTINUA", "ok")
            rows.append([str(n), _esc(r.path.name), own[0].when if own else "-", own[-1].when if own else "-", seq])
        story.append(self._table(["#", "Print", "Primeira mensagem", "Última mensagem", "Sequência"], rows,
                                 [0.6 * cm, 5.4 * cm, 3.2 * cm, 3.2 * cm, CONTENT_WIDTH - 12.4 * cm]))
        story.append(Spacer(1, 0.2 * cm))
        for g in st.gaps:
            text = (f"Entre <b>{_esc(g.before_print)}</b> e <b>{_esc(g.after_print)}</b> há mensagens "
                    f"não capturadas ({g.last_before.when} a {g.first_after.when}).")
            if with_export:
                story.append(self._p(text + " Como cada print foi conferido com a conversa exportada, "
                                     "isso não indica problema.", "small"))
            else:
                story += [self._callout("bad", text + " Pode haver mensagens que não foram printadas.", "Lacuna"),
                          Spacer(1, 0.15 * cm)]
        for c in st.contradictions:
            diffs = "; ".join(f"“{a or '(nada)'}” x “{b or '(nada)'}”" for a, b in c.differences)
            story += [self._callout("bad",
                f"Na mensagem de {c.when}, <b>{_esc(c.print_a)}</b> mostra “{_esc(safe_text(c.text_a)[:90])}” e "
                f"<b>{_esc(c.print_b)}</b> mostra “{_esc(safe_text(c.text_b)[:90])}”. Diferença: {_esc(diffs)}.",
                "Contradição entre prints"), Spacer(1, 0.15 * cm)]
        for i in st.issues:
            if i.severity == "info":
                story.append(self._p(f"Observação sobre {_esc(i.print_name)}: {_esc(i.message)}.", "small"))
            else:
                story += [self._callout("bad", f"<b>{_esc(i.print_name)}</b>: {_esc(i.message)}.", "Incoerência"),
                          Spacer(1, 0.15 * cm)]

    # ------------------------------------------------------------------ #
    # 4. Mensagens
    # ------------------------------------------------------------------ #

    def _messages(self, story: list[Any], d: dict[str, Any]) -> None:
        scope = d.get("transcript_scope") or "prints"
        msgs = [m for m in (d.get("messages") or []) if hasattr(m, "line_number")]
        checks = d.get("screenshot_checks") or []
        st = d.get("stitch")
        seen_in: dict[int, list[str]] = {}
        for c in checks:
            for bc in c.checks:
                if bc.message is not None:
                    seen_in.setdefault(bc.message.line_number, []).append(c.reading.path.name)

        if msgs and scope == "prints" and checks:
            rows_src = [m for m in msgs if m.line_number in seen_in]
            lead = (f"Somente as <b>{len(rows_src)} mensagens que aparecem nos prints</b>, como estão na "
                    f"conversa exportada ({len(msgs)} mensagens no total). A conversa completa está "
                    f"guardada, lacrada, na pasta do caso, e não é reproduzida aqui.")
        elif msgs and scope == "period":
            rows_src = msgs
            ex = d.get("excerpt")
            span = f" de {ex.start:%d/%m/%Y} a {ex.end:%d/%m/%Y}" if ex else ""
            lead = f"As <b>{len(rows_src)} mensagens do período{span}</b>, como estão na conversa exportada."
        elif msgs:
            rows_src = msgs
            lead = (f"A conversa exportada completa: <b>{len(msgs)} mensagens</b>, de "
                    f"{msgs[0].timestamp:%d/%m/%Y} a {msgs[-1].timestamp:%d/%m/%Y}.")
        elif st is not None and st.messages:
            self._section(story, "4", "Mensagens",
                          "Sem a conversa exportada, as mensagens abaixo foram reconstituídas a partir "
                          "dos prints, sem repetições.")
            rows = [[m.when, "(ligação)" if m.kind == "call" else _esc(safe_text(m.text)[:300]),
                     _esc(", ".join(m.sources))] for m in st.messages]
            story += [self._table(["Data e hora", "Mensagem (lida por OCR)", "Aparece em"], rows,
                                  [2.8 * cm, CONTENT_WIDTH - 7.3 * cm, 4.5 * cm]),
                      self._p("A leitura por OCR pode ter pequenas imprecisões; os prints originais, "
                              "preservados e carimbados, são a referência.", "small")]
            return
        else:
            return

        self._section(story, "4", "Mensagens", "Transcrição a partir da conversa exportada, com o número "
                      "da linha no arquivo original. Emojis aparecem como [emoji].")
        story.append(self._p(lead))
        with_print_col = scope == "prints" and bool(checks)
        rows = []
        for m in rows_src:
            content = safe_text(m.content) or "(sem texto: ligação ou mídia)"
            row = [str(m.line_number), f"{m.timestamp:%d/%m/%Y %H:%M}", _esc(person_name(m.sender)[:60]), _esc(content[:400])]
            if with_print_col:
                row.append(_esc(", ".join(sorted(set(seen_in.get(m.line_number, []))))))
            rows.append(row)
        if with_print_col:
            story.append(self._table(["Linha", "Data e hora", "Remetente", "Mensagem", "Print"], rows,
                                     [1.1 * cm, 2.4 * cm, 3.0 * cm, CONTENT_WIDTH - 10.5 * cm, 4.0 * cm]))
        else:
            story.append(self._table(["Linha", "Data e hora", "Remetente", "Mensagem"], rows,
                                     [1.1 * cm, 2.4 * cm, 3.2 * cm, CONTENT_WIDTH - 6.7 * cm]))

    # ------------------------------------------------------------------ #
    # 5. Metodologia aplicada
    # ------------------------------------------------------------------ #

    def _methodology(self, story: list[Any], d: dict[str, Any]) -> None:
        story.append(PageBreak())
        self._section(story, "5", "Metodologia aplicada",
                      "Como o trabalho foi feito, com quais ferramentas, e o que este relatório "
                      "permite ou não permite afirmar.")
        steps = [
            ("Recebimento e cópia",
             "Os arquivos foram copiados para a pasta do caso, sem nenhuma alteração. Os originais de "
             "quem os entregou não são modificados."),
            ("Impressão digital",
             "Foi calculado o SHA-256 de cada arquivo recebido e gravado em um manifesto."),
            ("Carimbo de tempo",
             "O manifesto foi enviado a uma Autoridade de Carimbo do Tempo (padrão RFC 3161), que "
             "devolveu um carimbo assinado com a data e a hora. Só o código do manifesto sai do computador."),
        ]
        if d.get("emails"):
            steps.append(("Assinatura do e-mail",
                          "A assinatura DKIM do provedor do remetente foi conferida e a chave pública "
                          "consultada foi arquivada no manifesto."))
        if d.get("excerpt") is not None:
            steps.append(("Recorte do período",
                          "As mensagens do período escolhido, que formam um bloco contínuo de linhas, "
                          "foram copiadas byte a byte para um arquivo de recorte."))
        steps += [
            ("Leitura da conversa exportada",
             "O arquivo .txt do WhatsApp foi lido mensagem a mensagem (data, hora, remetente, texto), "
             "no fuso horário do celular que exportou."),
            ("Leitura dos prints",
             "Cada print foi lido por reconhecimento óptico de caracteres (OCR, Tesseract). Os horários, "
             "pequenos demais, foram relidos em recorte ampliado. Datas relativas (\"Ontem\", \"Segunda-"
             "feira\") foram convertidas pela data em que o print foi tirado."),
            ("Conferência",
             "Cada mensagem do print foi procurada na conversa exportada, no mesmo dia, comparando "
             "texto e hora. Também foram verificados o contato, a ordem das mensagens, o momento do "
             "print e mensagens omitidas entre as que aparecem. Os prints foram ainda comparados entre si."),
            ("Relatório",
             "Os resultados foram reunidos neste documento, gerado automaticamente."),
        ]
        rows = []
        for n, (title, text) in enumerate(steps, start=1):
            badge = Table([[self._p(str(n), "step_no")]], colWidths=[0.7 * cm], rowHeights=[0.7 * cm])
            badge.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PRIMARY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                       ("ROUNDEDCORNERS", [10, 10, 10, 10])]))
            rows.append([badge, self._p(f"<b>{title}.</b> {text}")])
        t = Table(rows, colWidths=[1.1 * cm, CONTENT_WIDTH - 1.1 * cm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story += [self._p("Passo a passo", "h2"), t, Spacer(1, 0.3 * cm)]

        story += [self._p("Ferramentas utilizadas", "h2"), self._table(
            ["Etapa", "Ferramenta", "Versão"], self._tools(), [5 * cm, 7 * cm, CONTENT_WIDTH - 12 * cm]),
            Spacer(1, 0.4 * cm)]

        story += [CondPageBreak(7 * cm), self._p("O que este relatório permite e não permite afirmar", "h2")]
        can = [
            "Os arquivos do manifesto são exatamente os mesmos desde o horário do carimbo de tempo "
            "(quando obtido), o que pode ser conferido sem o LexProof.",
            "Cada mensagem visível nos prints foi confrontada com a conversa exportada e com os demais "
            "prints, e cada divergência está apontada na Seção 3.",
            "Quando houve e-mail com assinatura válida, os anexos são os que saíram da conta do remetente.",
        ]
        cannot = [
            "Que o conteúdo é autêntico antes de ser entregue ao LexProof. A conversa exportada é um "
            "arquivo de texto; se ela e os prints tivessem sido alterados juntos, antes da preservação, "
            "a conferência não detectaria.",
            "Quem escreveu as mensagens. A conversa mostra o nome salvo na agenda; o número só aparece "
            "quando há o print do perfil do contato.",
            "O conteúdo de fotos, áudios e vídeos: o OCR lê apenas o texto dos balões.",
        ]
        table = Table([[self._p("<b>Permite afirmar</b>"), self._p("<b>Não permite afirmar</b>")],
                       [[self._p("• " + x, "cell") for x in can], [self._p("• " + x, "cell") for x in cannot]]],
                      colWidths=[CONTENT_WIDTH / 2, CONTENT_WIDTH / 2])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), OK_SOFT), ("BACKGROUND", (1, 0), (1, -1), WARN_SOFT),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("LINEAFTER", (0, 0), (0, -1), 2, colors.white),
        ]))
        story += [table, Spacer(1, 0.25 * cm), self._p(
            "Quando necessário, a prova pode ser complementada por ata notarial, perícia no aparelho ou "
            "cópia da conversa do outro participante.", "small"), Spacer(1, 0.4 * cm)]

        story += [CondPageBreak(6 * cm), self._p("Glossário", "h2")]
        terms = [
            ("SHA-256", "Algoritmo que gera a impressão digital (resumo criptográfico) de um arquivo. "
                        "Não se confunde com assinatura digital ICP-Brasil."),
            ("Manifesto", "Lista dos arquivos preservados, com a impressão digital de cada um."),
            ("Carimbo de tempo", "Registro assinado por uma Autoridade de Carimbo do Tempo (TSA) atestando "
                                 "que um dado já existia em determinado horário (RFC 3161)."),
            ("DKIM", "Assinatura que o servidor de e-mail do remetente põe em cada mensagem enviada."),
            ("OCR", "Reconhecimento óptico de caracteres: leitura do texto que aparece numa imagem."),
            ("Conversa exportada", "Arquivo gerado pela função \"Exportar conversa\" do WhatsApp."),
        ]
        story += [self._table(["Termo", "Significado"], [[f"<b>{_esc(a)}</b>", _esc(b)] for a, b in terms],
                              [3.6 * cm, CONTENT_WIDTH - 3.6 * cm]), Spacer(1, 0.5 * cm)]

        story += [CondPageBreak(4 * cm), self._callout("warn", DISCLAIMER + (
            " Este relatório registra o que foi recebido, quando, e o resultado das conferências "
            "descritas acima; a avaliação da prova cabe a quem a examina."), "Aviso")]

    def _tools(self) -> list[list[str]]:
        import platform

        try:
            import pytesseract

            tess = str(pytesseract.get_tesseract_version())
        except Exception:
            tess = "não identificada"
        try:
            import reportlab

            rl = reportlab.Version
        except Exception:
            rl = "-"
        try:
            import importlib.metadata as md

            dk = md.version("dkimpy")
        except Exception:
            dk = "-"
        try:
            out = subprocess.run(["openssl", "version"], capture_output=True, text=True, timeout=10).stdout.split()
            ossl = out[1] if len(out) > 1 else "-"
        except Exception:
            ossl = "não identificada"
        py = platform.python_version()
        return [
            ["Processamento", "LexProof", __version__],
            ["Linguagem", "Python", py],
            ["Impressão digital", "SHA-256 (hashlib do Python)", py],
            ["Carimbo de tempo", "OpenSSL (RFC 3161)", ossl],
            ["Assinatura do e-mail", "dkimpy", dk],
            ["Leitura dos prints", "Tesseract OCR (português)", tess],
            ["Relatório", "ReportLab", rl],
        ]

    # ------------------------------------------------------------------ #
    # Apêndices
    # ------------------------------------------------------------------ #

    def _appendices(self, story: list[Any], d: dict[str, Any]) -> None:
        story.append(PageBreak())
        story += [self._p("Apêndices", "h1"), Spacer(1, 0.3 * cm)]
        hashes = d.get("hashes") or []
        if hashes:
            story += [self._p("A. Todos os arquivos processados", "h2"), self._p(
                "Inclui os arquivos de dentro dos ZIPs e os anexos dos e-mails.", "small"), Spacer(1, 0.1 * cm)]
            rows = [[_esc(str(h.get("file_name", ""))[:60]), self._p(str(h.get("sha256", "-")), "mono")] for h in hashes]
            story += [self._table(["Arquivo", "SHA-256"], rows, [6.5 * cm, CONTENT_WIDTH - 6.5 * cm]), Spacer(1, 0.5 * cm)]
        ops = d.get("operations") or []
        if ops:
            labels = {"completed": ("CONCLUÍDA", "ok"), "skipped": ("NÃO APLICÁVEL", "neutral"),
                      "failed": ("FALHOU", "bad"), "running": ("EM ANDAMENTO", "neutral"),
                      "pending": ("PENDENTE", "neutral")}
            rows = []
            for op in ops:
                label, kind = labels.get(op.get("status", ""), (str(op.get("status", "-")).upper(), "neutral"))
                if op.get("step") == "Relatório" and op.get("status") == "running":
                    label, kind = "ESTE DOCUMENTO", "info"
                when = local_time(op["time"], with_utc=False).replace(" (Brasília)", "") if op.get("time") else "-"
                rows.append([when, _esc(op.get("description") or op.get("step", "")),
                             self._pill(label, kind), _esc(safe_text(op.get("detail", ""))[:120])])
            story += [CondPageBreak(5 * cm), self._p("B. Registro das operações", "h2"), self._p(
                "Etapas executadas pelo LexProof nesta preservação, na ordem e com o horário de início "
                "(Brasília).", "small"), Spacer(1, 0.1 * cm),
                self._table(["Início", "Etapa", "Situação", "Observação"], rows,
                            [3.6 * cm, 6.2 * cm, 2.8 * cm, CONTENT_WIDTH - 12.6 * cm])]
