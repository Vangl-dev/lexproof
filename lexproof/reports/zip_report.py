"""Gerador de relatório ZIP empacotando todos os formatos."""

from __future__ import annotations

import io
import json
import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from lexproof import __version__
from lexproof.models.report import ReportConfig, ReportType
from lexproof.reports.base import BaseReportGenerator
from lexproof.reports.html_report import HTMLReportGenerator
from lexproof.reports.json_report import JSONReportGenerator
from lexproof.reports.manifest_report import ManifestReportGenerator
from lexproof.reports.pdf_report import PDFReportGenerator

logger = logging.getLogger("lexproof.reports.zip")


class ZIPReportGenerator(BaseReportGenerator):
    """Gera um arquivo ZIP empacotando todos os tipos de relatório.

    Cria um arquivo ZIP organizado com diretórios para cada formato
    de relatório, incluindo os arquivos de evidência originais
    e o manifest de integridade.
    """

    def __init__(self) -> None:
        """Inicializa o gerador ZIP com instâncias dos outros geradores."""
        self.pdf_generator = PDFReportGenerator()
        self.html_generator = HTMLReportGenerator()
        self.json_generator = JSONReportGenerator()
        self.manifest_generator = ManifestReportGenerator()

    def generate(self, case_data: dict[str, Any], config: ReportConfig) -> Path:
        """Gera o arquivo ZIP com todos os relatórios.

        Cria um ZIP com a seguinte estrutura:
            relatorio_lexproof/
                reports/
                    relatorio.pdf
                    relatorio.html
                    relatorio.json
                manifest/
                    manifest.json
                evidence/
                    (arquivos de evidência originais)

        Args:
            case_data: Dicionário com os dados do caso.
            config: Configuração do relatório.

        Returns:
            Caminho do arquivo ZIP gerado.
        """
        output_path = config.output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="lexproof_") as tmp_dir:
            tmp_path = Path(tmp_dir)

            pdf_path = self._generate_pdf(case_data, config, tmp_path)
            html_path = self._generate_html(case_data, config, tmp_path)
            json_path = self._generate_json(case_data, config, tmp_path)
            manifest_path = self._generate_manifest(case_data, config, tmp_path)

            evidence_files = case_data.get("evidence_files", [])

            self._create_zip(
                output_path=output_path,
                pdf_path=pdf_path,
                html_path=html_path,
                json_path=json_path,
                manifest_path=manifest_path,
                evidence_files=evidence_files,
            )

        logger.info("Relatório ZIP gerado: %s", output_path)
        return output_path

    def _generate_pdf(
        self, case_data: dict[str, Any], config: ReportConfig, tmp_path: Path
    ) -> Path:
        """Gera o relatório PDF em diretório temporário."""
        pdf_config = config.model_copy(update={
            "report_type": ReportType.PDF,
            "output_path": tmp_path / "reports" / "relatorio.pdf",
        })
        return self.pdf_generator.generate(case_data, pdf_config)

    def _generate_html(
        self, case_data: dict[str, Any], config: ReportConfig, tmp_path: Path
    ) -> Path:
        """Gera o relatório HTML em diretório temporário."""
        html_config = config.model_copy(update={
            "report_type": ReportType.HTML,
            "output_path": tmp_path / "reports" / "relatorio.html",
        })
        return self.html_generator.generate(case_data, html_config)

    def _generate_json(
        self, case_data: dict[str, Any], config: ReportConfig, tmp_path: Path
    ) -> Path:
        """Gera o relatório JSON em diretório temporário."""
        json_config = config.model_copy(update={
            "report_type": ReportType.JSON,
            "output_path": tmp_path / "reports" / "relatorio.json",
        })
        return self.json_generator.generate(case_data, json_config)

    def _generate_manifest(
        self, case_data: dict[str, Any], config: ReportConfig, tmp_path: Path
    ) -> Path:
        """Gera o manifest.json em diretório temporário."""
        manifest_config = config.model_copy(update={
            "report_type": ReportType.MANIFEST,
            "output_path": tmp_path / "manifest" / "manifest.json",
        })
        return self.manifest_generator.generate(case_data, manifest_config)

    def _create_zip(
        self,
        output_path: Path,
        pdf_path: Path,
        html_path: Path,
        json_path: Path,
        manifest_path: Path,
        evidence_files: list[dict[str, Any]],
    ) -> None:
        """Cria o arquivo ZIP com todos os relatórios e evidências.

        Args:
            output_path: Caminho do arquivo ZIP de saída.
            pdf_path: Caminho do relatório PDF.
            html_path: Caminho do relatório HTML.
            json_path: Caminho do relatório JSON.
            manifest_path: Caminho do manifest.json.
            evidence_files: Lista de evidências do caso em formato dict.
        """
        with zipfile.ZipFile(str(output_path), "w", zipfile.ZIP_DEFLATED) as zf:
            if pdf_path.exists():
                zf.write(str(pdf_path), "relatorio_lexproof/reports/relatorio.pdf")

            if html_path.exists():
                zf.write(str(html_path), "relatorio_lexproof/reports/relatorio.html")

            if json_path.exists():
                zf.write(str(json_path), "relatorio_lexproof/reports/relatorio.json")

            if manifest_path.exists():
                zf.write(str(manifest_path), "relatorio_lexproof/manifest/manifest.json")

            added_evidence: set[str] = set()
            for ev in evidence_files:
                file_path = ev.get("file_path")
                file_name = ev.get("file_name", "")
                if file_path and file_name:
                    fp = Path(str(file_path))
                    if fp.exists() and str(fp) not in added_evidence:
                        zf.write(str(fp), f"relatorio_lexproof/evidence/{file_name}")
                        added_evidence.add(str(fp))

            readme_content = self._build_readme()
            zf.writestr("relatorio_lexproof/README.txt", readme_content)

    def _build_readme(self) -> str:
        """Constrói o conteúdo do README incluído no ZIP.

        Returns:
            Texto do README com informações sobre o conteúdo do ZIP.
        """
        return (
            "LexProof - Preservação de Evidências Digitais\n"
            "==============================================\n\n"
            f"Versão do LexProof: {__version__}\n\n"
            "Este arquivo ZIP contém os relatórios gerados pelo LexProof:\n\n"
            "reports/\n"
            "  relatorio.pdf   - Relatório completo em PDF\n"
            "  relatorio.html  - Relatório completo em HTML (abrir em navegador)\n"
            "  relatorio.json  - Relatório em formato JSON estruturado\n\n"
            "manifest/\n"
            "  manifest.json   - Manifesto de integridade com hashes globais\n\n"
            "evidence/\n"
            "  (arquivos)      - Cópias dos arquivos de evidência originais\n\n"
            "Para verificar a integridade, use o manifest.json ou escaneie\n"
            "o QR code presente no relatório PDF/HTML.\n"
        )

    def prepare_report_data(self, case_data: dict[str, Any]) -> dict[str, Any]:
        """Prepara dados delegando ao gerador JSON.

        Args:
            case_data: Dados brutos do caso.

        Returns:
            Dados preparados do relatório.
        """
        return self.json_generator.prepare_report_data(case_data)
