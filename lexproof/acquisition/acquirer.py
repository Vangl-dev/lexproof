"""Aquisitor forense de evidências do LexProof.

Implementa o pipeline completo de aquisição:
1. Receber arquivo
2. Calcular hashes SHA-256 e BLAKE3
3. Registrar metadados
4. Extrair ZIP (se aplicável)
5. Catalogar arquivos internos
6. Gerar manifesto
7. Limpar diretório temporário
"""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from lexproof.acquisition.zip_handler import SecureZipHandler, ZipFileInfo, ZipManifest
from lexproof.crypto.hasher import FileHasher
from lexproof.models.evidence import (
    ChatExportEvidence,
    Evidence,
    EvidenceMetadata,
    EvidenceSource,
    EvidenceType,
    ImageEvidence,
)

logger = logging.getLogger(__name__)


class EvidenceCategory(str, Enum):
    """Categoria da evidência."""

    ORIGINAL = "original"
    DERIVED = "derived"


@dataclass
class AcquisitionResult:
    """Resultado da aquisição de uma evidência."""

    evidence: Evidence
    category: EvidenceCategory
    source_path: Path
    hashes: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    zip_manifest: Optional[ZipManifest] = None
    extracted_files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineStep:
    """Etapa do pipeline de processamento."""

    step: str
    start_time: str
    end_time: str
    duration_seconds: float
    result: str
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ForensicAcquirer:
    """Aquisitor forense de evidências.

    Implementa o pipeline completo de aquisição com:
    - Hashing SHA-256 e BLAKE3
    - Extração segura de ZIPs
    - Geração de manifestos
    - Registro de pipeline
    - Limpeza automática
    """

    def __init__(self, output_dir: Path) -> None:
        """Inicializa o aquisitor.

        Args:
            output_dir: Diretório de saída para a sessão.
        """
        self._output_dir = output_dir
        self._hasher = FileHasher()
        self._zip_handler = SecureZipHandler()
        self._temp_dir: Optional[Path] = None
        self._pipeline_steps: list[PipelineStep] = []
        self._start_time: Optional[datetime] = None

    def acquire(
        self,
        file_paths: list[Path],
        *,
        client_name: str = "",
        case_number: str = "",
        responsible_technician: str = "",
    ) -> list[AcquisitionResult]:
        """Executa a aquisição forense completa.

        Args:
            file_paths: Lista de caminhos dos arquivos para adquirir.
            client_name: Nome do cliente (opcional).
            case_number: Número do processo (opcional).
            responsible_technician: Responsável técnico (opcional).

        Returns:
            Lista de resultados da aquisição.
        """
        self._start_time = datetime.now(timezone.utc)
        self._pipeline_steps.clear()

        # Criar estrutura de diretórios
        self._create_session_structure()

        results: list[AcquisitionResult] = []

        for file_path in file_paths:
            try:
                result = self._acquire_single(file_path)
                results.append(result)
            except Exception as e:
                logger.error("Erro ao adquirir %s: %s", file_path, e)
                # Criar resultado com erro
                results.append(AcquisitionResult(
                    evidence=Evidence(
                        file_path=file_path,
                        file_name=file_path.name,
                        file_size=0,
                        evidence_type=EvidenceType.OTHER,
                        sha256="",
                        blake3="",
                    ),
                    category=EvidenceCategory.ORIGINAL,
                    source_path=file_path,
                    errors=[str(e)],
                ))

        # Gerar arquivos de sessão
        self._generate_session_files(results, client_name, case_number, responsible_technician)

        # Limpar diretório temporário
        self._cleanup_temp()

        return results

    def _acquire_single(self, file_path: Path) -> AcquisitionResult:
        """Adquire um único arquivo.

        Args:
            file_path: Caminho do arquivo.

        Returns:
            Resultado da aquisição.
        """
        step_start = datetime.now(timezone.utc)

        logger.info("Iniciando aquisição: %s", file_path.name)

        # 1. Calcular hashes imediatamente
        hashes = self._compute_hashes(file_path)

        # 2. Determinar tipo de evidência
        evidence_type = self._detect_evidence_type(file_path)

        # 3. Criar evidência base
        evidence = self._create_evidence(file_path, evidence_type, hashes)

        # 4. Se for ZIP, processar conteúdo
        zip_manifest = None
        extracted_files = []
        if file_path.suffix.lower() == ".zip":
            zip_manifest, extracted_files = self._process_zip(file_path, evidence)

        # 5. Registrar etapa do pipeline
        step_end = datetime.now(timezone.utc)
        self._pipeline_steps.append(PipelineStep(
            step="Aquisição",
            start_time=step_start.isoformat(),
            end_time=step_end.isoformat(),
            duration_seconds=(step_end - step_start).total_seconds(),
            result=f"Adquirido: {file_path.name}",
        ))

        return AcquisitionResult(
            evidence=evidence,
            category=EvidenceCategory.ORIGINAL,
            source_path=file_path,
            hashes=hashes,
            metadata={
                "file_name": file_path.name,
                "file_size": file_path.stat().st_size,
                "acquired_at": step_end.isoformat(),
            },
            zip_manifest=zip_manifest,
            extracted_files=extracted_files,
        )

    def _compute_hashes(self, file_path: Path) -> dict[str, str]:
        """Calcula hashes SHA-256 e BLAKE3.

        Args:
            file_path: Caminho do arquivo.

        Returns:
            Dicionário com os hashes.
        """
        step_start = datetime.now(timezone.utc)

        hashes = {}
        try:
            sha256_result = self._hasher.compute_hash(file_path, "sha256")
            hashes["sha256"] = sha256_result.hash_value

            try:
                blake3_result = self._hasher.compute_hash(file_path, "blake3")
                hashes["blake3"] = blake3_result.hash_value
                logger.info(
                    "Hashes calculados: %s (SHA-256: %s..., BLAKE3: %s...)",
                    file_path.name,
                    hashes["sha256"][:16],
                    hashes["blake3"][:16],
                )
            except Exception as e:
                hashes["blake3"] = ""
                logger.warning("BLAKE3 indisponivel para %s: %s. Continuando com SHA-256.", file_path.name, e)
                logger.info(
                    "Hashes calculados: %s (SHA-256: %s...)",
                    file_path.name,
                    hashes["sha256"][:16],
                )
        except Exception as e:
            logger.error("Erro ao calcular hashes: %s", e)
            raise

        step_end = datetime.now(timezone.utc)
        self._pipeline_steps.append(PipelineStep(
            step="Hash",
            start_time=step_start.isoformat(),
            end_time=step_end.isoformat(),
            duration_seconds=(step_end - step_start).total_seconds(),
            result=f"Hashes calculados para {file_path.name}",
        ))

        return hashes

    def _detect_evidence_type(self, file_path: Path) -> EvidenceType:
        """Detecta o tipo de evidência.

        Args:
            file_path: Caminho do arquivo.

        Returns:
            Tipo da evidência.
        """
        ext = file_path.suffix.lower()

        if ext == ".zip":
            # Verificar se é exportação WhatsApp
            if self._is_whatsapp_zip(file_path):
                return EvidenceType.CHAT_EXPORT
            return EvidenceType.ARCHIVE

        if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}:
            return EvidenceType.IMAGE

        if ext == ".txt":
            # Verificar se é exportação WhatsApp
            if self._is_whatsapp_txt(file_path):
                return EvidenceType.CHAT_EXPORT
            return EvidenceType.TEXT

        return EvidenceType.OTHER

    def _is_whatsapp_zip(self, file_path: Path) -> bool:
        """Verifica se um ZIP é exportação do WhatsApp.

        Args:
            file_path: Caminho do arquivo ZIP.

        Returns:
            True se for exportação WhatsApp.
        """
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                for name in zf.namelist():
                    if name.lower().endswith("_chat.txt"):
                        return True
                    if "whatsapp" in name.lower():
                        return True
        except Exception:
            pass
        return False

    def _is_whatsapp_txt(self, file_path: Path) -> bool:
        """Verifica se um TXT é exportação do WhatsApp.

        Args:
            file_path: Caminho do arquivo TXT.

        Returns:
            True se for exportação WhatsApp.
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            patterns = [
                "Mensagens e chamadas são criptografadas",
                "Messages and calls are end-to-end encrypted",
            ]
            return any(pattern in content for pattern in patterns)
        except Exception:
            return False

    def _create_evidence(
        self,
        file_path: Path,
        evidence_type: EvidenceType,
        hashes: dict[str, str],
    ) -> Evidence:
        """Cria objeto Evidence.

        Args:
            file_path: Caminho do arquivo.
            evidence_type: Tipo da evidência.
            hashes: Hashes calculados.

        Returns:
            Objeto Evidence criado.
        """
        file_size = file_path.stat().st_size

        # Determinar fonte
        if evidence_type == EvidenceType.CHAT_EXPORT:
            source = EvidenceSource.WHATSAPP_EXPORT
        else:
            source = EvidenceSource.MANUAL_UPLOAD

        # Criar evidência baseado no tipo
        if evidence_type == EvidenceType.IMAGE:
            # Tentar obter dimensões
            width, height = self._get_image_dimensions(file_path)
            return ImageEvidence(
                file_path=file_path,
                file_name=file_path.name,
                file_size=file_size,
                evidence_type=evidence_type,
                source=source,
                sha256=hashes.get("sha256", ""),
                blake3=hashes.get("blake3", ""),
                width=width,
                height=height,
                format=file_path.suffix.lstrip(".").upper(),
            )
        elif evidence_type == EvidenceType.CHAT_EXPORT:
            return ChatExportEvidence(
                file_path=file_path,
                file_name=file_path.name,
                file_size=file_size,
                evidence_type=evidence_type,
                source=source,
                sha256=hashes.get("sha256", ""),
                blake3=hashes.get("blake3", ""),
                export_format="whatsapp",
                message_count=0,
            )
        else:
            return Evidence(
                file_path=file_path,
                file_name=file_path.name,
                file_size=file_size,
                evidence_type=evidence_type,
                source=source,
                sha256=hashes.get("sha256", ""),
                blake3=hashes.get("blake3", ""),
            )

    def _get_image_dimensions(self, file_path: Path) -> tuple[int, int]:
        """Obtém dimensões de uma imagem.

        Args:
            file_path: Caminho da imagem.

        Returns:
            Tupla (largura, altura).
        """
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                return img.size
        except Exception:
            return 0, 0

    def _process_zip(
        self,
        zip_path: Path,
        evidence: Evidence,
    ) -> tuple[ZipManifest, list[Path]]:
        """Processa um arquivo ZIP.

        Args:
            zip_path: Caminho do ZIP.
            evidence: Evidência criada.

        Returns:
            Tupla (manifesto, arquivos extraídos).
        """
        step_start = datetime.now(timezone.utc)

        # Criar diretório temporário
        self._temp_dir = Path(tempfile.mkdtemp(prefix="lexproof_"))

        # Validar ZIP
        if not self._zip_handler.validate(zip_path):
            raise ValueError(f"ZIP não válido: {self._zip_handler.errors}")

        # Obter conteúdo
        contents = self._zip_handler.get_contents(zip_path)

        # Calcular hashes dos arquivos internos
        file_hashes: dict[str, dict[str, str]] = {}
        for info in contents:
            if not info.is_dir:
                # Extrair temporariamente para calcular hash
                temp_file = self._temp_dir / info.name
                temp_file.parent.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    with zf.open(info.name) as src, open(temp_file, "wb") as dst:
                        dst.write(src.read())

                # Calcular hashes
                try:
                    sha256 = self._hasher.compute_hash(temp_file, "sha256")
                    blake3 = self._hasher.compute_hash(temp_file, "blake3")
                    file_hashes[info.name] = {
                        "sha256": sha256.hash_value,
                        "blake3": blake3.hash_value,
                    }
                except Exception as e:
                    logger.warning("Erro ao calcular hash de %s: %s", info.name, e)

        # Criar manifesto
        manifest = ZipManifest(
            original_zip=zip_path.name,
            sha256=evidence.sha256,
            blake3=evidence.blake3,
            size=evidence.file_size,
            file_count=len([c for c in contents if not c.is_dir]),
            files=[
                ZipFileInfo(
                    name=info.name,
                    size=info.size,
                    compressed_size=info.compressed_size,
                    is_dir=info.is_dir,
                    is_symlink=info.is_symlink,
                    sha256=file_hashes.get(info.name, {}).get("sha256"),
                    blake3=file_hashes.get(info.name, {}).get("blake3"),
                )
                for info in contents
            ],
        )

        # Extrair ZIP para diretório permanente
        extract_dir = self._output_dir / "evidence" / "original" / zip_path.stem
        extracted_files = self._zip_handler.extract(zip_path, extract_dir)

        step_end = datetime.now(timezone.utc)
        self._pipeline_steps.append(PipelineStep(
            step="Extração",
            start_time=step_start.isoformat(),
            end_time=step_end.isoformat(),
            duration_seconds=(step_end - step_start).total_seconds(),
            result=f"ZIP processado: {len(contents)} arquivos",
        ))

        return manifest, extracted_files

    def _create_session_structure(self) -> None:
        """Cria a estrutura de diretórios da sessão."""
        dirs = [
            self._output_dir / "evidence" / "original",
            self._output_dir / "evidence" / "derived",
            self._output_dir / "logs",
            self._output_dir / "temp",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _generate_session_files(
        self,
        results: list[AcquisitionResult],
        client_name: str,
        case_number: str,
        responsible_technician: str,
    ) -> None:
        """Gera os arquivos de sessão.

        Args:
            results: Resultados da aquisição.
            client_name: Nome do cliente.
            case_number: Número do processo.
            responsible_technician: Responsável técnico.
        """
        session_data = {
            "id": f"LEX-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "client_name": client_name,
            "case_number": case_number,
            "responsible_technician": responsible_technician,
            "created_at": self._start_time.isoformat() if self._start_time else datetime.now(timezone.utc).isoformat(),
            "evidence_count": len(results),
            "evidence_files": [
                {
                    "name": r.evidence.file_name,
                    "type": r.evidence.evidence_type.value,
                    "sha256": r.hashes.get("sha256", ""),
                    "blake3": r.hashes.get("blake3", ""),
                }
                for r in results
            ],
        }

        # Salvar session.json
        session_path = self._output_dir / "session.json"
        session_path.write_text(
            json.dumps(session_data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        # Salvar pipeline.json
        pipeline_data = {
            "steps": [
                {
                    "step": s.step,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "duration_seconds": s.duration_seconds,
                    "result": s.result,
                    "warnings": s.warnings,
                    "errors": s.errors,
                }
                for s in self._pipeline_steps
            ]
        }
        pipeline_path = self._output_dir / "pipeline.json"
        pipeline_path.write_text(
            json.dumps(pipeline_data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        # Salvar manifestos ZIP
        for result in results:
            if result.zip_manifest:
                manifest_path = self._output_dir / "zip_manifest.json"
                manifest_data = {
                    "original_zip": result.zip_manifest.original_zip,
                    "sha256": result.zip_manifest.sha256,
                    "blake3": result.zip_manifest.blake3,
                    "size": result.zip_manifest.size,
                    "files": [
                        {
                            "path": f.name,
                            "sha256": f.sha256,
                            "blake3": f.blake3,
                            "size": f.size,
                        }
                        for f in result.zip_manifest.files
                        if not f.is_dir
                    ],
                }
                manifest_path.write_text(
                    json.dumps(manifest_data, indent=2, ensure_ascii=False, default=str),
                    encoding="utf-8",
                )

        # Salvar hashes.json
        hashes_data = {}
        for result in results:
            hashes_data[result.evidence.file_name] = result.hashes
        hashes_path = self._output_dir / "hashes.json"
        hashes_path.write_text(
            json.dumps(hashes_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Salvar metadata.json
        metadata_data = {
            "session": session_data,
            "acquisition": {
                "total_files": len(results),
                "original_files": sum(1 for r in results if r.category == EvidenceCategory.ORIGINAL),
                "derived_files": sum(1 for r in results if r.category == EvidenceCategory.DERIVED),
            },
        }
        metadata_path = self._output_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps(metadata_data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        logger.info("Arquivos de sessão gerados em %s", self._output_dir)

    def _cleanup_temp(self) -> None:
        """Limpa o diretório temporário."""
        if self._temp_dir and self._temp_dir.exists():
            try:
                shutil.rmtree(self._temp_dir)
                logger.info("Diretório temporário removido: %s", self._temp_dir)
            except Exception as e:
                logger.warning("Erro ao remover diretório temporário: %s", e)


import zipfile
