"""Gerador de relatorios tecnicos em formato PDF (laudo tecnico).

Gera documentos PDF profissionais para submissao judicial com
capa, indice, evidencias, hashes, cadeia de custodia e verificacoes.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from lexproof import __version__

logger = logging.getLogger("lexproof.reports.pdf")

PAGE_WIDTH, PAGE_HEIGHT = A4

_HEADER_COLOR = colors.Color(0.1, 0.14, 0.49)
_ACCENT_COLOR = colors.Color(0.0, 0.4, 0.8)
_TABLE_ALT_COLOR = colors.Color(0.95, 0.95, 0.97)
_LIGHT_GRAY = colors.Color(0.92, 0.92, 0.94)
_PASS_GREEN = colors.Color(0.2, 0.69, 0.3)
_FAIL_RED = colors.Color(0.85, 0.15, 0.15)
_WARN_ORANGE = colors.Color(0.9, 0.6, 0.0)


class _CoverPage(Flowable):
    """Flowable rendering the entire cover page."""

    def __init__(
        self,
        case_data: dict[str, Any],
        app_version: str,
        report_generated_at: str,
        report_hash: str,
    ) -> None:
        super().__init__()
        self.case_data = case_data
        self.app_version = app_version
        self.report_generated_at = report_generated_at
        self.report_hash = report_hash
        self.width = PAGE_WIDTH - 5 * cm
        self.height = PAGE_HEIGHT - 5 * cm

    def wrap(self, avail_width: int, avail_height: int) -> tuple[int, int]:
        return int(self.width), int(self.height)

    def draw(self) -> None:
        canvas = self.canv
        meta = self.case_data.get("metadata", {})
        content_width = self.width

        y_cursor = self.height - 2 * cm

        canvas.setFont("Helvetica-Bold", 36)
        canvas.setFillColor(_HEADER_COLOR)
        canvas.drawCentredString(content_width / 2, y_cursor, "LEXPROOF")
        y_cursor -= 1.2 * cm

        canvas.setFont("Helvetica", 14)
        canvas.setFillColor(colors.Color(0.3, 0.3, 0.5))
        canvas.drawCentredString(
            content_width / 2,
            y_cursor,
            "Relatorio de Preservacao de Evidencias Digitais",
        )
        y_cursor -= 1.5 * cm

        canvas.setStrokeColor(_HEADER_COLOR)
        canvas.setLineWidth(2)
        canvas.line(2 * cm, y_cursor, content_width - 2 * cm, y_cursor)
        y_cursor -= 2 * cm

        box_x = 2 * cm
        box_width = content_width - 4 * cm
        box_height = 7 * cm
        box_y = y_cursor - box_height
        canvas.setStrokeColor(_HEADER_COLOR)
        canvas.setLineWidth(1)
        canvas.setFillColor(colors.Color(0.98, 0.98, 1.0))
        canvas.roundRect(box_x, box_y, box_width, box_height, 4, fill=1, stroke=1)

        info_y = box_y + box_height - 1.2 * cm
        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(_HEADER_COLOR)

        fields = [
            ("Numero do Caso", meta.get("case_id", "N/A")),
            ("Titulo", meta.get("title", "N/A")),
            ("Data de Geracao", self.report_generated_at),
            ("Perito Responsavel", meta.get("examiner", "N/A")),
            ("Organizacao", meta.get("organization", "N/A")),
        ]

        for label, value in fields:
            canvas.setFont("Helvetica-Bold", 10)
            canvas.setFillColor(_HEADER_COLOR)
            canvas.drawString(box_x + 1 * cm, info_y, f"{label}:")
            canvas.setFont("Helvetica", 10)
            canvas.setFillColor(colors.Color(0.15, 0.15, 0.15))
            canvas.drawString(box_x + 5 * cm, info_y, str(value))
            info_y -= 1.1 * cm

        y_cursor = box_y - 2 * cm

        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.Color(0.5, 0.5, 0.5))
        canvas.drawCentredString(
            content_width / 2,
            y_cursor,
            f"Documento gerado automaticamente pelo LexProof v{self.app_version}",
        )

        if self.report_hash:
            y_cursor -= 0.8 * cm
            canvas.setFont("Courier", 6)
            canvas.setFillColor(colors.Color(0.55, 0.55, 0.55))
            canvas.drawCentredString(
                content_width / 2,
                y_cursor,
                f"Hash do relatorio: {self.report_hash[:80]}",
            )


class _BarcodeFlowable(Flowable):
    """Visual barcode-like representation of a hash string."""

    _CHAR_COLORS = [
        colors.Color(0.1, 0.14, 0.49),
        colors.Color(0.0, 0.4, 0.8),
        colors.Color(0.2, 0.69, 0.3),
        colors.Color(0.85, 0.15, 0.15),
        colors.Color(0.9, 0.6, 0.0),
    ]

    def __init__(self, hash_value: str, bar_width: float = 1.5 * cm, bar_height: float = 0.6 * cm) -> None:
        super().__init__()
        self.hash_value = hash_value
        self.bar_width = bar_width
        self.bar_height = bar_height
        self.width = bar_width
        self.height = bar_height

    def wrap(self, avail_width: int, avail_height: int) -> tuple[int, int]:
        return int(self.bar_width), int(self.bar_height)

    def draw(self) -> None:
        canvas = self.canv
        num_bars = min(len(self.hash_value), 40)
        bar_w = self.bar_width / num_bars
        for i in range(num_bars):
            char_val = ord(self.hash_value[i]) % 16
            h_ratio = 0.3 + (char_val / 15) * 0.7
            bar_h = self.bar_height * h_ratio
            color = self._CHAR_COLORS[i % len(self._CHAR_COLORS)]
            canvas.setFillColor(color)
            x = i * bar_w
            canvas.rect(x, 0, bar_w * 0.85, bar_h, fill=1, stroke=0)


class PDFReportGenerator:
    """Gera relatorios tecnicos profissionais em formato PDF (laudo tecnico).

    Utiliza reportlab para criar documentos PDF com capa, indice,
    tabelas de evidencias, hashes de integridade, cadeia de custodia
    e resultados de verificacao, aptos para submissao judicial.
    """

    def __init__(self) -> None:
        """Inicializa o gerador PDF com estilos padrao."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self) -> None:
        """Configura estilos personalizados para o documento."""
        self.styles.add(ParagraphStyle(
            name="CoverTitle",
            parent=self.styles["Title"],
            fontSize=28,
            leading=34,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=_HEADER_COLOR,
        ))
        self.styles.add(ParagraphStyle(
            name="CoverSubtitle",
            parent=self.styles["Normal"],
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            spaceAfter=12,
            textColor=colors.Color(0.3, 0.3, 0.5),
        ))
        self.styles.add(ParagraphStyle(
            name="SectionHeader",
            parent=self.styles["Heading1"],
            fontSize=16,
            leading=20,
            spaceBefore=20,
            spaceAfter=10,
            textColor=_HEADER_COLOR,
            borderWidth=1,
            borderColor=_HEADER_COLOR,
            borderPadding=4,
        ))
        self.styles.add(ParagraphStyle(
            name="SubSection",
            parent=self.styles["Heading2"],
            fontSize=12,
            leading=15,
            spaceBefore=12,
            spaceAfter=6,
            textColor=_ACCENT_COLOR,
        ))
        self.styles.add(ParagraphStyle(
            name="BodyTextCustom",
            parent=self.styles["Normal"],
            fontSize=10,
            leading=13,
            spaceAfter=6,
        ))
        self.styles.add(ParagraphStyle(
            name="HashValue",
            parent=self.styles["Code"],
            fontSize=7,
            leading=9,
            wordWrap="CJK",
        ))
        self.styles.add(ParagraphStyle(
            name="TOCItem",
            parent=self.styles["Normal"],
            fontSize=11,
            leading=18,
            leftIndent=1 * cm,
        ))
        self.styles.add(ParagraphStyle(
            name="TableCell",
            parent=self.styles["Normal"],
            fontSize=8,
            leading=10,
        ))
        self.styles.add(ParagraphStyle(
            name="StatusPass",
            parent=self.styles["Normal"],
            fontSize=9,
            textColor=_PASS_GREEN,
        ))
        self.styles.add(ParagraphStyle(
            name="StatusFail",
            parent=self.styles["Normal"],
            fontSize=9,
            textColor=_FAIL_RED,
        ))
        self.styles.add(ParagraphStyle(
            name="StatusWarning",
            parent=self.styles["Normal"],
            fontSize=9,
            textColor=_WARN_ORANGE,
        ))

    def generate(self, case_data: dict[str, Any], output_path: Path) -> Path:
        """Gera o relatorio PDF tecnico completo.

        Cria um documento PDF profissional com capa, indice e todas
        as secoes de dados do caso conforme especificacao judicial.

        Args:
            case_data: Dicionario com os dados do caso. Chaves esperadas:
                - metadata (dict): case_id, title, description, examiner,
                  organization, created_at
                - evidence_files (list): name, path, type, size, imported_at,
                  thumbnail_path
                - hashes (list): file_name, sha256, sha3_512, blake3
                - global_hash (str): hash global do caso
                - custody_chain (list): timestamp, user, action, details
                - verifications (list): check_name, status, details
                - inconsistencies (list[str]): lista de inconsistencias
            output_path: Caminho de saida do arquivo PDF.

        Returns:
            Caminho do arquivo PDF gerado.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report_generated_at = datetime.now(timezone.utc).strftime(
            "%d/%m/%Y %H:%M:%S UTC"
        )

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=2.5 * cm,
            leftMargin=2.5 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title=f"LexProof - {case_data.get('metadata', {}).get('title', 'Relatorio')}",
            author="LexProof Digital Forensics",
        )

        story: list[Any] = []

        story.append(_CoverPage(case_data, __version__, report_generated_at, ""))
        story.append(NextPageTemplate("body"))
        story.append(PageBreak())

        self._add_table_of_contents(story, case_data)
        story.append(PageBreak())

        self._add_resumo_executivo(story, case_data)
        self._add_evidencias_analisadas(story, case_data)
        self._add_hashes_integridade(story, case_data)
        self._add_cadeia_custodia(story, case_data)
        self._add_resultados_verificacao(story, case_data)
        self._add_observacoes(story, case_data)

        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id="body",
        )

        def _footer(canvas: Any, doc_ref: Any) -> None:
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.Color(0.5, 0.5, 0.5))
            canvas.drawString(
                2.5 * cm,
                1.2 * cm,
                f"LexProof v{__version__} | Pagina {doc_ref.page}",
            )
            canvas.drawRightString(
                PAGE_WIDTH - 2.5 * cm,
                1.2 * cm,
                f"Pagina {doc_ref.page} de {doc_ref.page}",
            )
            canvas.restoreState()

        body_template = PageTemplate(
            id="body",
            frames=[frame],
            onPage=_footer,
        )

        cover_frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id="cover",
        )

        def _cover_footer(canvas: Any, doc_ref: Any) -> None:
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.Color(0.5, 0.5, 0.5))
            canvas.drawCentredString(
                PAGE_WIDTH / 2,
                1.2 * cm,
                f"Documento gerado automaticamente pelo LexProof v{__version__}",
            )
            canvas.restoreState()

        cover_template = PageTemplate(
            id="cover",
            frames=[cover_frame],
            onPage=_cover_footer,
        )

        doc.addPageTemplates([cover_template, body_template])

        doc.build(story, onFirstPage=_cover_footer, onLaterPages=_footer)

        report_hash = self._compute_report_hash(output_path)
        logger.info("Relatorio PDF gerado: %s", output_path)
        return output_path

    def _add_table_of_contents(
        self, story: list[Any], case_data: dict[str, Any]
    ) -> None:
        """Adiciona a pagina de indice ao relatorio."""
        story.append(Paragraph("Indice", self.styles["SectionHeader"]))
        story.append(Spacer(1, 0.5 * cm))

        toc_items = [
            "1. Resumo Executivo",
            "2. Evidencias Analisadas",
            "3. Hashes de Integridade",
            "4. Cadeia de Custodia",
            "5. Resultados da Verificacao",
            "6. Observacoes e Inconsistencias",
            "7. Anexos",
        ]

        for item in toc_items:
            story.append(Paragraph(item, self.styles["TOCItem"]))

        story.append(PageBreak())

    def _add_resumo_executivo(
        self, story: list[Any], case_data: dict[str, Any]
    ) -> None:
        """Adiciona a secao de resumo executivo."""
        story.append(Paragraph("1. Resumo Executivo", self.styles["SectionHeader"]))

        meta = case_data.get("metadata", {})
        evidence_files = case_data.get("evidence_files", [])
        verifications = case_data.get("verifications", [])
        inconsistencies = case_data.get("inconsistencies", [])

        title = meta.get("title", "N/A")
        description = meta.get("description", "")
        examiner = meta.get("examiner", "N/A")

        summary_text = (
            f"O presente relatorio apresenta os resultados da preservacao "
            f"e analise de evidencias digitais referentes ao caso "
            f"<b>{self._escape_html(title)}</b>, conduzida pelo perito "
            f"<b>{self._escape_html(examiner)}</b>."
        )
        if description:
            summary_text += f" {self._escape_html(description)}"

        story.append(Paragraph(summary_text, self.styles["BodyTextCustom"]))
        story.append(Spacer(1, 0.3 * cm))

        stats_data = [
            ["Metrica", "Valor"],
            ["Arquivos analisados", str(len(evidence_files))],
            ["Verificacoes realizadas", str(len(verifications))],
            ["Inconsistencias encontradas", str(len(inconsistencies))],
        ]

        pass_count = sum(1 for v in verifications if v.get("status") == "PASS")
        fail_count = sum(1 for v in verifications if v.get("status") == "FAIL")
        warning_count = sum(1 for v in verifications if v.get("status") == "WARNING")

        stats_data.append(["Verificacoes aprovadas", str(pass_count)])
        stats_data.append(["Verificacoes reprovadas", str(fail_count)])
        stats_data.append(["Avisos", str(warning_count)])

        table = Table(stats_data, colWidths=[8 * cm, 5 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _TABLE_ALT_COLOR]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(table)
        story.append(PageBreak())

    def _add_evidencias_analisadas(
        self, story: list[Any], case_data: dict[str, Any]
    ) -> None:
        """Adiciona a secao de evidencias analisadas com tabela e miniaturas."""
        story.append(Paragraph("2. Evidencias Analisadas", self.styles["SectionHeader"]))

        evidence_files = case_data.get("evidence_files", [])
        if not evidence_files:
            story.append(Paragraph(
                "Nenhuma evidencia registrada.", self.styles["BodyTextCustom"]
            ))
            story.append(PageBreak())
            return

        table_data: list[list[Any]] = [
            ["#", "Nome do Arquivo", "Tipo", "Tamanho", "Data de Importacao"]
        ]
        for idx, ev in enumerate(evidence_files, start=1):
            name = self._escape_html(str(ev.get("name", "")))
            ev_type = self._escape_html(str(ev.get("type", "")))
            size_str = self._format_file_size(int(ev.get("size", 0)))
            imported = self._escape_html(str(ev.get("imported_at", "")))
            table_data.append([str(idx), name, ev_type, size_str, imported])

        col_widths = [1 * cm, 5 * cm, 2.5 * cm, 2.5 * cm, 5 * cm]
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (1, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _TABLE_ALT_COLOR]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.5 * cm))

        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
        for ev in evidence_files:
            name = str(ev.get("name", ""))
            ext = Path(name).suffix.lower()
            if ext in image_extensions:
                thumb_path = ev.get("thumbnail_path")
                file_path = ev.get("path")
                img_source = thumb_path or file_path
                if img_source and Path(img_source).exists():
                    story.append(Paragraph(
                        f"<b>{self._escape_html(name)}</b>",
                        self.styles["SubSection"],
                    ))
                    try:
                        story.append(Image(str(img_source), width=6 * cm, height=4 * cm))
                    except Exception:
                        story.append(Paragraph(
                            "[Imagem nao disponivel]",
                            self.styles["BodyTextCustom"],
                        ))
                    story.append(Spacer(1, 0.3 * cm))

        story.append(PageBreak())

    def _add_hashes_integridade(
        self, story: list[Any], case_data: dict[str, Any]
    ) -> None:
        """Adiciona a secao de hashes de integridade."""
        story.append(Paragraph("3. Hashes de Integridade", self.styles["SectionHeader"]))

        hashes = case_data.get("hashes", [])
        if not hashes:
            story.append(Paragraph(
                "Nenhum hash calculado.", self.styles["BodyTextCustom"]
            ))
            story.append(PageBreak())
            return

        for h in hashes:
            file_name = self._escape_html(str(h.get("file_name", "")))
            sha256_val = str(h.get("sha256", ""))
            sha3_val = str(h.get("sha3_512", ""))
            blake3_val = str(h.get("blake3", ""))

            card_data = [
                ["Propriedade", "Valor"],
                ["Arquivo", file_name],
                ["SHA-256", sha256_val],
                ["SHA3-512", sha3_val],
                ["BLAKE3", blake3_val],
            ]

            card_table = Table(card_data, colWidths=[3 * cm, 13 * cm])
            card_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), _ACCENT_COLOR),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 1), (1, -1), "Courier"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _TABLE_ALT_COLOR]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(card_table)

            barcode = _BarcodeFlowable(sha256_val)
            story.append(Spacer(1, 0.2 * cm))
            story.append(barcode)
            story.append(Spacer(1, 0.5 * cm))

        global_hash = case_data.get("global_hash", "")
        if global_hash:
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph(
                "<b>Hash Global do Caso:</b>", self.styles["BodyTextCustom"]
            ))
            story.append(Paragraph(
                self._escape_html(global_hash),
                self.styles["HashValue"],
            ))

        story.append(PageBreak())

    def _add_cadeia_custodia(
        self, story: list[Any], case_data: dict[str, Any]
    ) -> None:
        """Adiciona a secao de cadeia de custodia com estilo timeline."""
        story.append(Paragraph("4. Cadeia de Custodia", self.styles["SectionHeader"]))

        custody_chain = case_data.get("custody_chain", [])
        if not custody_chain:
            story.append(Paragraph(
                "Nenhuma cadeia de custodia registrada.",
                self.styles["BodyTextCustom"],
            ))
            story.append(PageBreak())
            return

        timeline_data: list[list[Any]] = [
            ["Data/Hora", "Usuario", "Acao", "Detalhes"]
        ]
        for entry in custody_chain:
            ts = self._escape_html(str(entry.get("timestamp", "")))
            user = self._escape_html(str(entry.get("user", "")))
            action = self._escape_html(str(entry.get("action", "")))
            details = self._escape_html(str(entry.get("details", "")))
            timeline_data.append([ts, user, action, details])

        table = Table(timeline_data, colWidths=[3.5 * cm, 3 * cm, 3.5 * cm, 6 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _TABLE_ALT_COLOR]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(PageBreak())

    def _add_resultados_verificacao(
        self, story: list[Any], case_data: dict[str, Any]
    ) -> None:
        """Adiciona a secao de resultados da verificacao."""
        story.append(Paragraph(
            "5. Resultados da Verificacao", self.styles["SectionHeader"]
        ))

        verifications = case_data.get("verifications", [])
        if not verifications:
            story.append(Paragraph(
                "Nenhuma verificacao realizada.", self.styles["BodyTextCustom"]
            ))
            story.append(PageBreak())
            return

        for v in verifications:
            check_name = self._escape_html(str(v.get("check_name", "")))
            status = str(v.get("status", "")).upper()
            details = self._escape_html(str(v.get("details", "")))

            if status == "PASS":
                status_color = _PASS_GREEN
                status_style = self.styles["StatusPass"]
            elif status == "FAIL":
                status_color = _FAIL_RED
                status_style = self.styles["StatusFail"]
            else:
                status_color = _WARN_ORANGE
                status_style = self.styles["StatusWarning"]

            check_data = [
                [Paragraph(f"<b>Verificacao:</b> {check_name}", self.styles["BodyTextCustom"]),
                 ""],
                [Paragraph(f"<b>Status:</b>", self.styles["BodyTextCustom"]),
                 Paragraph(f"<b>{status}</b>", status_style)],
                [Paragraph(f"<b>Detalhes:</b> {details}", self.styles["BodyTextCustom"]),
                 ""],
            ]

            check_table = Table(check_data, colWidths=[10 * cm, 6 * cm])
            check_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BACKGROUND", (1, 1), (1, 1), colors.Color(
                    status_color.red * 0.15 + 0.85,
                    status_color.green * 0.15 + 0.85,
                    status_color.blue * 0.15 + 0.85,
                )),
                ("BOX", (0, 0), (-1, -1), 1, colors.Color(0.7, 0.7, 0.7)),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.Color(0.85, 0.85, 0.85)),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(check_table)
            story.append(Spacer(1, 0.4 * cm))

        story.append(PageBreak())

    def _add_observacoes(
        self, story: list[Any], case_data: dict[str, Any]
    ) -> None:
        """Adiciona a secao de observacoes e inconsistencias."""
        story.append(Paragraph(
            "6. Observacoes e Inconsistencias", self.styles["SectionHeader"]
        ))

        inconsistencies = case_data.get("inconsistencies", [])
        if not inconsistencies:
            story.append(Paragraph(
                "Nenhuma inconsistencia foi encontrada durante a analise.",
                self.styles["BodyTextCustom"],
            ))
            story.append(PageBreak())
            return

        for idx, inc in enumerate(inconsistencies, start=1):
            story.append(Paragraph(
                f"{idx}. {self._escape_html(str(inc))}",
                self.styles["BodyTextCustom"],
            ))

        story.append(PageBreak())

    def _compute_report_hash(self, report_path: Path) -> str:
        """Computa o hash SHA-256 do relatorio gerado.

        Args:
            report_path: Caminho do arquivo PDF gerado.

        Returns:
            Hash SHA-256 do arquivo em hexadecimal.
        """
        sha256 = hashlib.sha256()
        with open(report_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _format_file_size(self, size_bytes: int) -> str:
        """Formata tamanho de arquivo em unidades legiveis.

        Args:
            size_bytes: Tamanho em bytes.

        Returns:
            String formatada (ex: '1.5 MB').
        """
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def _escape_html(self, text: str) -> str:
        """Escapa caracteres especiais para uso em paragrafos reportlab.

        Args:
            text: Texto a ser escapado.

        Returns:
            Texto com caracteres HTML escapados.
        """
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
