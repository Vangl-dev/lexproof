"""Identificacao rapida dos arquivos adicionados a uma preservacao.

Usado pela interface para dizer, antes de processar, o que cada arquivo e
(conversa exportada, print, outro) e avisar de problemas comuns.
"""

from __future__ import annotations

import logging
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

from lexproof.core.constants import DEFAULT_TIMEZONE, SUPPORTED_IMAGE_TYPES
from lexproof.parsers.whatsapp_parser import WhatsAppParser
from lexproof.triangulation.screenshot_reader import capture_time_from_file

logger = logging.getLogger(__name__)

KIND_EXPORT = "export"
KIND_SCREENSHOT = "screenshot"
KIND_OTHER = "other"


@dataclass
class FileInfo:
    """Descricao de um arquivo para a tela de importacao."""

    path: Path
    kind: str
    title: str
    detail: str = ""
    warnings: list[str] = field(default_factory=list)


def _describe_export(txt_path: Path) -> str:
    parser = WhatsAppParser()
    if not parser.validate(txt_path):
        return ""
    msgs = parser.parse(txt_path)
    if not msgs:
        return "nenhuma mensagem reconhecida"
    first, last = msgs[0].timestamp, msgs[-1].timestamp
    return f"{len(msgs)} mensagens, de {first:%d/%m/%Y} a {last:%d/%m/%Y}"


def describe_file(path: Path) -> FileInfo:
    """Diz o que e *path* em linguagem simples."""
    path = Path(path)
    ext = path.suffix.lower()
    try:
        if ext == ".zip":
            with zipfile.ZipFile(path) as zf, tempfile.TemporaryDirectory() as tmp:
                txts = [n for n in zf.namelist() if n.lower().endswith(".txt")]
                for name in txts:
                    target = Path(tmp) / "conversa.txt"
                    target.write_bytes(zf.read(name))
                    detail = _describe_export(target)
                    if detail:
                        media = len(zf.namelist()) - len(txts)
                        if media:
                            detail += f" e {media} anexo(s)"
                        return FileInfo(path, KIND_EXPORT, "Conversa exportada do WhatsApp", detail)
            return FileInfo(path, KIND_OTHER, "Arquivo ZIP", "não contém conversa do WhatsApp")
        if ext == ".txt":
            detail = _describe_export(path)
            if detail:
                return FileInfo(path, KIND_EXPORT, "Conversa exportada do WhatsApp", detail)
            return FileInfo(path, KIND_OTHER, "Arquivo de texto", "não é uma conversa do WhatsApp")
        if ext in SUPPORTED_IMAGE_TYPES:
            captured, _ = capture_time_from_file(path, ZoneInfo(DEFAULT_TIMEZONE))
            if captured:
                return FileInfo(path, KIND_SCREENSHOT, "Print de tela", f"tirado em {captured:%d/%m/%Y às %H:%M}")
            return FileInfo(
                path, KIND_SCREENSHOT, "Imagem", "sem data de captura",
                ["Sem data no nome nem nos metadados: talvez tenha sido enviada pelo "
                 "WhatsApp como foto, o que apaga essa informação."],
            )
    except Exception as exc:
        logger.warning("Falha ao identificar %s: %s", path.name, exc)
        return FileInfo(path, KIND_OTHER, "Arquivo", f"não foi possível ler ({exc})")
    return FileInfo(path, KIND_OTHER, "Outro arquivo", "será preservado, mas não analisado")


def intake_warnings(infos: list[FileInfo]) -> list[str]:
    """Avisos sobre o conjunto de arquivos."""
    kinds = {i.kind for i in infos}
    warnings = []
    if KIND_SCREENSHOT in kinds and KIND_EXPORT not in kinds:
        warnings.append(
            "Sem a conversa exportada, os prints serão preservados, mas não poderão ser "
            "conferidos. Inclua o ZIP gerado em \"Exportar conversa\"."
        )
    if sum(1 for i in infos if i.kind == KIND_EXPORT) > 1:
        warnings.append("Há mais de uma conversa exportada; os prints serão conferidos com a primeira.")
    return warnings
