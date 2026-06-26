"""Gerador de relatórios em formato PDF."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from lexproof import __version__
from lexproof.models.report import ReportConfig
from lexproof.reports.base import BaseReportGenerator
from lexproof.reports.qr_generator import QRCodeGenerator

logger = logging.getLogger("lexproof.reports.pdf")

PAGE_WIDTH, PAGE_HEIGHT = A4


class PDFReportGenerator(BaseReportGenerator):
    """Gera relatórios completos em formato PDF.

    Utiliza reportlab para criar documentos PDF profissionais
    com capa, sumário, tabelas e todas as seções de evidência.
    """

    def __init__(self) -> None:
        """Inicializa o gerador PDF com estilos padrão."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.qr_generator = QRCodeGenerator()

    def _setup_custom_styles(self) -> None:
        """Configura estilos personalizados para o documento."""
        self.styles.add(ParagraphStyle(
            name="CoverTitle",
            parent=self.styles["Title"],
            fontSize=28,
            leading=34,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.HexColor("#1a1a2e"),
        ))
        self.styles.add(ParagraphStyle(
            name="CoverSubtitle",
            parent=self.styles["Normal"],
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            spaceAfter=12,
            textColor=colors.HexColor("#4a4a6a"),
        ))
        self.styles.add(ParagraphStyle(
            name="SectionHeader",
            parent=self.styles["Heading1"],
            fontSize=16,
            leading=20,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor("#16213e"),
            borderWidth=1,
            borderColor=colors.HexColor("#16213e"),
            borderPadding=4,
        ))
        self.styles.add(ParagraphStyle(
            name="SubSection",
            parent=self.styles["Heading2"],
            fontSize=12,
            leading=15,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor("#0f3460"),
        ))
        self.styles.add(ParagraphStyle(
            name="BodyTextCustom",
            parent=self.styles["Normal"],
            fontSize=10,
            leading=13,
            spaceAfter=6,
        ))
        self.styles.add(ParagraphStyle(
            name="FooterStyle",
            parent=self.styles["Normal"],
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.grey,
        ))
        self.styles.add(ParagraphStyle(
            name="HashValue",
            parent=self.styles["Code"],
            fontSize=7,
            leading=9,
            wordWrap="CJK",
        ))

    def generate(self, case_data: dict[str, Any], config: ReportConfig) -> Path:
        """Gera o relatório PDF completo.

        Cria um documento PDF com capa, sumário e todas as seções
        de dados do caso conforme configurado.

        Args:
            case_data: Dicionário com os dados do caso.
            config: Configuração do relatório.

        Returns:
            Caminho do arquivo PDF gerado.
        """
        report_data = self.prepare_report_data(case_data)
        output_path = config.output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2.5 * cm,
            title=f"LexProof - {report_data['metadata'].get('title', 'Relatório')}",
            author="LexProof Digital Forensics",
        )

        story: list[Any] = []

        self._add_cover_page(story, report_data, config)
        self._add_table_of_contents(story, report_data, config)
        self._add_evidence_section(story, report_data, config)
        self._add_hash_section(story, report_data, config)
        self._add_timeline_section(story, report_data, config)
        self._add_ocr_section(story, report_data, config)
        self._add_verification_section(story, report_data, config)
        self._add_custody_section(story, report_data, config)
        self._add_inconsistencies_section(story, report_data, config)
        self._add_qr_section(story, report_data, config)

        doc.build(story, onFirstPage=self._add_footer, onLaterPages=self._add_footer)
        logger.info("Relatório PDF gerado: %s", output_path)
        return output_path

    def _add_cover_page(
        self, story: list[Any], report_data: dict[str, Any], config: ReportConfig
    ) -> None:
        """Adiciona a página de capa ao relatório."""
        story.append(Spacer(1, 6 * cm))

        story.append(Paragraph("LEXPROOF", self.styles["CoverTitle"]))
        story.append(Paragraph(
            "Relatório de Preservação de Evidências Digitais",
            self.styles["CoverSubtitle"],
        ))
        story.append(Spacer(1, 2 * cm))

        metadata = report_data.get("metadata", {})
        if metadata.get("title"):
            story.append(Paragraph(
                f"<b>{self._escape_html(metadata['title'])}</b>",
                self.styles["CoverTitle"],
            ))
            story.append(Spacer(1, 0.5 * cm))

        info_lines = []
        if metadata.get("case_number"):
            info_lines.append(f"Processo: {metadata['case_number']}")
        if metadata.get("client_name"):
            info_lines.append(f"Cliente: {metadata['client_name']}")
        if metadata.get("lawyer_name"):
            info_lines.append(f"Advogado: {metadata['lawyer_name']}")
        if metadata.get("court"):
            info_lines.append(f"Tribunal: {metadata['court']}")

        for line in info_lines:
            story.append(Paragraph(
                self._escape_html(line), self.styles["CoverSubtitle"]
            ))

        story.append(Spacer(1, 3 * cm))
        story.append(Paragraph(
            f"Gerado em: {report_data['report_generated_at']}",
            self.styles["CoverSubtitle"],
        ))
        story.append(Paragraph(
            f"LexProof v{report_data['app_version']}",
            self.styles["CoverSubtitle"],
        ))
        story.append(PageBreak())

    def _add_table_of_contents(
        self, story: list[Any], report_data: dict[str, Any], config: ReportConfig
    ) -> None:
        """Adiciona a página de sumário ao relatório."""
        story.append(Paragraph("Sumário", self.styles["SectionHeader"]))
        story.append(Spacer(1, 0.5 * cm))

        toc_items = ["1. Evidências"]
        section_num = 2

        if config.include_hashes:
            toc_items.append(f"{section_num}. Resultados de Hash")
            section_num += 1
        if config.include_timeline:
            toc_items.append(f"{section_num}. Linha do Tempo")
            section_num += 1
        if config.include_ocr:
            toc_items.append(f"{section_num}. Resultados de OCR")
            section_num += 1
        if config.include_verification:
            toc_items.append(f"{section_num}. Resultados de Verificação")
            section_num += 1
        if config.include_custody:
            toc_items.append(f"{section_num}. Cadeia de Custódia")
            section_num += 1
        if report_data.get("inconsistencies"):
            toc_items.append(f"{section_num}. Inconsistências Detectadas")
            section_num += 1
        if config.include_qr_code:
            toc_items.append(f"{section_num}. QR Code de Verificação")
            section_num += 1

        for item in toc_items:
            story.append(Paragraph(item, self.styles["BodyTextCustom"]))

        story.append(PageBreak())

    def _add_evidence_section(
        self, story: list[Any], report_data: dict[str, Any], config: ReportConfig
    ) -> None:
        """Adiciona a seção de evidências ao relatório."""
        story.append(Paragraph("1. Evidências", self.styles["SectionHeader"]))

        evidence_files = report_data.get("evidence_files", [])
        if not evidence_files:
            story.append(Paragraph(
                "Nenhuma evidência registrada.", self.styles["BodyTextCustom"]
            ))
            story.append(PageBreak())
            return

        table_data = [["Arquivo", "Tipo", "Tamanho", "Hash SHA-256"]]
        for ev in evidence_files:
            file_size = ev.get("file_size", 0)
            size_str = self._format_file_size(file_size)
            file_name = self._escape_html(str(ev.get("file_name", "")))
            ev_type = self._escape_html(str(ev.get("evidence_type", "")))
            file_hash = self._escape_html(str(ev.get("original_hash", "N/A")))
            table_data.append([file_name, ev_type, size_str, file_hash])

        table = Table(table_data, colWidths=[5 * cm, 2.5 * cm, 2 * cm, 6.5 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(PageBreak())

    def _add_hash_section(
        self, story: list[Any], report_data: dict[str, Any], config: ReportConfig
    ) -> None:
        """Adiciona a seção de resultados de hash."""
        if not config.include_hashes:
            return

        story.append(Paragraph("2. Resultados de Hash", self.styles["SectionHeader"]))

        hash_results = report_data.get("hash_results", [])
        if not hash_results:
            story.append(Paragraph(
                "Nenhum hash calculado.", self.styles["BodyTextCustom"]
            ))
            story.append(PageBreak())
            return

        table_data = [["Algoritmo", "Arquivo", "Hash", "Data/Hora"]]
        for hr in hash_results:
            algo = self._escape_html(str(hr.get("algorithm", "")))
            file_path = self._escape_html(str(hr.get("file_path", "")))
            hash_val = self._escape_html(str(hr.get("hash_value", "")))
            computed = self._escape_html(str(hr.get("computed_at", "")))
            table_data.append([algo, file_path, hash_val, computed])

        table = Table(table_data, colWidths=[2.5 * cm, 4 * cm, 7.5 * cm, 3 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(PageBreak())

    def _add_timeline_section(
        self, story: list[Any], report_data: dict[str, Any], config: ReportConfig
    ) -> None:
        """Adiciona a seção da linha do tempo."""
        if not config.include_timeline:
            return

        story.append(Paragraph("3. Linha do Tempo", self.styles["SectionHeader"]))

        timeline = report_data.get("timeline", [])
        if not timeline:
            story.append(Paragraph(
                "Nenhuma entrada na linha do tempo.", self.styles["BodyTextCustom"]
            ))
            story.append(PageBreak())
            return

        table_data = [["Data/Hora", "Tipo", "Remetente", "Conteúdo"]]
        for entry in timeline:
            ts = self._escape_html(str(entry.get("timestamp", "")))
            etype = self._escape_html(str(entry.get("entry_type", "")))
            sender = self._escape_html(str(entry.get("sender", "")))
            content = self._escape_html(str(entry.get("content", "")))
            if len(content) > 80:
                content = content[:77] + "..."
            table_data.append([ts, etype, sender, content])

        table = Table(table_data, colWidths=[3.5 * cm, 2.5 * cm, 3 * cm, 8 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(PageBreak())

    def _add_ocr_section(
        self, story: list[Any], report_data: dict[str, Any], config: ReportConfig
    ) -> None:
        """Adiciona a seção de resultados de OCR."""
        if not config.include_ocr:
            return

        story.append(Paragraph("4. Resultados de OCR", self.styles["SectionHeader"]))

        ocr_results = report_data.get("ocr_results", [])
        if not ocr_results:
            story.append(Paragraph(
                "Nenhum resultado de OCR disponível.", self.styles["BodyTextCustom"]
            ))
            story.append(PageBreak())
            return

        for idx, ocr in enumerate(ocr_results, start=1):
            story.append(Paragraph(
                f"OCR #{idx} - {self._escape_html(str(ocr.get('source_image', '')))}",
                self.styles["SubSection"],
            ))

            details = [
                ("Confiança", f"{ocr.get('confidence', 0):.1%}"),
                ("Engine", str(ocr.get("engine_used", ""))),
                ("Tempo de processamento", f"{ocr.get('processing_time', 0):.2f}s"),
            ]
            for label, value in details:
                story.append(Paragraph(
                    f"<b>{label}:</b> {self._escape_html(value)}",
                    self.styles["BodyTextCustom"],
                ))

            timestamps = ocr.get("detected_timestamps", [])
            if timestamps:
                story.append(Paragraph(
                    "<b>Timestamps detectados:</b>", self.styles["BodyTextCustom"]
                ))
                for ts in timestamps:
                    story.append(Paragraph(
                        f"  • {self._escape_html(str(ts))}",
                        self.styles["BodyTextCustom"],
                    ))

            senders = ocr.get("detected_senders", [])
            if senders:
                story.append(Paragraph(
                    "<b>Remetentes detectados:</b>", self.styles["BodyTextCustom"]
                ))
                for s in senders:
                    story.append(Paragraph(
                        f"  • {self._escape_html(str(s))}",
                        self.styles["BodyTextCustom"],
                    ))

            extracted = ocr.get("extracted_text", "")
            if extracted:
                story.append(Paragraph(
                    "<b>Texto extraído:</b>", self.styles["BodyTextCustom"]
                ))
                safe_text = self._escape_html(extracted)
                story.append(Paragraph(safe_text, self.styles["BodyTextCustom"]))

            story.append(Spacer(1, 0.5 * cm))

        story.append(PageBreak())

    def _add_verification_section(
        self, story: list[Any], report_data: dict[str, Any], config: ReportConfig
    ) -> None:
        """Adiciona a seção de resultados de verificação."""
        if not config.include_verification:
            return

        story.append(Paragraph(
            "5. Resultados de Verificação", self.styles["SectionHeader"]
        ))

        verification = report_data.get("verification_results", [])
        if not verification:
            story.append(Paragraph(
                "Nenhuma verificação realizada.", self.styles["BodyTextCustom"]
            ))
            story.append(PageBreak())
            return

        table_data = [["Verificação", "Status", "Esperado", "Atual"]]
        for vr in verification:
            name = self._escape_html(str(vr.get("check_name", "")))
            status = self._escape_html(str(vr.get("status", "")))
            expected = self._escape_html(str(vr.get("expected", "N/A")))
            actual = self._escape_html(str(vr.get("actual", "N/A")))
            table_data.append([name, status, expected, actual])

        table = Table(table_data, colWidths=[5 * cm, 2.5 * cm, 4.5 * cm, 5 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)

        summary = report_data.get("summary", {})
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph(
            f"<b>Resumo:</b> {summary.get('verification_pass', 0)} passou, "
            f"{summary.get('verification_fail', 0)} falhou, "
            f"{summary.get('verification_warnings', 0)} com aviso",
            self.styles["BodyTextCustom"],
        ))
        story.append(PageBreak())

    def _add_custody_section(
        self, story: list[Any], report_data: dict[str, Any], config: ReportConfig
    ) -> None:
        """Adiciona a seção de cadeia de custódia."""
        if not config.include_custody:
            return

        story.append(Paragraph("6. Cadeia de Custódia", self.styles["SectionHeader"]))

        custody_chains = report_data.get("custody_chains", [])
        if not custody_chains:
            story.append(Paragraph(
                "Nenhuma cadeia de custódia registrada.",
                self.styles["BodyTextCustom"],
            ))
            story.append(PageBreak())
            return

        for chain in custody_chains:
            evidence_id = self._escape_html(str(chain.get("evidence_id", "")))
            story.append(Paragraph(
                f"Evidência: {evidence_id}", self.styles["SubSection"]
            ))

            events = chain.get("events", [])
            if not events:
                story.append(Paragraph(
                    "  Nenhum evento registrado.", self.styles["BodyTextCustom"]
                ))
                continue

            table_data = [["Evento", "Descrição", "Data/Hora", "Operador"]]
            for ev in events:
                etype = self._escape_html(str(ev.get("event_type", "")))
                desc = self._escape_html(str(ev.get("description", "")))
                ts = self._escape_html(str(ev.get("timestamp", "")))
                op = self._escape_html(str(ev.get("operator", "")))
                table_data.append([etype, desc, ts, op])

            table = Table(table_data, colWidths=[3 * cm, 6 * cm, 4.5 * cm, 3.5 * cm])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.5 * cm))

        story.append(PageBreak())

    def _add_inconsistencies_section(
        self, story: list[Any], report_data: dict[str, Any], config: ReportConfig
    ) -> None:
        """Adiciona a seção de inconsistências."""
        inconsistencies = report_data.get("inconsistencies", [])
        if not inconsistencies:
            return

        story.append(Paragraph(
            "7. Inconsistências Detectadas", self.styles["SectionHeader"]
        ))

        for idx, inc in enumerate(inconsistencies, start=1):
            story.append(Paragraph(
                f"{idx}. {self._escape_html(str(inc))}",
                self.styles["BodyTextCustom"],
            ))

        story.append(PageBreak())

    def _add_qr_section(
        self, story: list[Any], report_data: dict[str, Any], config: ReportConfig
    ) -> None:
        """Adiciona a seção de QR code de verificação."""
        if not config.include_qr_code:
            return

        story.append(Paragraph(
            "QR Code de Verificação", self.styles["SectionHeader"]
        ))

        hash_results = report_data.get("hash_results", [])
        case_hash = ""
        if hash_results:
            case_hash = str(hash_results[0].get("hash_value", ""))

        if case_hash:
            qr_data = {
                "type": "lexproof_verification",
                "version": report_data.get("schema_version", "1.0"),
                "case_hash": case_hash,
                "generated_at": report_data.get("report_generated_at", ""),
            }
            qr_image = self.qr_generator.generate_verification_qr(qr_data)

            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                qr_path = Path(tmp.name)
            self.qr_generator.save_qr(qr_image, qr_path)

            story.append(Paragraph(
                "Escaneie este QR code para verificar a integridade do relatório:",
                self.styles["BodyTextCustom"],
            ))
            story.append(Spacer(1, 0.3 * cm))
            story.append(Image(str(qr_path), width=5 * cm, height=5 * cm))
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph(
                f"Hash: {self._escape_html(case_hash[:64])}",
                self.styles["HashValue"],
            ))

            qr_path.unlink(missing_ok=True)
        else:
            story.append(Paragraph(
                "Nenhum hash disponível para gerar QR code.",
                self.styles["BodyTextCustom"],
            ))

    def _add_footer(self, canvas: Any, doc: Any) -> None:
        """Adiciona rodapé com versão do app e número de página."""
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(
            2 * cm,
            1.2 * cm,
            f"LexProof v{__version__} - Preservação de Evidências Digitais",
        )
        canvas.drawRightString(
            PAGE_WIDTH - 2 * cm,
            1.2 * cm,
            f"Página {doc.page}",
        )
        canvas.restoreState()

    def _format_file_size(self, size_bytes: int) -> str:
        """Formata tamanho de arquivo em unidades legíveis."""
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def _escape_html(self, text: str) -> str:
        """Escapa caracteres especiais para uso em parágrafos reportlab."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
