"""Identificacao rapida dos arquivos adicionados a uma preservacao.

Usado pela interface para dizer, antes de processar, o que cada arquivo e
(conversa exportada, print, outro) e avisar de problemas comuns.
"""

from __future__ import annotations

import logging
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from lexproof.core.constants import DEFAULT_TIMEZONE, SUPPORTED_IMAGE_TYPES
from lexproof.parsers.whatsapp_parser import WhatsAppParser
from lexproof.triangulation.screenshot_reader import capture_time_from_file

logger = logging.getLogger(__name__)

KIND_EXPORT = "export"
KIND_SCREENSHOT = "screenshot"
KIND_EMAIL = "email"
KIND_OTHER = "other"


@dataclass
class FileInfo:
    """Descricao de um arquivo para a tela de importacao."""

    path: Path
    kind: str
    title: str
    detail: str = ""
    warnings: list[str] = field(default_factory=list)
    # Periodo coberto, para conversas exportadas
    first_date: Optional[date] = None
    last_date: Optional[date] = None
    # Nome do arquivo da conversa ("Conversa do WhatsApp com Fulano")
    export_name: str = ""

    @property
    def has_export(self) -> bool:
        return self.kind == KIND_EXPORT or (self.kind == KIND_EMAIL and self.first_date is not None)


def _describe_export(txt_path: Path) -> tuple[str, Optional[date], Optional[date]]:
    parser = WhatsAppParser()
    if not parser.validate(txt_path):
        return "", None, None
    msgs = parser.parse(txt_path)
    if not msgs:
        return "nenhuma mensagem reconhecida", None, None
    first, last = msgs[0].timestamp, msgs[-1].timestamp
    return f"{len(msgs)} mensagens, de {first:%d/%m/%Y} a {last:%d/%m/%Y}", first.date(), last.date()


def describe_file(path: Path) -> FileInfo:
    """Diz o que e *path* em linguagem simples."""
    path = Path(path)
    ext = path.suffix.lower()
    try:
        if ext == ".eml":
            return _describe_email(path)
        if ext == ".zip":
            with zipfile.ZipFile(path) as zf, tempfile.TemporaryDirectory() as tmp:
                txts = [n for n in zf.namelist() if n.lower().endswith(".txt")]
                for name in txts:
                    target = Path(tmp) / "conversa.txt"
                    target.write_bytes(zf.read(name))
                    detail, first, last = _describe_export(target)
                    if detail:
                        media = len(zf.namelist()) - len(txts)
                        if media:
                            detail += f" e {media} anexo(s)"
                        return FileInfo(path, KIND_EXPORT, "Conversa exportada do WhatsApp", detail,
                                        first_date=first, last_date=last, export_name=Path(name).stem)
            return FileInfo(path, KIND_OTHER, "Arquivo ZIP", "não contém conversa do WhatsApp")
        if ext == ".txt":
            detail, first, last = _describe_export(path)
            if detail:
                return FileInfo(path, KIND_EXPORT, "Conversa exportada do WhatsApp", detail,
                                first_date=first, last_date=last, export_name=path.stem)
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


def _describe_email(path: Path) -> FileInfo:
    from lexproof.acquisition.email_intake import read_email

    first = last = None
    export_note = export_name = ""
    with tempfile.TemporaryDirectory() as tmp:
        em = read_email(path, Path(tmp))
        for att in em.attachments:
            if att.path.suffix.lower() in (".zip", ".txt"):
                inner = describe_file(att.path)
                if inner.kind == KIND_EXPORT:
                    first, last = inner.first_date, inner.last_date
                    export_name = inner.export_name
                    export_note = f" · inclui conversa exportada ({inner.detail})"
    when = f" em {em.date:%d/%m/%Y às %H:%M}" if em.date else ""
    detail = f"de {em.sender or 'remetente desconhecido'}{when}, {len(em.attachments)} anexo(s){export_note}"
    warnings = []
    if em.verified:
        detail += f" · assinatura do provedor válida ({em.aligned_signature.domain})"
    else:
        reason = em.signatures[0].error if em.signatures else "sem assinatura DKIM"
        warnings.append(
            f"Assinatura do provedor não confirmada ({reason}). Use \"Baixar original\" no "
            "Gmail (ou \"Salvar como\" no Outlook) e não encaminhe o e-mail antes."
        )
    return FileInfo(path, KIND_EMAIL, "E-mail recebido", detail, warnings,
                    first_date=first, last_date=last, export_name=export_name)


def intake_warnings(infos: list[FileInfo]) -> list[str]:
    """Avisos sobre o conjunto de arquivos."""
    kinds = {i.kind for i in infos}
    warnings = []
    if (KIND_SCREENSHOT in kinds or KIND_EMAIL in kinds) and not any(i.has_export for i in infos):
        warnings.append(
            "Sem a conversa exportada, os prints serão conferidos entre si (lacunas e "
            "contradições), mas não com a conversa original."
        )
    if sum(1 for i in infos if i.has_export) > 1:
        warnings.append("Há mais de uma conversa exportada; os prints serão conferidos com a primeira.")
    return warnings
