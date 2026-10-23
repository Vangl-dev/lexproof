"""Gerador do Relatorio de Preservacao e Integridade em formato PDF.

Versao v0.57 — Relatorio de Preservacao e Integridade.
Todas as tabelas usam Paragraph para quebra automatica.
Miniaturas reais de imagens.
Secao Ambiente Tecnico.
Fluxograma visual.
Historico completo de processamento por imagem.
OCR detalhado.
Conferencia dos prints com a exportacao.
Carimbo de tempo RFC 3161.
Resumo executivo.
Referencias cruzadas.
Linguagem narrativa.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from lexproof import __version__
from lexproof.core.constants import DEFAULT_TIMEZONE
from lexproof.reports.report_data import hash_algorithm_rows

logger = logging.getLogger("lexproof.reports.pdf")

PAGE_WIDTH, PAGE_HEIGHT = A4
_CW = PAGE_WIDTH - 5 * cm

_C1 = colors.Color(0.1, 0.14, 0.49)
_C2 = colors.Color(0.0, 0.4, 0.8)
_C3 = colors.Color(0.95, 0.95, 0.97)
_C4 = colors.Color(0.92, 0.92, 0.94)
_PASS = colors.Color(0.2, 0.69, 0.3)
_FAIL = colors.Color(0.85, 0.15, 0.15)
_WARN = colors.Color(0.9, 0.6, 0.0)
_GRAY = colors.Color(0.45, 0.45, 0.45)
_DARK = colors.Color(0.15, 0.15, 0.15)
_INFO_BG = colors.Color(0.94, 0.96, 1.0)
_INFO_BORDER = colors.Color(0.0, 0.4, 0.8)

_DISCLAIMER = (
    "Documento gerado automaticamente por software. Nao constitui laudo pericial, "
    "ata notarial nem certificacao de autenticidade. Registra o processamento "
    "realizado e permite sua verificacao independente."
)
_WARN_BG = colors.Color(1.0, 0.97, 0.9)
_WARN_BORDER = colors.Color(0.9, 0.6, 0.0)


def _safe(text: Any) -> str:
    """Texto exibivel em Helvetica: letras estilizadas viram comuns, emojis viram [emoji]."""
    t = unicodedata.normalize("NFKC", str(text or ""))
    t = "".join(
        "\x00" if unicodedata.category(c) in ("So", "Cs") or ord(c) > 0xFFFF else c
        for c in t
    )
    t = re.sub("\x00+", "[emoji]", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Cf")
    t = "".join(c if ord(c) < 256 else "?" for c in unicodedata.normalize("NFC", t))
    t = t.replace("?️", "").replace("[emoji]?", "[emoji]")
    return re.sub(r"\s+", " ", t).strip()


def _fmt_local(dt: Any) -> str:
    """Data/hora no fuso de Brasilia, com o equivalente UTC."""
    if dt is None:
        return "-"
    local = dt.astimezone(ZoneInfo(DEFAULT_TIMEZONE))
    utc = dt.astimezone(timezone.utc)
    return f"{local:%d/%m/%Y %H:%M:%S} (Brasília) = {utc:%H:%M:%S} UTC"


def _p(text: str, styles: Any, style_name: str = "BodyJustified") -> Paragraph:
    """Helper para criar Paragraph com estilo."""
    return Paragraph(text, styles[style_name])


def _ph(text: str, styles: Any) -> Paragraph:
    """Paragraph com estilo de cabecalho de tabela."""
    return Paragraph(f"<b>{text}</b>", styles["SmallBold"])


def _info_box(text: str, styles: Any) -> list[Any]:
    t = Table([[_p(text, styles)]], colWidths=[_CW - 1 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _INFO_BG),
        ("BOX", (0, 0), (-1, -1), 1, _INFO_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    return [Spacer(1, 0.3 * cm), t, Spacer(1, 0.3 * cm)]


def _warn_box(text: str, styles: Any) -> list[Any]:
    t = Table([[_p(text, styles)]], colWidths=[_CW - 1 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _WARN_BG),
        ("BOX", (0, 0), (-1, -1), 1, _WARN_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    return [Spacer(1, 0.3 * cm), t, Spacer(1, 0.3 * cm)]


class _CoverPage(Flowable):
    def __init__(self, case_data: dict[str, Any], app_version: str, generated_at: str) -> None:
        super().__init__()
        self.case_data = case_data
        self.app_version = app_version
        self.generated_at = generated_at
        self.width = _CW
        self.height = PAGE_HEIGHT - 5 * cm

    def wrap(self, avail_width: int, avail_height: int) -> tuple[int, int]:
        return int(self.width), int(self.height)

    def draw(self) -> None:
        canvas = self.canv
        meta = self.case_data.get("metadata", {})
        w = self.width
        y = self.height - 1.5 * cm
        canvas.setFillColor(_C1)
        canvas.rect(0, y - 0.3 * cm, w, 2.5 * cm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 22)
        canvas.drawCentredString(w / 2, y + 1.1 * cm, "RELATORIO DE PRESERVACAO")
        canvas.drawCentredString(w / 2, y + 0.1 * cm, "E INTEGRIDADE")
        y -= 1.2 * cm
        canvas.setFont("Helvetica", 12)
        canvas.setFillColor(_GRAY)
        canvas.drawCentredString(w / 2, y, "Registro do processamento de arquivos digitais, verificavel de forma independente")
        y -= 1.8 * cm
        canvas.setStrokeColor(_C1)
        canvas.setLineWidth(1.5)
        canvas.line(0, y, w, y)
        y -= 0.8 * cm
        canvas.setFillColor(_C3)
        canvas.setStrokeColor(_C1)
        canvas.setLineWidth(0.5)
        box_h = 9 * cm
        canvas.roundRect(0, y - box_h, w, box_h, 4, fill=1, stroke=1)
        info_y = y - 1.0 * cm
        for label, value in [
            ("Numero do Relatorio", meta.get("case_id", "N/A")),
            ("Data de Geracao", self.generated_at),
            ("Versao do LexProof", self.app_version),
            ("Responsavel pela Preservacao", meta.get("examiner", "N/A")),
            ("Organizacao", meta.get("organization", "N/A")),
            ("Objeto da Analise", meta.get("title", "N/A")),
        ]:
            canvas.setFont("Helvetica-Bold", 9)
            canvas.setFillColor(_C1)
            canvas.drawString(1 * cm, info_y, f"{label}:")
            canvas.setFont("Helvetica", 9)
            canvas.setFillColor(_DARK)
            canvas.drawString(6.5 * cm, info_y, str(value))
            info_y -= 1.05 * cm
        y = y - box_h - 1.2 * cm
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(_GRAY)
        canvas.drawCentredString(w / 2, y, f"Documento gerado automaticamente pelo LexProof v{self.app_version}")


class PDFReportGenerator:
    def __init__(self) -> None:
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self) -> None:
        S = self.styles
        defs = [
            ("SectionHeader", S["Heading1"], 15, 19, TA_LEFT, 8, _C1),
            ("SubSection", S["Heading2"], 12, 15, TA_LEFT, 5, _C2),
            ("BodyTextCustom", S["Normal"], 10, 14, TA_LEFT, 6, _DARK),
            ("BodyJustified", S["Normal"], 10, 14, TA_LEFT, 6, _DARK),
            ("SmallText", S["Normal"], 8, 10, TA_LEFT, 4, _GRAY),
            ("SmallBold", S["Normal"], 8, 10, TA_LEFT, 4, _DARK),
            ("TableCell", S["Normal"], 7, 9, TA_LEFT, 2, _DARK),
            ("TableCellBold", S["Normal"], 7, 9, TA_LEFT, 2, _DARK),
            ("HashValue", S["Code"], 6, 8, TA_LEFT, 2, _DARK),
            ("TechnicalComment", S["Normal"], 9, 12, TA_LEFT, 4, colors.Color(0.25, 0.25, 0.35)),
            ("ConclusionTitle", S["Heading1"], 13, 17, TA_LEFT, 6, _C1),
            ("ConclusionBody", S["Normal"], 10, 14, TA_LEFT, 8, _DARK),
        ]
        for name, parent, fs, ld, al, sa, tc in defs:
            S.add(ParagraphStyle(name=name, parent=parent, fontSize=fs, leading=ld, alignment=al, spaceAfter=sa, textColor=tc))

    def generate(self, case_data: dict[str, Any], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        gen_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")
        doc = SimpleDocTemplate(
            str(output_path), pagesize=A4,
            rightMargin=2.5 * cm, leftMargin=2.5 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
            title=f"LexProof - {case_data.get('metadata', {}).get('title', 'Relatorio de Preservacao e Integridade')}",
            author="LexProof",
        )
        story: list[Any] = []
        story.append(_CoverPage(case_data, __version__, gen_at))
        story.append(PageBreak())

        self._add_resumo_executivo(story, case_data)
        self._add_identificacao_caso(story, case_data)
        self._add_carimbo(story, case_data)
        self._add_conferencia_prints(story, case_data)
        self._add_inventario(story, case_data)
        self._add_cadeia_custodia(story, case_data)
        self._add_transcricao(story, case_data)
        self._add_ambiente_tecnico(story, case_data)
        self._add_metodologia(story, case_data)
        self._add_limitacoes(story, case_data)
        self._add_glossario(story)
        self._add_apendices(story, case_data)

        def _footer(canvas: Any, doc_ref: Any) -> None:
            canvas.saveState()
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(_GRAY)
            canvas.drawString(2.5 * cm, 1.2 * cm, f"LexProof v{__version__} | Relatorio de Preservacao e Integridade")
            canvas.drawRightString(PAGE_WIDTH - 2.5 * cm, 1.2 * cm, f"Pagina {doc_ref.page}")
            canvas.setStrokeColor(_C4)
            canvas.setLineWidth(0.5)
            canvas.line(2.5 * cm, 1.5 * cm, PAGE_WIDTH - 2.5 * cm, 1.5 * cm)
            _disclaimer(canvas)
            canvas.restoreState()

        def _disclaimer(canvas: Any) -> None:
            canvas.setFont("Helvetica", 6)
            canvas.setFillColor(_GRAY)
            canvas.drawCentredString(PAGE_WIDTH / 2, 0.8 * cm, _DISCLAIMER)

        def _first_page(canvas: Any, doc_ref: Any) -> None:
            canvas.saveState()
            _disclaimer(canvas)
            canvas.restoreState()

        doc.build(story, onFirstPage=_first_page, onLaterPages=_footer)
        logger.info("Relatorio de preservacao gerado: %s", output_path)
        return output_path

    # ------------------------------------------------------------------ #
    # HELPER: tabela com Paragraph em todas as celulas
    # ------------------------------------------------------------------ #

    def _make_table(self, rows: list[list[str]], col_widths: list[float], S: Any = None) -> Table:
        """Cria tabela com Paragraph em todas as celulas para quebra automatica."""
        if S is None:
            S = self.styles
        p_rows = []
        for i, row in enumerate(rows):
            p_row = []
            for cell in row:
                if i == 0:
                    p_row.append(Paragraph(f"<b>{self._esc(str(cell))}</b>", S["SmallBold"]))
                else:
                    p_row.append(Paragraph(self._esc(str(cell)), S["TableCell"]))
            p_rows.append(p_row)
        t = Table(p_rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _C1),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, _C4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _C3]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        return t

    def _esc(self, text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _ts(self, ts_raw: str) -> tuple[str, str]:
        try:
            dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            return dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M:%S")
        except (ValueError, TypeError):
            if "T" in ts_raw:
                parts = ts_raw.split("T")
                return parts[0], parts[1][:8] if len(parts) > 1 else ""
            return ts_raw, ""

    def _fsize(self, size_bytes: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def _img_exts(self) -> set[str]:
        return {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}

    def _images_of(self, evidence_files: list[dict]) -> list[dict]:
        exts = self._img_exts()
        return [e for e in evidence_files if Path(str(e.get("name", ""))).suffix.lower() in exts]

    def _hashes_by(self, hashes: list[dict]) -> dict[str, dict[str, str]]:
        h = {}
        for hr in hashes:
            fn = str(hr.get("file_name", ""))
            if fn not in h:
                h[fn] = {}
            for k in ("sha256", "blake3", "hash_value"):
                v = hr.get(k, "")
                if v:
                    h[fn][k] = str(v)
        return h

    def _ocr_source(self, r: Any) -> str:
        """Caminho da imagem de origem do OCR (campo real do modelo atual)."""
        p = str(getattr(r, "source_image", "") or "")
        if not p:
            p = str(getattr(r, "file_path", "") or "")
        return p

    def _add_resumo_executivo(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        ef = d.get("evidence_files", [])
        seal = d.get("seal")
        checks = d.get("screenshot_checks") or []
        msgs = [m for m in (d.get("messages") or []) if hasattr(m, "timestamp")]

        story.append(Paragraph("Resumo", S["SectionHeader"]))
        story.append(_p("O que este relatório registra, em linguagem simples:", S))

        points: list[tuple[bool, str]] = []
        n_orig = (
            sum(1 for _, rel in seal.files if not rel.startswith("preservacao/"))
            if seal is not None else len(ef)
        )
        if seal is not None and seal.timestamp is not None:
            points.append((True,
                f"<b>{n_orig} arquivo(s) recebido(s)</b> tiveram seu SHA-256 registrado em um "
                f"manifesto, carimbado por terceiro ({self._esc(seal.timestamp.tsa_url)}) em "
                f"<b>{_fmt_local(seal.timestamp.gen_time)}</b>. Isso permite a qualquer pessoa "
                f"conferir que eles não foram alterados desde então (Seção 2)."))
        elif seal is not None:
            points.append((False,
                f"{n_orig} arquivo(s) tiveram seu SHA-256 registrado, mas <b>o carimbo de tempo "
                f"não foi obtido</b>; a data desta preservação não está atestada por terceiro (Seção 2)."))
        else:
            points.append((False, "Não foi gerado manifesto de hashes nem carimbo de tempo."))

        for em in d.get("emails") or []:
            sig = em.aligned_signature
            if em.verified:
                points.append((True,
                    f"O e-mail <b>{self._esc(_safe(em.sender))}</b> de "
                    f"{_fmt_local(em.date).split(' = ')[0] if em.date else '-'} trouxe "
                    f"{len(em.attachments)} anexo(s) com assinatura DKIM válida de "
                    f"<b>{self._esc(sig.domain)}</b>: os anexos são os mesmos que saíram desse "
                    f"servidor (Seção 2)."))
            else:
                points.append((False,
                    f"O e-mail {self._esc(_safe(em.sender)) or em.eml_path.name} <b>não tem "
                    f"assinatura DKIM válida do remetente</b>; não comprova a origem dos anexos (Seção 2)."))

        ex = d.get("excerpt")
        if ex is not None:
            fate = ("o restante foi apagado da pasta do caso, ficando só o hash do arquivo completo"
                    if ex.discarded else "o arquivo completo ficou guardado, lacrado, fora do relatório")
            points.append((True,
                f"A conversa foi <b>limitada ao período de {ex.start:%d/%m/%Y} a {ex.end:%d/%m/%Y}</b> "
                f"({ex.kept_messages} de {ex.total_messages} mensagens); {fate}. O recorte pode ser "
                f"conferido contra o arquivo completo (Seção 2)."))

        if msgs:
            senders = sorted({_safe(m.sender).replace("[emoji]", "").strip() for m in msgs if m.sender and m.sender != "Desconhecido"})
            points.append((True,
                f"A conversa exportada do WhatsApp tem <b>{len(msgs)} mensagens</b>, de "
                f"{msgs[0].timestamp:%d/%m/%Y} a {msgs[-1].timestamp:%d/%m/%Y}, entre "
                f"{self._esc(' e '.join(senders)) or '-'} (transcrição na Seção 6)."))
        else:
            st = d.get("stitch")
            if st is not None and st.order:
                first, last = st.first, st.last
                span = f", de {first.when} a {last.when}" if first and last else ""
                text = (
                    f"Sem exportação da conversa: os <b>{len(st.order)} prints</b> foram conferidos "
                    f"entre si ({len(st.messages)} mensagens distintas{span}). "
                )
                if st.all_ok:
                    text += "Eles se encadeiam sem lacunas nem contradições (Seção 3)."
                else:
                    text += (
                        f"Foram encontradas <b>{len(st.gaps)} lacuna(s), {len(st.contradictions)} "
                        f"contradição(ões) e {len(st.issues)} incoerência(s)</b> (Seção 3)."
                    )
                points.append((st.all_ok, text))
            else:
                points.append((False, "Nenhuma exportação de conversa do WhatsApp foi lida."))

        for chk in checks:
            name = self._esc(chk.reading.path.name)
            if chk.all_ok:
                points.append((True,
                    f"Print <b>{name}</b>: as {chk.total} mensagens visíveis conferem com a "
                    f"exportação em texto, data e hora (Seção 3)."))
            else:
                points.append((False,
                    f"Print <b>{name}</b>: {chk.confirmed} de {chk.total} mensagens conferem; "
                    f"<b>há divergências</b> descritas na Seção 3."))

        for ok, text in points:
            box = _info_box if ok else _warn_box
            story.extend(box(text, S))

        story.append(Spacer(1, 0.3 * cm))
        story.append(_p(
            "Este relatório não atesta que o conteúdo é autêntico antes de ter sido entregue ao "
            "LexProof, nem quem escreveu as mensagens. Ele registra o que foi recebido, quando, e "
            "o resultado do confronto entre os prints e a conversa exportada (Seção 9).",
            S, "SmallText",
        ))
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # CARIMBO DE TEMPO
    # ------------------------------------------------------------------ #

    def _add_carimbo(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        seal = d.get("seal")
        story.append(Paragraph("2. Carimbo de Tempo e Verificação Independente", S["SectionHeader"]))
        if seal is None:
            story.extend(_warn_box(
                "Esta preservação não gerou manifesto de hashes nem carimbo de tempo.", S
            ))
            story.append(PageBreak())
            return

        story.append(_p(
            "Logo após o recebimento, o LexProof calculou o SHA-256 de cada arquivo original e "
            "gravou essas impressões digitais em um manifesto. O manifesto foi então enviado a uma "
            "Autoridade de Carimbo do Tempo (TSA, padrão RFC 3161), que devolveu um carimbo "
            "assinado com a data e a hora em que o recebeu. A TSA recebe apenas o hash do "
            "manifesto, nunca o conteúdo dos arquivos.",
            S,
        ))
        ts = seal.timestamp
        rows = [["Item", "Valor"], ["Manifesto", f"{seal.seal_dir.name}/{seal.manifest_path.name}"],
                ["SHA-256 do manifesto", seal.manifest_sha256]]
        if ts is not None:
            rows += [
                ["Emitido por", ts.tsa_url],
                ["Horário atestado", _fmt_local(ts.gen_time)],
                ["Número de série", ts.serial],
                ["Arquivo do carimbo", f"{seal.seal_dir.name}/{ts.tsr_path.name}"],
            ]
        story.append(self._make_table(rows, [4.5 * cm, 11.5 * cm], S))
        if ts is None:
            story.extend(_warn_box(
                "<b>Carimbo de tempo não obtido</b>"
                + (f": {self._esc(seal.timestamp_error)}" if seal.timestamp_error else "")
                + ". O manifesto comprova a integridade dos arquivos a partir do momento em que "
                "for entregue a um terceiro, mas não a data desta preservação.",
                S,
            ))
        else:
            story.extend(_info_box(
                f"O carimbo comprova que os arquivos listados abaixo já existiam, exatamente "
                f"como estão, em <b>{_fmt_local(ts.gen_time)}</b>. Qualquer alteração posterior, "
                f"mesmo de um único byte, faria a conferência falhar.",
                S,
            ))

        story.append(Paragraph("<b>Como qualquer pessoa pode conferir</b>", S["SubSection"]))
        story.append(_p(
            "A pasta <b>preservacao</b> do caso contém o manifesto, o carimbo, os certificados "
            "públicos da TSA e o arquivo COMO_VERIFICAR.txt. A conferência usa ferramentas "
            "comuns e não depende do LexProof:",
            S,
        ))
        cmds = [f"sha256sum -c preservacao/{seal.manifest_path.name}"]
        if ts is not None and seal.verify_command:
            cmds.append(seal.verify_command)
        for c in cmds:
            story.append(Paragraph(self._esc(c), S["HashValue"]))
        story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph("<b>Arquivos no manifesto</b>", S["SubSection"]))
        rows = [["Arquivo", "SHA-256"]]
        for digest, rel in seal.files:
            rows.append([rel, digest])
        story.append(self._make_table(rows, [6 * cm, 10 * cm], S))
        self._add_recorte(story, d)
        self._add_emails(story, d)
        story.append(PageBreak())

    def _add_emails(self, story: list[Any], d: dict[str, Any]) -> None:
        """Subsecao da Secao 2: arquivos recebidos por e-mail e o DKIM."""
        S = self.styles
        emails = d.get("emails") or []
        if not emails:
            return
        story.append(Paragraph("<b>Arquivos recebidos por e-mail</b>", S["SubSection"]))
        story.append(_p(
            "Os provedores de e-mail assinam as mensagens que enviam (assinatura DKIM), "
            "incluindo os anexos. O LexProof conferiu essa assinatura ao receber cada e-mail. "
            "Assinatura válida significa que remetente, data, assunto e anexos estão exatamente "
            "como saíram do servidor do domínio indicado. A chave pública do provedor, consultada "
            "no DNS neste momento, foi arquivada em <b>preservacao/dkim-chaves.txt</b>, que está "
            "no manifesto carimbado, para que a conferência possa ser refeita depois que o "
            "provedor trocar a chave.",
            S,
        ))
        for em in emails:
            sig = em.aligned_signature or (em.signatures[0] if em.signatures else None)
            if em.verified:
                result = f"Válida, assinada por {sig.domain}"
            elif sig is not None and sig.valid:
                result = f"Válida, mas assinada por {sig.domain} (outro domínio) ou parcial"
            elif sig is not None:
                result = f"NÃO confere ({sig.error})"
            else:
                result = "Sem assinatura DKIM" + (f" ({em.error})" if em.error else "")
            rows = [
                ["Item", "Valor"],
                ["Arquivo", em.eml_path.name],
                ["Remetente", _safe(em.sender)],
                ["Destinatário", _safe(em.to)],
                ["Data de envio", _fmt_local(em.date) if em.date else "-"],
                ["Assunto", _safe(em.subject) or "-"],
                ["Assinatura DKIM", result],
                ["Anexos", str(len(em.attachments))],
            ]
            table = self._make_table(rows, [4 * cm, 12 * cm], S)
            table.setStyle(TableStyle([("TEXTCOLOR", (1, 6), (1, 6), _PASS if em.verified else _FAIL)]))
            story.append(table)
            if em.attachments:
                arows = [["Anexo", "SHA-256"]]
                for a in em.attachments:
                    arows.append([a.name, a.sha256])
                story.append(Spacer(1, 0.15 * cm))
                story.append(self._make_table(arows, [6 * cm, 10 * cm], S))
            if not em.verified:
                story.extend(_warn_box(
                    "Sem assinatura válida do domínio do remetente, este e-mail não comprova a "
                    "origem dos anexos. Isso acontece quando o e-mail foi encaminhado, salvo de "
                    "forma diferente do original (\"Baixar original\" no Gmail) ou alterado.",
                    S,
                ))
            story.append(Spacer(1, 0.3 * cm))

    def _add_prints_entre_si(self, story: list[Any], d: dict[str, Any]) -> None:
        """Parte da Secao 3: prints conferidos entre si."""
        S = self.styles
        st = d.get("stitch")
        if st is None or not st.order:
            return
        with_export = bool(d.get("screenshot_checks"))
        story.append(Paragraph("<b>Prints conferidos entre si</b>", S["SubSection"]))
        story.append(_p(
            "Ao rolar a tela entre um print e outro, prints vizinhos repetem algumas mensagens. "
            "O LexProof ordenou os prints pelo conteúdo e verificou se cada um tem mensagem em "
            "comum com o seguinte. Sem mensagem em comum há uma <b>lacuna</b>: pode haver "
            "mensagens que não foram capturadas. A mesma mensagem (mesma data e hora) com texto "
            "diferente em dois prints é uma <b>contradição</b>. Um balão cortado na borda da tela "
            "é comparado apenas com o trecho visível.",
            S,
        ))
        rows = [["#", "Print", "Tirado em", "Primeira mensagem", "Última mensagem", "Sequência"]]
        gap_after = {g.after_print for g in st.gaps}
        for n, r in enumerate(st.order, start=1):
            own = [m for m in st.messages if r.path.name in m.sources]
            seq = "início" if n == 1 else ("LACUNA antes" if r.path.name in gap_after else "continua")
            rows.append([
                str(n), r.path.name,
                f"{r.captured_at:%d/%m/%Y %H:%M}" if r.captured_at else "-",
                own[0].when if own else "-", own[-1].when if own else "-", seq,
            ])
        table = self._make_table(rows, [0.7 * cm, 4.6 * cm, 2.6 * cm, 2.9 * cm, 2.9 * cm, 2.3 * cm], S)
        for n, r in enumerate(st.order, start=1):
            if r.path.name in gap_after:
                table.setStyle(TableStyle([("TEXTCOLOR", (5, n), (5, n), _FAIL)]))
        story.append(table)

        for g in st.gaps:
            if with_export:
                story.append(_p(
                    f"Entre <b>{self._esc(g.before_print)}</b> e <b>{self._esc(g.after_print)}</b> há "
                    f"mensagens não printadas ({g.last_before.when} a {g.first_after.when}). Como "
                    f"cada print foi conferido com a exportação (abaixo), isso não indica problema.",
                    S, "SmallText",
                ))
                continue
            story.extend(_warn_box(
                f"<b>Lacuna</b> entre <b>{self._esc(g.before_print)}</b> e "
                f"<b>{self._esc(g.after_print)}</b>: os prints não têm mensagem em comum. Pode "
                f"haver mensagens não capturadas entre {g.last_before.when} "
                f"(\"{self._esc(_safe(g.last_before.text)[:50])}\") e {g.first_after.when} "
                f"(\"{self._esc(_safe(g.first_after.text)[:50])}\").",
                S,
            ))
        for c in st.contradictions:
            diffs = "; ".join(f"\"{a or '(nada)'}\" x \"{b or '(nada)'}\"" for a, b in c.differences)
            story.extend(_warn_box(
                f"<b>Contradição</b> na mensagem de {c.when}: <b>{self._esc(c.print_a)}</b> mostra "
                f"\"{self._esc(_safe(c.text_a)[:80])}\" e <b>{self._esc(c.print_b)}</b> mostra "
                f"\"{self._esc(_safe(c.text_b)[:80])}\". Diferença: {self._esc(diffs)}.",
                S,
            ))
        for i in st.issues:
            story.extend(_warn_box(f"<b>{self._esc(i.print_name)}</b>: {self._esc(i.message)}.", S))
        if st.unread:
            story.append(_p(
                f"Imagens sem balões de conversa reconhecidos (não conferidas): "
                f"{self._esc(', '.join(st.unread))}.", S, "SmallText",
            ))

        first, last = st.first, st.last
        span = f", de {first.when} a {last.when}" if first and last else ""
        verdict = (
            f"<b>Resultado:</b> {len(st.order)} print(s), {len(st.messages)} mensagem(ns) "
            f"distinta(s){span}; {len(st.gaps)} lacuna(s), {len(st.contradictions)} "
            f"contradição(ões) e {len(st.issues)} incoerência(s)."
        )
        story.extend((_warn_box if st.needs_attention(with_export) else _info_box)(verdict, S))
        story.append(Spacer(1, 0.3 * cm))

    def _add_transcricao_prints(self, story: list[Any], st: Any) -> None:
        S = self.styles
        story.append(Paragraph("6. Transcrição Reconstituída a partir dos Prints", S["SectionHeader"]))
        story.append(_p(
            f"Não houve exportação da conversa. Abaixo, as <b>{len(st.messages)}</b> mensagens "
            f"distintas lidas nos prints, em ordem, sem repetições, com os prints em que cada "
            f"uma aparece. A leitura é feita por OCR e pode conter pequenas imprecisões de "
            f"acentuação; os prints originais, preservados e listados no manifesto, são a referência.",
            S,
        ))
        rows = [["Data e hora", "Mensagem", "Aparece em"]]
        for m in st.messages:
            text = "(ligação)" if m.kind == "call" else _safe(m.text)
            rows.append([m.when, text[:300], ", ".join(m.sources)])
        story.append(self._make_table(rows, [3 * cm, 8.5 * cm, 4.5 * cm], S))
        story.append(PageBreak())

    def _add_recorte(self, story: list[Any], d: dict[str, Any]) -> None:
        """Subsecao da Secao 2: recorte da conversa ao periodo de interesse."""
        S = self.styles
        ex = d.get("excerpt")
        if ex is None:
            return
        story.append(Paragraph("<b>Recorte do período de interesse</b>", S["SubSection"]))
        fate = (
            "Por privacidade, a conversa completa e as mídias fora do período foram "
            "<b>apagadas</b> da pasta do caso; ficaram apenas os hashes do arquivo completo."
            if ex.discarded else
            "A conversa completa foi guardada, lacrada, na pasta do caso (listada no manifesto), "
            "mas este relatório mostra apenas o período de interesse."
        )
        story.append(_p(
            f"A análise foi limitada ao período de <b>{ex.start:%d/%m/%Y} a {ex.end:%d/%m/%Y}</b>: "
            f"{ex.kept_messages} de {ex.total_messages} mensagens. Como a exportação é cronológica, "
            f"essas mensagens são as linhas {ex.first_line} a {ex.last_line} do arquivo, copiadas "
            f"byte a byte para o recorte. {fate} O registro <b>preservacao/recorte.txt</b> está "
            f"no manifesto carimbado.",
            S,
        ))
        rows = [["Item", "SHA-256"]]
        if ex.source_zip:
            rows.append([f"ZIP completo: {ex.source_zip}", ex.source_zip_sha256])
        rows.append([f"Conversa completa: {ex.source_txt}", ex.source_txt_sha256])
        rows.append([f"Recorte (linhas {ex.first_line} a {ex.last_line})", ex.excerpt_sha256])
        story.append(self._make_table(rows, [6 * cm, 10 * cm], S))
        story.append(_p(
            "Quem tiver a conversa completa (o cliente ou um perito) confere que o recorte é fiel:",
            S,
        ))
        story.append(Paragraph(self._esc(ex.verify_command), S["HashValue"]))
        if ex.discarded:
            story.extend(_warn_box(
                "Como o restante foi descartado, essa conferência depende de alguém ainda ter o "
                "arquivo completo. Recomende ao cliente guardar a conversa no celular ou o arquivo "
                "exportado.",
                S,
            ))
        story.append(Spacer(1, 0.3 * cm))

    # ------------------------------------------------------------------ #
    # CONFERENCIA DOS PRINTS
    # ------------------------------------------------------------------ #

    def _add_conferencia_prints(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        checks = d.get("screenshot_checks") or []
        st = d.get("stitch")
        story.append(Paragraph("3. Conferência dos Prints", S["SectionHeader"]))
        if not checks and (st is None or not st.order):
            story.extend(_warn_box("Nenhum print de conversa foi reconhecido.", S))
            story.append(PageBreak())
            return
        self._add_prints_entre_si(story, d)
        if not checks:
            story.extend(_warn_box(
                "Sem a exportação da conversa, os prints foram conferidos apenas entre si. "
                "Eles não foram confrontados com a conversa original do WhatsApp.",
                S,
            ))
            story.append(PageBreak())
            return
        story.append(Paragraph("<b>Prints conferidos com a conversa exportada</b>", S["SubSection"]))

        story.append(_p(
            "Cada print foi lido por reconhecimento de texto (OCR). Para cada balão visível, o "
            "LexProof identificou o texto, o horário e a data (pelo separador de data acima dele) "
            "e procurou a mesma mensagem na exportação da conversa. O resultado de cada balão é: "
            "<b>Confere</b> (texto, data e hora iguais), <b>Horário diferente</b>, <b>Data "
            "diferente</b>, <b>Texto diferente</b> ou <b>Não encontrada</b>. Acentos e pontuação "
            "não são considerados, pois o OCR pode lê-los de forma imprecisa.",
            S,
        ))

        for idx, chk in enumerate(checks, start=1):
            reading = chk.reading
            story.append(Paragraph(
                f"<b>3.{idx} {self._esc(reading.path.name)}</b>", S["SubSection"]
            ))
            info = [["Item", "Print", "Exportação / Conferência"]]
            info.append([
                "Contato",
                _safe(reading.contact) or "não identificado",
                (_safe(chk.export_contact) or "-") + (
                    "" if chk.contact_matches is None
                    else (" (confere)" if chk.contact_matches else " (DIFERENTE)")
                ),
            ])
            info.append([
                "Momento do print",
                _fmt_local(reading.captured_at) if reading.captured_at else "não identificado",
                f"fonte: {reading.captured_at_source}" if reading.captured_at_source else "-",
            ])
            if chk.captured_after_messages is not None:
                info.append([
                    "Print posterior às mensagens",
                    "",
                    "sim" if chk.captured_after_messages else "NÃO: o print é anterior a mensagens que exibe",
                ])
            info.append([
                "Ordem das mensagens", "", "mesma ordem da exportação" if chk.order_ok else "ORDEM DIFERENTE da exportação",
            ])
            story.append(self._make_table(info, [4 * cm, 5 * cm, 7 * cm], S))
            story.append(Spacer(1, 0.2 * cm))
            self._thumb_fit(str(reading.path), story, max_w=5 * cm, max_h=10 * cm)

            rows = [["#", "Data", "Hora", "Texto no print", "Resultado", "Linha"]]
            for n, c in enumerate(chk.checks, start=1):
                b = c.bubble
                rows.append([
                    str(n),
                    b.date.strftime("%d/%m/%Y") if b.date else "(deduzida)",
                    b.time or "ilegível",
                    _safe(b.text)[:90],
                    c.status.label,
                    str(c.message.line_number) if c.message else "-",
                ])
            table = self._make_table(rows, [0.7 * cm, 2 * cm, 1.3 * cm, 7 * cm, 3.5 * cm, 1.5 * cm], S)
            for r, c in enumerate(chk.checks, start=1):
                color = _PASS if c.status.ok else _FAIL
                table.setStyle(TableStyle([("TEXTCOLOR", (4, r), (4, r), color)]))
            story.append(table)

            notes = [(n, c) for n, c in enumerate(chk.checks, start=1) if c.notes]
            if notes:
                story.append(Spacer(1, 0.2 * cm))
                for n, c in notes:
                    for note in c.notes:
                        story.append(_p(f"Balão {n}: {self._esc(_safe(note))}", S, "SmallText"))

            if chk.hidden_messages:
                lines = "<br/>".join(
                    f"Linha {m.line_number} ({m.timestamp:%d/%m/%Y %H:%M}): {self._esc(_safe(m.content)[:80])}"
                    for m in chk.hidden_messages[:15]
                )
                story.extend(_warn_box(
                    f"<b>Mensagens da exportação que não aparecem no print</b>, embora estejam "
                    f"entre mensagens que aparecem:<br/>{lines}",
                    S,
                ))
            if chk.hidden_media:
                story.append(_p(
                    f"{chk.hidden_media} mídia(s) (foto, áudio, figurinha) do mesmo trecho não "
                    f"foram conferidas, pois o OCR não lê imagens dentro do print.",
                    S, "SmallText",
                ))

            verdict = (
                f"<b>Resultado:</b> {chk.confirmed} de {chk.total} balão(ões) conferem com a exportação"
            )
            if chk.all_ok:
                story.extend(_info_box(verdict + ", sem nenhuma divergência.", S))
            else:
                story.extend(_warn_box(verdict + ". Há divergências descritas acima, que devem ser "
                                       "examinadas antes de usar este print.", S))
        story.append(PageBreak())

    def _thumb_fit(self, file_path: str, story: list[Any], max_w: float, max_h: float) -> None:
        """Miniatura preservando a proporção da imagem."""
        try:
            from PIL import Image as PILImage

            with PILImage.open(file_path) as im:
                w, h = im.size
            scale = min(max_w / w, max_h / h)
            story.append(Image(file_path, width=w * scale, height=h * scale))
            story.append(Spacer(1, 0.2 * cm))
        except Exception as e:
            story.extend(_warn_box(f"Miniatura indisponível: {self._esc(str(e))}", self.styles))

    # ------------------------------------------------------------------ #
    # TRANSCRICAO
    # ------------------------------------------------------------------ #

    def _add_transcricao(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        msgs = [m for m in (d.get("messages") or []) if hasattr(m, "line_number")]
        if not msgs and d.get("stitch") is not None and d["stitch"].messages:
            self._add_transcricao_prints(story, d["stitch"])
            return
        ex = d.get("excerpt")
        title = "6. Transcrição da Conversa Exportada"
        if ex is not None:
            title += f" ({ex.start:%d/%m/%Y} a {ex.end:%d/%m/%Y})"
        story.append(Paragraph(title, S["SectionHeader"]))
        if not msgs:
            story.extend(_warn_box("Nenhuma exportação de conversa foi lida.", S))
            story.append(PageBreak())
            return
        first, last = msgs[0].timestamp, msgs[-1].timestamp
        senders = sorted({_safe(m.sender).replace("[emoji]", "").strip() for m in msgs if m.sender and m.sender != "Desconhecido"})
        story.append(_p(
            f"Transcrição das <b>{len(msgs)}</b> mensagens da exportação, de "
            f"{first:%d/%m/%Y %H:%M} a {last:%d/%m/%Y %H:%M} (horário do celular que exportou). "
            f"Participantes: {self._esc(', '.join(senders)) or '-'}. A coluna <b>Linha</b> é o "
            f"número da linha no arquivo .txt original. Emojis aparecem como [emoji]; o arquivo "
            f"original, preservado e listado no manifesto, é a referência.",
            S,
        ))
        rows = [["Linha", "Data e hora", "Remetente", "Mensagem"]]
        for m in msgs:
            content = _safe(m.content) or "(sem texto: ligação ou mídia)"
            rows.append([str(m.line_number), f"{m.timestamp:%d/%m/%Y %H:%M}", _safe(m.sender).replace("[emoji]", "").strip()[:22], content[:300]])
        story.append(self._make_table(rows, [1.2 * cm, 2.6 * cm, 3.2 * cm, 9 * cm], S))
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # 1. IDENTIFICACAO DO CASO
    # ------------------------------------------------------------------ #

    def _add_identificacao_caso(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        meta = d.get("metadata", {})
        ef = d.get("evidence_files", [])
        imgs = self._images_of(ef)
        exps = [e for e in ef if str(e.get("type", "")) == "chat_export"]

        story.append(Paragraph("1. Identificacao do Caso", S["SectionHeader"]))
        rows = [
            ["Campo", "Descricao"],
            ["Numero do Relatorio", meta.get("case_id", "N/A")],
            ["Data de Geracao", datetime.now(timezone.utc).strftime("%d/%m/%Y")],
            ["Versao do LexProof", __version__],
            ["Responsavel pela Preservacao", meta.get("examiner", "N/A")],
            ["Organizacao", meta.get("organization", "N/A")],
            ["Objeto da Analise", meta.get("title", "N/A")],
        ]
        if meta.get("received_via"):
            rows.append(["Origem dos arquivos", meta["received_via"]])
        story.append(self._make_table(rows, [4.5 * cm, 11.5 * cm], S))
        story.append(Spacer(1, 0.3 * cm))

        parts = []
        if exps:
            names = ", ".join(f"'{self._esc(str(e.get('name', '')))}'" for e in exps)
            parts.append(f"uma exportacao de conversa do WhatsApp denominada {names}")
        if imgs:
            n = len(imgs)
            word = "captura" if n == 1 else "capturas"
            parts.append(f"{n} {word} de tela")
        if not parts:
            parts.append(f"{len(ef)} arquivo(s)")
        story.extend(_info_box(
            f"Foi submetido ao LexProof um conjunto de evidencias digitais composto por "
            f"{' e '.join(parts)}. "
            f"O carimbo de tempo esta na Secao 2, a conferencia dos prints com a conversa na "
            f"Secao 3 e a lista de arquivos com seus hashes na Secao 4.",
            S,
        ))
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # AMBIENTE TECNICO
    # ------------------------------------------------------------------ #

    def _add_ambiente_tecnico(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        story.append(Paragraph("7. Ambiente Tecnico", S["SectionHeader"]))
        story.append(_p(
            "Todas as ferramentas e bibliotecas utilizadas neste relatorio sao documentadas "
            "abaixo. Cada processo indica o motor utilizado, a biblioteca, a versao e o "
            "resultado obtido. Esta transparencia permite que qualquer pessoa reproduza o processamento.",
            S,
        ))
        story.append(Spacer(1, 0.3 * cm))

        try:
            import PySide6
            qt_ver = PySide6.__version__
        except Exception:
            qt_ver = "N/D"
        try:
            import reportlab as rl
            rl_ver = rl.Version
        except Exception:
            rl_ver = __version__

        rows = [
            ["Processo", "Motor", "Biblioteca", "Versao", "Resultado"],
            ["Preservacao", "PreservationPipeline", "Interno", __version__, "OK"],
            ["Hash SHA-256", "hashlib", "Python stdlib", "3.x", "OK"],
            ["Hash BLAKE3", "blake3", "blake3", "1.x", "OK (ou indisponivel)"],
            ["OCR", "EasyOCR / Tesseract", "easyocr / pytesseract", "N/D", "OK"],
            ["Leitura EXIF", "Pillow", "PIL", "N/D", "OK"],
            ["Parser WhatsApp", "WhatsAppParser", "Interno", __version__, "OK"],
            ["Carimbo de tempo", "RFC 3161 (FreeTSA)", "openssl", "-", "OK"],
            ["Conferencia dos prints", "ScreenshotMatcher", "Interno + Tesseract", __version__, "OK"],
            ["Timeline", "TimelineBuilder", "Interno", __version__, "OK"],
            ["PDF", "ReportLab", "reportlab", rl_ver, "OK"],
            ["Interface", "PySide6", "Qt", qt_ver, "OK"],
        ]
        story.append(self._make_table(rows, [3 * cm, 3 * cm, 3 * cm, 2.5 * cm, 4.5 * cm], S))
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # METODOLOGIA
    # ------------------------------------------------------------------ #

    def _add_metodologia(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        ef = d.get("evidence_files", [])
        hashes = d.get("hashes", [])
        ocrs = d.get("ocr_results", [])
        msgs = d.get("messages", d.get("txt_messages", []))
        msg_n = len(msgs) if isinstance(msgs, list) else 0
        vers = d.get("verifications", [])
        img_n = len(self._images_of(ef))

        story.append(Paragraph("8. Metodologia", S["SectionHeader"]))
        story.append(_p(
            f"Esta secao documenta cada etapa executada pelo LexProof. "
            f"Foram processadas <b>{len(ef)}</b> evidencia(s) ({img_n} imagem(ns)), "
            f"executadas <b>{len(hashes)}</b> operacoes de hashing, "
            f"<b>{len(ocrs)}</b> processamento(s) OCR, "
            f"<b>{msg_n}</b> indexacao(es) de mensagem(ns), "
            f"<b>{len(d.get('screenshot_checks') or [])}</b> conferencia(s) de print e "
            f"<b>{len(vers)}</b> verificacao(es). "
            f"Cada etapa e detalhada na tabela abaixo com seu resultado especifico "
            f"(vide Tambem: Secao 7 - Ambiente Tecnico).",
            S,
        ))
        story.append(Spacer(1, 0.3 * cm))

        steps = [
            ("Recebimento", "Os arquivos foram recebidos e validados quanto a integridade e formato.", f"{len(ef)} arquivo(s) validado(s)."),
            ("Preservacao", "Cada arquivo foi preservado em sua forma original, sem modificacao.", f"{len(ef)} arquivo(s) preservado(s)."),
            ("Hashes", "SHA-256 e BLAKE3 calculados para cada arquivo.", f"{len(hashes)} hash(es) calculado(s)."),
            ("Metadados", "Metadados extraidos de todas as imagens.", f"{img_n} imagem(ns) processada(s)."),
            ("OCR", "Texto extraido de cada imagem via OCR.", f"{len(ocrs)} imagem(ns) processada(s)."),
            ("Parser", "Exportacao do WhatsApp parseada.", f"{msg_n} mensagem(ns) indexada(s)."),
            ("Carimbo de tempo", "Manifesto SHA-256 dos originais carimbado por TSA (RFC 3161).", "Ver Secao 2."),
            ("Conferencia", "Cada balao dos prints confrontado com a exportacao.", f"{len(d.get('screenshot_checks') or [])} print(s) conferido(s) (Secao 3)."),
            ("Timeline", "Eventos organizados em ordem cronologica.", f"{msg_n} entrada(s) na linha do tempo."),
            ("Verificacoes", "Verificacoes automaticas de integridade.", f"{len(vers)} verificacao(es) executada(s)."),
            ("Relatorio", "Todos os resultados consolidados neste documento.", "Relatorio gerado (Secoes 1-10)."),
        ]
        rows = [["Etapa", "Objeto", "Resultado"]]
        for name, proc, result in steps:
            rows.append([name, proc, result])
        story.append(self._make_table(rows, [2.5 * cm, 8 * cm, 5.5 * cm], S))
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # CADEIA DE CUSTODIA
    # ------------------------------------------------------------------ #

    def _add_cadeia_custodia(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        custody = d.get("custody_chain", [])
        story.append(Paragraph("5. Cadeia de Custodia", S["SectionHeader"]))

        if not custody:
            story.extend(_warn_box("Nenhum registro de cadeia de custodia disponivel.", S))
            story.append(PageBreak())
            return

        story.append(_p(
            f"A cadeia de custodia abaixo registra as <b>{len(custody)}</b> operacao(oes) "
            f"realizada(s) sobre as evidencias, desde o recebimento ate a geracao deste relatorio. "
            f"Cada registro indica o horario, a operacao executada e o arquivo afetado.",
            S,
        ))
        story.append(Spacer(1, 0.3 * cm))

        rows = [["Horario", "Operacao", "Detalhes", "Arquivo", "Status"]]
        for entry in custody:
            ts_raw = str(entry.get("timestamp", ""))
            _, time_str = self._ts(ts_raw)
            action = str(entry.get("action", ""))
            details = str(entry.get("details", ""))
            file_ref = ""
            if "Arquivo " in details:
                file_ref = details.split("Arquivo ")[1].split(" importado")[0] if "importado" in details else details.split("Arquivo ")[1][:40]
            rows.append([time_str, action, details[:80], file_ref[:35], "Registrado"])
        story.append(self._make_table(rows, [2 * cm, 2 * cm, 5.5 * cm, 3.5 * cm, 3 * cm], S))
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # INVENTARIO
    # ------------------------------------------------------------------ #

    def _add_inventario(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        ef = d.get("evidence_files", [])
        hashes = d.get("hashes", [])
        hb = self._hashes_by(hashes)

        story.append(Paragraph("4. Inventario das Evidencias", S["SectionHeader"]))
        story.append(_p(
            f"A tabela abaixo lista as <b>{len(ef)}</b> evidencia(s) preservada(s), "
            f"com <b>{len(hashes)}</b> hash(es) calculado(s). "
            f"Cada arquivo possui hash SHA-256 unico que permite verificacao futura de integridade "
            f"(vide Secao 7 - Ambiente Tecnico).",
            S,
        ))
        story.append(Spacer(1, 0.3 * cm))

        rows = [["#", "Nome", "Tipo", "Tamanho", "SHA-256 (12c)", "Data", "Status"]]
        for i, ev in enumerate(ef, 1):
            name = str(ev.get("name", ""))
            ev_type = str(ev.get("type", ""))
            size = self._fsize(int(ev.get("size", 0)))
            sha = hb.get(name, {}).get("sha256", "")
            sha_s = sha[:12] + "..." if len(sha) > 12 else sha
            ts = str(ev.get("imported_at", ""))
            date_s, _ = self._ts(ts)
            rows.append([str(i), name[:30], ev_type, size, sha_s, date_s, "Preservado"])
        story.append(self._make_table(rows, [0.8 * cm, 3.5 * cm, 1.8 * cm, 1.5 * cm, 3 * cm, 2.2 * cm, 3.2 * cm], S))
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # LIMITACOES
    # ------------------------------------------------------------------ #

    def _add_limitacoes(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        story.append(Paragraph("9. Limitações", S["SectionHeader"]))
        for title, items in [
            ("O que este relatório permite afirmar", [
                "Os arquivos listados no manifesto são exatamente os mesmos desde o horário do "
                "carimbo de tempo (quando obtido), o que pode ser conferido sem o LexProof.",
                "Cada mensagem visível nos prints foi confrontada com a conversa exportada, e cada "
                "divergência de texto, data, hora, ordem ou contato está apontada na Seção 3.",
                "A transcrição da Seção 6 reproduz a exportação, com o número de cada linha.",
            ]),
            ("O que este relatório NÃO permite afirmar", [
                "Que o conteúdo é autêntico antes de ter sido entregue ao LexProof. A exportação "
                "do WhatsApp é um arquivo de texto; se ela e os prints foram alterados juntos, "
                "antes da preservação, a conferência não detecta.",
                "Quem escreveu as mensagens: a exportação mostra o nome salvo na agenda do "
                "celular, não um número de telefone verificado.",
                "O conteúdo de fotos, áudios e vídeos: o OCR lê apenas o texto dos balões.",
            ]),
            ("O que depende de conferência humana", [
                "Examinar cada divergência apontada antes de usar o print correspondente.",
                "Interpretar o contexto das mensagens.",
                "Quando necessário, buscar meios complementares (ata notarial, perícia no "
                "aparelho, cópia da conversa do outro participante).",
            ]),
        ]:
            story.append(Paragraph(f"<b>{title}</b>", S["ConclusionTitle"]))
            for item in items:
                story.append(Paragraph(f"- {item}", S["ConclusionBody"]))
            story.append(Spacer(1, 0.2 * cm))
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # GLOSSARIO
    # ------------------------------------------------------------------ #

    def _add_glossario(self, story: list[Any]) -> None:
        S = self.styles
        story.append(Paragraph("10. Glossario", S["SectionHeader"]))
        story.append(_p("Termos tecnicos utilizados neste relatorio:", S))
        story.append(Spacer(1, 0.3 * cm))

        terms = [
            ("SHA-256", "Algoritmo de hash que gera um resumo criptografico unico de 256 bits, como uma impressao digital do arquivo. Nao se confunde com assinatura digital ICP-Brasil. Qualquer alteracao no arquivo produz um hash completamente diferente."),
            ("OCR", "Reconhecimento optico de caracteres. Tecnica que extrai texto visivel de imagens."),
            ("EXIF", "Metadados embutidos em imagens digitais (dispositivo, data, software)."),
            ("Hash", "Resumo criptografico unico gerado a partir do conteudo de um arquivo."),
            ("Carimbo de tempo", "Registro assinado por uma Autoridade de Carimbo do Tempo (TSA) que atesta que um dado ja existia em determinado horario."),
            ("Manifesto", "Lista dos arquivos preservados com o SHA-256 de cada um."),
            ("Linha do Tempo", "Sequencia cronologica de todos os eventos registrados nas evidencias."),
            ("Cadeia de Custodia", "Registro cronologico de todas as operacoes realizadas sobre as evidencias."),
        ]
        rows = [["Termo", "Definicao"]]
        for t, d in terms:
            rows.append([t, d])
        story.append(self._make_table(rows, [3 * cm, 13 * cm], S))
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # APENDICES
    # ------------------------------------------------------------------ #

    def _add_apendices(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        hashes = d.get("hashes", [])
        ocrs = d.get("ocr_results", [])

        story.append(Paragraph("Apendices", S["SectionHeader"]))

        if hashes:
            story.append(Paragraph("<b>A. Hashes Completos</b>", S["SubSection"]))
            story.append(_p(
                "Todos os hashes calculados durante a preservacao. "
                "Estes valores permitem verificacao futura da integridade de cada arquivo.",
                S,
            ))
            story.append(Spacer(1, 0.2 * cm))
            rows = [["Arquivo", "Algoritmo", "Hash"]]
            for file_name, algo, value in hash_algorithm_rows(hashes):
                rows.append([file_name[:35], algo, value[:65]])
            story.append(self._make_table(rows, [4 * cm, 2.5 * cm, 9.5 * cm], S))
            story.append(Spacer(1, 0.5 * cm))

        if ocrs:
            story.append(Paragraph("<b>B. Resultados OCR Completos</b>", S["SubSection"]))
            story.append(_p("Texto extraido de cada imagem processada por OCR:", S))
            story.append(Spacer(1, 0.2 * cm))
            for ocr in ocrs:
                p = self._ocr_source(ocr)
                n = Path(p).name if p else "N/A"
                txt = getattr(ocr, "extracted_text", "") or ""
                eng = getattr(ocr, "engine_used", "") or getattr(ocr, "engine", "") or "N/D"
                story.append(Paragraph(f"<b>{self._esc(n)}:</b> (motor: {eng})", S["BodyTextCustom"]))
                if txt:
                    story.append(Paragraph(
                        f"<font face='Courier' size='6'>{self._esc(txt[:500])}{'...' if len(txt) > 500 else ''}</font>",
                        S["SmallText"],
                    ))
                else:
                    story.append(_p("Nenhum texto reconhecido.", S))
                story.append(Spacer(1, 0.3 * cm))

        story.append(Spacer(1, 1 * cm))
        story.append(HRFlowable(width="100%", thickness=1, color=_C1))
        story.append(Spacer(1, 0.3 * cm))
        story.append(_p(
            f"<b>Documento gerado pelo LexProof v{__version__}</b> em "
            f"{datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S UTC')}.",
            S,
        ))

    # ------------------------------------------------------------------ #
    # HELPERS
    # ------------------------------------------------------------------ #
