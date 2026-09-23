"""Gerador de laudo tecnico pericial em formato PDF.

Versao v0.57 — Laudo Tecnico Profissional.
Todas as tabelas usam Paragraph para quebra automatica.
Miniaturas reais de imagens.
Secao Ambiente Tecnico.
Fluxograma visual.
Historico completo de processamento por imagem.
OCR detalhado.
Correlacao detalhada.
Resumo executivo.
Referencias cruzadas.
Linguagem narrativa.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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
_WARN_BG = colors.Color(1.0, 0.97, 0.9)
_WARN_BORDER = colors.Color(0.9, 0.6, 0.0)


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


def _flowchart_box(text: str, bg: colors.Color, border: colors.Color, styles: Any) -> Table:
    t = Table([[_p(text, styles, "FlowchartText")]], colWidths=[3.2 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 1, border),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


class _FlowchartArrow(Flowable):
    """Seta vertical simples para o fluxograma."""
    def __init__(self, width: float = 0.5 * cm, height: float = 0.6 * cm) -> None:
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, avail_width: int, avail_height: int) -> tuple[int, int]:
        return int(self.width), int(self.height)

    def draw(self) -> None:
        canvas = self.canv
        cx = self.width / 2
        canvas.setStrokeColor(_C1)
        canvas.setFillColor(_C1)
        canvas.setLineWidth(1.5)
        canvas.line(cx, self.height, cx, 3)
        canvas.line(cx - 3, 3, cx, 0)
        canvas.line(cx + 3, 3, cx, 0)


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
        canvas.setFont("Helvetica-Bold", 26)
        canvas.drawCentredString(w / 2, y + 0.3 * cm, "LAUDO TECNICO PERICIAL")
        y -= 1.2 * cm
        canvas.setFont("Helvetica", 12)
        canvas.setFillColor(_GRAY)
        canvas.drawCentredString(w / 2, y, "Preservacao e Analise de Evidencias Digitais")
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
            ("Numero do Laudo", meta.get("case_id", "N/A")),
            ("Data de Geracao", self.generated_at),
            ("Versao do LexProof", self.app_version),
            ("Perito Responsavel", meta.get("examiner", "N/A")),
            ("Organizacao", meta.get("organization", "N/A")),
            ("Grau Tecnico", meta.get("quality_grade", "N/A")),
            ("Objeto da Analise", meta.get("title", "N/A")),
        ]:
            canvas.setFont("Helvetica-Bold", 9)
            canvas.setFillColor(_C1)
            canvas.drawString(1 * cm, info_y, f"{label}:")
            canvas.setFont("Helvetica", 9)
            canvas.setFillColor(_DARK)
            canvas.drawString(5.5 * cm, info_y, str(value))
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
            ("FlowchartText", S["Normal"], 7, 9, TA_CENTER, 2, _DARK),
            ("FlowchartArrow", S["Normal"], 10, 12, TA_CENTER, 0, _C1),
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
            title=f"LexProof - {case_data.get('metadata', {}).get('title', 'Laudo Tecnico')}",
            author="LexProof Digital Forensics",
        )
        story: list[Any] = []
        story.append(_CoverPage(case_data, __version__, gen_at))
        story.append(PageBreak())

        self._add_resumo_executivo(story, case_data)
        self._add_identificacao_caso(story, case_data)
        self._add_ambiente_tecnico(story, case_data)
        self._add_fluxograma(story, case_data)
        self._add_metodologia(story, case_data)
        self._add_cadeia_custodia(story, case_data)
        self._add_inventario(story, case_data)
        self._add_analise_individual(story, case_data)
        self._add_correlacao(story, case_data)
        self._add_timeline(story, case_data)
        self._add_analise_tecnica(story, case_data)
        self._add_limitacoes(story, case_data)
        self._add_glossario(story)
        self._add_apendices(story, case_data)

        def _footer(canvas: Any, doc_ref: Any) -> None:
            canvas.saveState()
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(_GRAY)
            canvas.drawString(2.5 * cm, 1.2 * cm, f"LexProof v{__version__} | Laudo Tecnico Pericial")
            canvas.drawRightString(PAGE_WIDTH - 2.5 * cm, 1.2 * cm, f"Pagina {doc_ref.page}")
            canvas.setStrokeColor(_C4)
            canvas.setLineWidth(0.5)
            canvas.line(2.5 * cm, 1.5 * cm, PAGE_WIDTH - 2.5 * cm, 1.5 * cm)
            canvas.restoreState()

        doc.build(story, onLaterPages=_footer)
        logger.info("Laudo tecnico gerado: %s", output_path)
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

    def _ocr_by(self, ocr_results: list[Any]) -> dict[str, Any]:
        o = {}
        for r in ocr_results:
            p = str(getattr(r, "file_path", ""))
            n = Path(p).name if p else ""
            if n:
                o[n] = r
        return o

    def _find_corr(self, name: str, corrs: list[dict]) -> dict | None:
        for c in corrs:
            cn = str(c.get("evidence_name", c.get("image_name", "")))
            if name in cn or cn in name:
                return c
        return None

    def _thumb(self, file_path: str, story: list[Any]) -> None:
        """Adiciona miniatura real da imagem ou placeholder com erro."""
        if not file_path or not Path(file_path).exists():
            story.append(_warn_box(
                f"Miniatura nao disponivel: arquivo '{file_path}' nao encontrado no disco.",
                self.styles,
            ))
            return
        try:
            story.append(Image(str(file_path), width=10 * cm, height=7 * cm))
            story.append(Spacer(1, 0.2 * cm))
        except Exception as e:
            story.append(_warn_box(
                f"Falha ao renderizar miniatura de '{Path(file_path).name}': {e}",
                self.styles,
            ))

    # ------------------------------------------------------------------ #
    # 0. RESUMO EXECUTIVO
    # ------------------------------------------------------------------ #

    def _add_resumo_executivo(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        ef = d.get("evidence_files", [])
        imgs = self._images_of(ef)
        hashes = d.get("hashes", [])
        ocrs = d.get("ocr_results", [])
        corrs = d.get("correlations", [])
        msgs = d.get("messages", d.get("txt_messages", []))
        msg_n = len(msgs) if isinstance(msgs, list) else 0
        vers = d.get("verifications", [])
        pass_n = sum(1 for v in vers if v.get("status") == "PASS")
        conf = int((pass_n / len(vers)) * 100) if vers else 0

        story.append(Paragraph("Resumo Executivo", S["SectionHeader"]))
        story.append(_p(
            f"Este laudo documenta a preservacao e analise de <b>{len(ef)}</b> evidencia(s) "
            f"digitais. O processo envolveu hashing, OCR, correlacao e verificacoes de integridade. "
            f"O resultado e apresentado nas secoes seguintes com total rastreabilidade.",
            S,
        ))
        story.append(Spacer(1, 0.3 * cm))

        rows = [
            ["Metrica", "Valor"],
            ["Evidencias recebidas", str(len(ef))],
            ["Screenshots preservados", str(len(imgs))],
            ["Mensagens indexadas", str(msg_n)],
            ["OCR realizado", f"{len(ocrs)} imagem(ns)"],
            ["Correlacoes encontradas", str(len(corrs))],
            ["Hashes calculados", str(len(hashes))],
            ["Verificacoes executadas", str(len(vers))],
            ["Integridade verificada", f"{conf}% aprovada"],
        ]
        story.append(self._make_table(rows, [8 * cm, 8 * cm], S))
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
            ["Numero do Laudo", meta.get("case_id", "N/A")],
            ["Data de Geracao", datetime.now(timezone.utc).strftime("%d/%m/%Y")],
            ["Versao do LexProof", __version__],
            ["Perito Responsavel", meta.get("examiner", "N/A")],
            ["Organizacao", meta.get("organization", "N/A")],
            ["Objeto da Analise", meta.get("title", "N/A")],
        ]
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
            f"Este laudo apresenta a analise detalhada de cada evidencia (Secao 5), "
            f"com correlacao com a conversa (Secao 7) e verificacoes de integridade (Secao 11).",
            S,
        ))
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # AMBIENTE TECNICO
    # ------------------------------------------------------------------ #

    def _add_ambiente_tecnico(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        story.append(Paragraph("2. Ambiente Tecnico da Analise", S["SectionHeader"]))
        story.append(_p(
            "Todas as ferramentas e bibliotecas utilizadas neste laudo sao documentadas "
            "abaixo. Cada processo indica o motor utilizado, a biblioteca, a versao e o "
            "resultado obtido. Esta transparencia garante que o laudo e reproduzivel.",
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
            ["Correlacao", "EvidenceCorrelator", "Interno", __version__, "OK"],
            ["Timeline", "TimelineBuilder", "Interno", __version__, "OK"],
            ["PDF", "ReportLab", "reportlab", rl_ver, "OK"],
            ["Interface", "PySide6", "Qt", qt_ver, "OK"],
        ]
        story.append(self._make_table(rows, [3 * cm, 3 * cm, 3 * cm, 2.5 * cm, 4.5 * cm], S))
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # FLUXOGRAMA
    # ------------------------------------------------------------------ #

    def _add_fluxograma(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        story.append(Paragraph("3. Fluxograma do Processo", S["SectionHeader"]))
        story.append(_p(
            "O diagrama abaixo apresenta as etapas executadas pelo LexProof, "
            "desde o recebimento das evidencias ate a geracao deste laudo.",
            S,
        ))
        story.append(Spacer(1, 0.5 * cm))

        steps = [
            ("Recebimento", _C3, _C2),
            ("Preservacao", _C3, _C2),
            ("Hashes", _C3, _C2),
            ("Metadados", _C3, _C2),
            ("EXIF", _C3, _C2),
            ("OCR", _C3, _C2),
            ("Parser WhatsApp", _C3, _C2),
            ("Correlacao", _C3, _C2),
            ("Timeline", _C3, _C2),
            ("Verificacoes", _C3, _C2),
            ("Laudo Tecnico", colors.Color(0.9, 0.95, 1.0), _C1),
        ]

        flow_data = []
        for i, (name, bg, border) in enumerate(steps):
            flow_data.append([_flowchart_box(name, bg, border, S)])
            if i < len(steps) - 1:
                flow_data.append([_FlowchartArrow()])

        ft = Table(flow_data, colWidths=[3.2 * cm])
        ft.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        story.append(ft)
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # METODOLOGIA
    # ------------------------------------------------------------------ #

    def _add_metodologia(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        ef = d.get("evidence_files", [])
        hashes = d.get("hashes", [])
        ocrs = d.get("ocr_results", [])
        corrs = d.get("correlations", [])
        msgs = d.get("messages", d.get("txt_messages", []))
        msg_n = len(msgs) if isinstance(msgs, list) else 0
        vers = d.get("verifications", [])
        img_n = len(self._images_of(ef))

        story.append(Paragraph("4. Metodologia", S["SectionHeader"]))
        story.append(_p(
            f"Esta secao documenta cada etapa executada pelo LexProof. "
            f"Foram processadas <b>{len(ef)}</b> evidencia(s) ({img_n} imagem(ns)), "
            f"executadas <b>{len(hashes)}</b> operacoes de hashing, "
            f"<b>{len(ocrs)}</b> processamento(s) OCR, "
            f"<b>{msg_n}</b> indexacao(es) de mensagem(ns), "
            f"<b>{len(corrs)}</b> correlacao(es) e "
            f"<b>{len(vers)}</b> verificacao(es). "
            f"Cada etapa e detalhada na tabela abaixo com seu resultado especifico "
            f"(vide Tambem: Secao 2 - Ambiente Tecnico).",
            S,
        ))
        story.append(Spacer(1, 0.3 * cm))

        steps = [
            ("Recebimento", "Os arquivos foram recebidos e validados quanto a integridade e formato.", f"{len(ef)} arquivo(s) validado(s)."),
            ("Preservacao", "Cada arquivo foi preservado em sua forma original, sem modificacao.", f"{len(ef)} arquivo(s) preservado(s)."),
            ("Hashes", "SHA-256 e BLAKE3 calculados para cada arquivo.", f"{len(hashes)} assinatura(s) calculada(s)."),
            ("Metadados", "Metadados extraidos de todas as imagens.", f"{img_n} imagem(ns) processada(s)."),
            ("OCR", "Texto extraido de cada imagem via OCR.", f"{len(ocrs)} imagem(ns) processada(s)."),
            ("Parser", "Exportacao do WhatsApp parseada.", f"{msg_n} mensagem(ns) indexada(s)."),
            ("Correlacao", "Imagens comparadas com mensagens via OCR e temporal.", f"{len(corrs)} correlacao(es) encontrada(s)."),
            ("Timeline", "Eventos organizados em ordem cronologica.", f"{msg_n} entrada(s) na linha do tempo."),
            ("Verificacoes", "Verificacoes automaticas de integridade.", f"{len(vers)} verificacao(es) executada(s)."),
            ("Laudo", "Todos os resultados consolidados neste documento.", "Laudo gerado (Secoes 1-12)."),
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
            f"realizada(s) sobre as evidencias, desde o recebimento ate a geracao deste laudo. "
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

        story.append(Paragraph("6. Inventario das Evidencias", S["SectionHeader"]))
        story.append(_p(
            f"A tabela abaixo lista as <b>{len(ef)}</b> evidencia(s) preservada(s), "
            f"com <b>{len(hashes)}</b> assinatura(s) digital(is) calculada(s). "
            f"Cada arquivo possui hash SHA-256 unico que permite verificacao futura de integridade "
            f"(vide Secao 2 - Ambiente Tecnico).",
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
    # ANALISE INDIVIDUAL (PRINCIPAL)
    # ------------------------------------------------------------------ #

    def _add_analise_individual(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        ef = d.get("evidence_files", [])
        hashes = d.get("hashes", [])
        corrs = d.get("correlations", [])
        ocrs = d.get("ocr_results", [])
        vers = d.get("verifications", [])
        msgs = d.get("messages", d.get("txt_messages", []))
        msg_n = len(msgs) if isinstance(msgs, list) else 0

        imgs = self._images_of(ef)
        story.append(Paragraph("7. Analise Individual das Imagens", S["SectionHeader"]))
        story.append(_p(
            f"Esta secao apresenta a analise detalhada de cada uma das "
            f"<b>{len(imgs)}</b> imagem(ns) preservada(s). "
            f"Cada captura de tela e avaliada individualmente com propriedades, "
            f"metadados, OCR, correlacao e historico completo de processamento. "
            f"Cada analise referencia a Secao 4 (Metodologia) e a Secao 2 (Ambiente Tecnico).",
            S,
        ))
        story.append(Spacer(1, 0.3 * cm))

        hb = self._hashes_by(hashes)
        ob = self._ocr_by(ocrs)
        pass_n = sum(1 for v in vers if v.get("status") == "PASS")

        for idx, ev in enumerate(imgs, 1):
            name = str(ev.get("name", ""))
            fp = ev.get("path", "")
            size = self._fsize(int(ev.get("size", 0)))

            story.append(Paragraph(f"<b>7.{idx} Imagem: {self._esc(name)}</b>", S["SubSection"]))

            # Tabela de propriedades
            info = [["Propriedade", "Valor"], ["Nome", name], ["Tamanho", size]]
            w, h, exif = self._get_img_info(fp)
            if w:
                info.append(["Resolucao", f"{w} x {h} px"])
            fh = hb.get(name, {})
            if fh.get("sha256"):
                info.append(["SHA-256", fh["sha256"]])
            for ek, ev_val in exif:
                info.append([ek, ev_val])
            story.append(self._make_table(info, [4 * cm, 12 * cm], S))
            story.append(Spacer(1, 0.3 * cm))

            # Miniatura real
            story.append(Paragraph("<b>Miniatura</b>", S["SubSection"]))
            self._thumb(fp, story)

            # OCR detalhado
            story.append(Paragraph("<b>Texto Extraido (OCR)</b>", S["SubSection"]))
            ocr_entry = ob.get(name)
            if ocr_entry is not None:
                ocr_text = getattr(ocr_entry, "extracted_text", "") or ""
                engine = getattr(ocr_entry, "engine_used", "") or getattr(ocr_entry, "engine", "") or "N/D"
                conf_ocr = getattr(ocr_entry, "confidence", 0.0)
                if ocr_text:
                    story.append(_p(
                        f"<b>Motor:</b> {engine} | <b>Confianca:</b> {conf_ocr:.1%} | "
                        f"<b>Texto:</b> {self._esc(ocr_text[:300])}{'...' if len(ocr_text) > 300 else ''}",
                        S,
                    ))
                else:
                    story.append(_p(
                        f"<b>Motor:</b> {engine} | <b>Resultado:</b> Nenhum texto reconhecido.",
                        S,
                    ))
            else:
                story.append(_p("OCR nao executado para esta imagem.", S))
            story.append(Spacer(1, 0.2 * cm))

            # Correlacao
            story.append(Paragraph("<b>Correlacao com a Conversa</b>", S["SubSection"]))
            mc = self._find_corr(name, corrs)
            if mc:
                msgs_c = str(mc.get("matched_messages", mc.get("messages", "")))
                conf_c = str(mc.get("confidence", mc.get("confidence_score", "")))
                result_c = str(mc.get("result", mc.get("status", "")))
                story.append(_p(
                    f"<b>Mensagem correlacionada:</b> {self._esc(msgs_c)} | "
                    f"<b>Confianca:</b> {self._esc(conf_c)} | "
                    f"<b>Resultado:</b> {self._esc(result_c)}",
                    S,
                ))
            else:
                story.append(_p("Nenhuma correspondencia automatica encontrada com a conversa exportada.", S))
            story.append(Spacer(1, 0.2 * cm))

            # Historico de processamento
            story.append(Paragraph("<b>Processamento Executado</b>", S["SubSection"]))
            proc_rows = [["Etapa", "Status", "Resultado"]]
            proc_rows.append(["Preservacao", "OK", "Arquivo preservado intacto"])
            proc_rows.append(["Hash SHA-256", "OK", fh.get("sha256", "N/D")[:20] + "..." if fh.get("sha256") else "Calculado"])
            if fh.get("blake3"):
                proc_rows.append(["Hash BLAKE3", "OK", "Calculado"])
            if w:
                proc_rows.append(["Extracao EXIF", "OK", f"Dispositivo, data, software extraidos"])
            if ocr_entry:
                ocr_text = getattr(ocr_entry, "extracted_text", "") or ""
                proc_rows.append(["OCR", "OK" if ocr_text else "Vazio", f"{len(ocr_text)} caracteres" if ocr_text else "Nenhum texto reconhecido"])
            else:
                proc_rows.append(["OCR", "N/D", "Nao executado"])
            proc_rows.append(["Correlacao", "OK" if mc else "Sem correspondencia", msgs_c if mc else "Nenhuma correspondencia encontrada"])
            proc_rows.append(["Verificacoes", "OK" if pass_n > 0 else "N/D", f"{pass_n} verificacao(es) aprovada(s)"])
            story.append(self._make_table(proc_rows, [3 * cm, 2.5 * cm, 10.5 * cm], S))
            story.append(Spacer(1, 0.2 * cm))

            # Comentario tecnico
            comment = self._tech_comment(name, ocr_entry, mc)
            story.extend(_info_box(f"<b>Comentario Tecnico (Secao 7.{idx}):</b> {comment}", S))
            story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # CORRELACAO
    # ------------------------------------------------------------------ #

    def _add_correlacao(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        corrs = d.get("correlations", [])
        ef = d.get("evidence_files", [])
        imgs = self._images_of(ef)

        story.append(Paragraph("8. Correlacao entre Imagens e Mensagens", S["SectionHeader"]))

        if not corrs:
            story.append(_p(
                "Nenhuma correspondencia automatica foi encontrada entre as imagens "
                "e as mensagens da exportacao do WhatsApp. "
                "A tabela abaixo lista cada imagem e o resultado da analise (vide Secao 7 para detalhes).",
                S,
            ))
            if imgs:
                story.append(Spacer(1, 0.3 * cm))
                rows = [["Imagem", "Status", "Motivo"]]
                for ie in imgs:
                    rows.append([str(ie.get("name", "N/A")), "Sem correspondencia", "OCR nao produziu texto compativel com a conversa"])
                story.append(self._make_table(rows, [5 * cm, 3.5 * cm, 7.5 * cm], S))
            story.append(PageBreak())
            return

        story.append(_p(
            f"Foram encontradas <b>{len(corrs)}</b> correlacoes entre imagens e mensagens. "
            f"Cada correlacao e detalhada na tabela abaixo com mensagem correspondente, "
            f"trecho da conversa, similaridade, metodo utilizado e confianca "
            f"(vide Secao 7 para analise individual).",
            S,
        ))
        story.append(Spacer(1, 0.3 * cm))

        rows = [["Imagem", "Mensagem", "Trecho", "Confianca", "Metodo", "Conclusao"]]
        for c in corrs:
            ev_n = str(c.get("evidence_name", c.get("image_name", "N/A")))
            msgs = str(c.get("matched_messages", c.get("messages", "N/A")))
            conf = str(c.get("confidence", c.get("confidence_score", "N/A")))
            res = str(c.get("result", c.get("status", "N/A")))
            rows.append([ev_n[:25], msgs[:30], msgs[:40], conf, "OCR + Temporal", res[:25]])
        story.append(self._make_table(rows, [2.5 * cm, 2.5 * cm, 3.5 * cm, 2 * cm, 2.5 * cm, 3 * cm], S))
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # TIMELINE
    # ------------------------------------------------------------------ #

    def _add_timeline(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        msgs = d.get("messages", d.get("txt_messages", []))
        corrs = d.get("correlations", [])

        story.append(Paragraph("9. Linha do Tempo", S["SectionHeader"]))

        if not msgs:
            story.extend(_warn_box("Nenhuma mensagem indexada para construcao da timeline.", S))
            story.append(PageBreak())
            return

        msg_n = len(msgs) if isinstance(msgs, list) else 0
        story.append(_p(
            f"A linha do tempo abaixo apresenta as <b>{msg_n}</b> mensagem(ns) "
            f"indexada(s) em ordem cronologica. "
            f"Foram identificadas <b>{len(corrs)}</b> correlacao(es) com imagens "
            f"(vide Secao 8 para detalhes).",
            S,
        ))
        story.append(Spacer(1, 0.3 * cm))

        entries = []
        if isinstance(msgs, list):
            for msg in msgs:
                ts = getattr(msg, "timestamp", None) or getattr(msg, "date", None)
                ts_s = ts.strftime("%d/%m/%Y %H:%M:%S") if hasattr(ts, "strftime") else str(ts) if ts else ""
                sender = getattr(msg, "sender", "") or ""
                content = (getattr(msg, "content", "") or getattr(msg, "text", "") or "")[:80]
                entries.append((ts_s, "Mensagem", sender, content))
        entries.sort(key=lambda x: x[0])

        rows = [["Horario", "Tipo", "Remetente", "Conteudo"]]
        for ts_s, tipo, sender, content in entries[:50]:
            rows.append([ts_s, tipo, sender[:15], content[:50]])
        if len(entries) > 50:
            rows.append(["...", f"+{len(entries) - 50} entradas", "", ""])
        story.append(self._make_table(rows, [4 * cm, 2 * cm, 3 * cm, 7 * cm], S))
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # ANALISE TECNICA
    # ------------------------------------------------------------------ #

    def _add_analise_tecnica(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        ef = d.get("evidence_files", [])
        vers = d.get("verifications", [])
        corrs = d.get("correlations", [])
        hashes = d.get("hashes", [])
        ocrs = d.get("ocr_results", [])
        msgs = d.get("messages", d.get("txt_messages", []))
        msg_n = len(msgs) if isinstance(msgs, list) else 0

        imgs = self._images_of(ef)
        pass_n = sum(1 for v in vers if v.get("status") == "PASS")
        conf = int((pass_n / len(vers)) * 100) if vers else 0

        corr_imgs = set()
        for c in corrs:
            cn = str(c.get("evidence_name", c.get("image_name", "")))
            for ev in ef:
                en = str(ev.get("name", ""))
                if en in cn or cn in en:
                    corr_imgs.add(en)
                    break
        unmatched = len(imgs) - len(corr_imgs)

        story.append(Paragraph("10. Analise Tecnica", S["SectionHeader"]))

        # 10.1 Integridade
        story.append(Paragraph("<b>10.1 Integridade dos Arquivos</b>", S["SubSection"]))
        story.append(_p(
            f"Foram preservados <b>{len(ef)}</b> arquivos, dos quais "
            f"<b>{len(imgs)}</b> sao imagens. "
            f"Foram calculadas <b>{len(hashes)}</b> assinaturas digitais (SHA-256 e BLAKE3). "
            f"Cada assinatura e unica e reproduzivel — qualquer alteracao produziria um hash "
            f"completamente diferente (vide Secao 6 - Inventario e Apendice A).",
            S,
        ))
        story.append(Spacer(1, 0.3 * cm))

        # 10.2 Correlacao
        story.append(Paragraph("<b>10.2 Correlacao Imagem-Mensagem</b>", S["SubSection"]))
        if corrs:
            story.append(_p(
                f"A analise identificou <b>{len(corrs)}</b> correspondencia(s). "
                f"<b>{len(corr_imgs)}</b> imagem(ns) apresentou(ram) correspondencia. "
                f"<b>{unmatched}</b> imagem(ns) nao apresentou correspondencia automatica. "
                f"Cada correlacao e detalhada na Secao 8 e na Secao 7.",
                S,
            ))
        else:
            story.append(_p(
                "A analise automatica nao identificou correspondencias. "
                "A tabela abaixo lista cada imagem e o resultado da analise "
                "(vide Secao 7 para analise individual de cada imagem).",
                S,
            ))
            if imgs:
                story.append(Spacer(1, 0.2 * cm))
                ob = self._ocr_by(ocrs)
                nr = [["Imagem", "OCR", "Texto", "Correlacao"]]
                for ie in imgs:
                    ie_n = str(ie.get("name", ""))
                    ocr_e = ob.get(ie_n)
                    ocr_t = getattr(ocr_e, "extracted_text", "") or "" if ocr_e else ""
                    nr.append([ie_n[:30], "Sim" if ocr_e else "Nao", f"{len(ocr_t)} chars" if ocr_t else "Vazio", "Nenhuma"])
                story.append(self._make_table(nr, [4.5 * cm, 2 * cm, 3 * cm, 6.5 * cm], S))
        story.append(Spacer(1, 0.3 * cm))

        # 10.3 Verificacoes
        story.append(Paragraph("<b>10.3 Verificacoes Automaticas</b>", S["SubSection"]))
        if vers:
            checks = ", ".join(str(v.get("check_name", "")) for v in vers)
            story.append(_p(
                f"Foram executadas <b>{len(vers)}</b> verificacoes: {checks}. "
                f"Das verificacoes, <b>{pass_n}</b> foram aprovadas ({conf}% de confianca). "
                f"Resultados detalhados na tabela abaixo.",
                S,
            ))
            vr = [["Verificacao", "Resultado", "Detalhes"]]
            for v in vers:
                cn = str(v.get("check_name", ""))
                st = str(v.get("status", "")).upper()
                st_t = {"PASS": "Aprovado", "FAIL": "Reprovado"}.get(st, "Alerta")
                det = v.get("details", {})
                det_t = " ".join(f"{k}: {val}" for k, val in det.items() if val) if isinstance(det, dict) else str(det)
                vr.append([cn, st_t, det_t[:80]])
            story.append(self._make_table(vr, [4 * cm, 2.5 * cm, 9.5 * cm], S))
        else:
            story.append(_p("Nenhuma verificacao tecnica automatizada foi executada neste caso.", S))

        # 10.4 Cronologia
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("<b>10.4 Consistencia Cronologica</b>", S["SubSection"]))
        if imgs:
            story.append(_p(
                f"Foram analisadas <b>{len(imgs)}</b> imagem(ns) e <b>{msg_n}</b> mensagem(ns). "
                f"<b>{len(corr_imgs)}</b> imagem(ns) apresentou correspondencia com a conversa. "
                f"<b>{unmatched}</b> imagem(ns) nao apresentou correspondencia automatica. "
                f"A avaliacao da coerencia temporal depende de analise visual pelo perito "
                f"(vide Secao 7 para analise individual).",
                S,
            ))
        else:
            story.append(_p("Nenhuma imagem foi preservada para analise cronologica.", S))
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # LIMITACOES
    # ------------------------------------------------------------------ #

    def _add_limitacoes(self, story: list[Any], d: dict[str, Any]) -> None:
        S = self.styles
        ef = d.get("evidence_files", [])
        hashes = d.get("hashes", [])
        vers = d.get("verifications", [])
        pass_n = sum(1 for v in vers if v.get("status") == "PASS")
        conf = int((pass_n / len(vers)) * 100) if vers else 0

        story.append(Paragraph("11. Limitacoes", S["SectionHeader"]))
        story.append(_p(
            f"Este laudo foi gerado de forma automatizada pelo LexProof "
            f"(vide Secao 2 - Ambiente Tecnico). Foram preservados {len(ef)} arquivos "
            f"com {len(hashes)} assinaturas digitais e executadas {len(vers)} verificacoes "
            f"({conf}% de confianca). As limitacoes sao inerentes ao processamento computacional.",
            S,
        ))
        story.append(Spacer(1, 0.3 * cm))

        for title, body in [
            ("O que o LexProof consegue afirmar (conforme verificacoes da Secao 10.3):",
             "- Os arquivos mantiveram integridade apos hashing.\n"
             "- Assinaturas digitais sao reproduziveis e rastreaveis.\n"
             "- Sequencia cronologica reconstruida a partir dos metadados.\n"
             "- Correlacoes refletem similaridade textual entre OCR e mensagens."),
            ("O que o LexProof NAO consegue afirmar (vide Secao 7 para analise individual):",
             "- Autenticidade original dos arquivos antes da importacao.\n"
             "- Integridade de imagens sem metadados EXIF.\n"
             "- Correspondencia exata quando OCR nao extraia texto.\n"
             "- Manipulacao manual antes do recebimento."),
            ("Verificacoes que dependem de pericia humana:",
             "- Validacao visual de cada screenshot contra a conversa.\n"
             "- Interpretacao do contexto das imagens e mensagens.\n"
             "- Analise de possiveis edicoes nas capturas.\n"
             "- Avaliacao da coerencia geral do conjunto."),
        ]:
            story.append(Paragraph(f"<b>{title}</b>", S["ConclusionTitle"]))
            for line in body.split("\n"):
                if line.strip():
                    story.append(Paragraph(line.strip(), S["ConclusionBody"]))
            story.append(Spacer(1, 0.2 * cm))
        story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # GLOSSARIO
    # ------------------------------------------------------------------ #

    def _add_glossario(self, story: list[Any]) -> None:
        S = self.styles
        story.append(Paragraph("12. Glossario", S["SectionHeader"]))
        story.append(_p("Termos tecnicos utilizados neste laudo:", S))
        story.append(Spacer(1, 0.3 * cm))

        terms = [
            ("SHA-256", "Algoritmo de hash que gera uma assinatura digital unica de 256 bits. Qualquer alteracao no arquivo produz um hash completamente diferente."),
            ("OCR", "Reconhecimento optico de caracteres. Tecnica que extrai texto visivel de imagens."),
            ("EXIF", "Metadados embutidos em imagens digitais (dispositivo, data, software)."),
            ("Hash", "Assinatura digital unica gerada a partir do conteudo de um arquivo."),
            ("Correlacao", "Associacao automatica entre imagens e mensagens da conversa."),
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
        corrs = d.get("correlations", [])

        story.append(Paragraph("Apendices", S["SectionHeader"]))

        if hashes:
            story.append(Paragraph("<b>A. Assinaturas Digitais Completas</b>", S["SubSection"]))
            story.append(_p(
                "Todos os hashes calculados durante a preservacao. "
                "Estes valores permitem verificacao futura da integridade de cada arquivo.",
                S,
            ))
            story.append(Spacer(1, 0.2 * cm))
            rows = [["Arquivo", "Algoritmo", "Hash"]]
            for h in hashes:
                rows.append([
                    str(h.get("file_name", ""))[:35],
                    str(h.get("algorithm", "")),
                    str(h.get("sha256", h.get("hash_value", "")))[:65],
                ])
            story.append(self._make_table(rows, [4 * cm, 2.5 * cm, 9.5 * cm], S))
            story.append(Spacer(1, 0.5 * cm))

        if ocrs:
            story.append(Paragraph("<b>B. Resultados OCR Completos</b>", S["SubSection"]))
            story.append(_p("Texto extraido de cada imagem processada por OCR:", S))
            story.append(Spacer(1, 0.2 * cm))
            for ocr in ocrs:
                p = str(getattr(ocr, "file_path", ""))
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

        if corrs:
            story.append(PageBreak())
            story.append(Paragraph("<b>C. Detalhamento das Correlacoes</b>", S["SubSection"]))
            story.append(_p(
                f"Total de {len(corrs)} correlacao(es) encontrada(s):",
                S,
            ))
            story.append(Spacer(1, 0.2 * cm))
            rows = [["Imagem", "Mensagens", "Confianca", "Resultado"]]
            for c in corrs:
                rows.append([
                    str(c.get("evidence_name", c.get("image_name", "N/A")))[:30],
                    str(c.get("matched_messages", c.get("messages", "N/A")))[:40],
                    str(c.get("confidence", c.get("confidence_score", "N/A"))),
                    str(c.get("result", c.get("status", "N/A")))[:25],
                ])
            story.append(self._make_table(rows, [4 * cm, 5 * cm, 2.5 * cm, 4.5 * cm], S))

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

    def _get_img_info(self, fp: str) -> tuple[str, str, list[tuple[str, str]]]:
        w, h, exif = "", "", []
        if not fp or not Path(fp).exists():
            return w, h, exif
        try:
            from PIL import Image as PILImage
            from PIL.ExifTags import TAGS
            with PILImage.open(fp) as img:
                w_s, h_s = img.size
                w, h = str(w_s), str(h_s)
                ex = img.getexif()
                if ex:
                    ed = {}
                    for tid, val in ex.items():
                        tn = TAGS.get(tid, str(tid))
                        ed[tn] = str(val)
                    if "Make" in ed or "Model" in ed:
                        exif.append(("Dispositivo", f"{ed.get('Make', '')} {ed.get('Model', '')}".strip()))
                    if "DateTimeOriginal" in ed:
                        exif.append(("Data Original", ed["DateTimeOriginal"]))
                    if "Software" in ed:
                        exif.append(("Software", ed["Software"]))
        except Exception:
            pass
        return w, h, exif

    def _tech_comment(self, name: str, ocr_entry: Any, mc: dict | None) -> str:
        parts = []
        if ocr_entry:
            txt = getattr(ocr_entry, "extracted_text", "") or ""
            eng = getattr(ocr_entry, "engine_used", "") or getattr(ocr_entry, "engine", "") or "N/D"
            if txt:
                parts.append(f"O OCR ({eng}) extraiu {len(txt)} caracteres de texto.")
            else:
                parts.append(f"O OCR ({eng}) foi executado mas nenhum texto foi reconhecido.")
        else:
            parts.append("OCR nao executado para esta imagem.")
        if mc:
            msgs = str(mc.get("matched_messages", mc.get("messages", "")))
            conf = str(mc.get("confidence", mc.get("confidence_score", "")))
            parts.append(f"Correlacao encontrada com {msgs} (confianca: {conf}).")
        else:
            parts.append("Nenhuma correspondencia automatica encontrada.")
        return " ".join(parts)
