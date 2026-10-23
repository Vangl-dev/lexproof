"""Recorte de uma exportacao do WhatsApp a um periodo de interesse.

A exportacao e cronologica, entao as mensagens de um periodo formam um bloco
continuo de linhas do .txt. O recorte copia esse bloco byte a byte, de modo
que quem tiver o arquivo completo consegue reproduzi-lo:

    sed -n 'INICIO,FIMp' "arquivo original.txt" | sha256sum

O hash do arquivo completo fica registrado (e carimbado). Opcionalmente, a
copia completa e as midias fora do periodo sao apagadas da pasta do caso.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from lexproof.models.message import WhatsAppMessage

logger = logging.getLogger(__name__)

EXCERPT_RECORD_NAME = "recorte.txt"
_ATTACHMENT_RE = re.compile(r"([\w\-. ()]+\.\w{2,5}) \((?:arquivo anexado|file attached)\)", re.IGNORECASE)


@dataclass
class ExcerptResult:
    """Recorte de uma exportacao."""

    source_txt: str
    source_txt_sha256: str
    source_zip: str = ""
    source_zip_sha256: str = ""
    start: Optional[date] = None
    end: Optional[date] = None
    total_messages: int = 0
    kept_messages: int = 0
    first_line: int = 0
    last_line: int = 0
    excerpt_path: Optional[Path] = None
    excerpt_sha256: str = ""
    discarded: bool = False
    removed_files: list[str] = field(default_factory=list)
    kept_attachments: list[Path] = field(default_factory=list)

    @property
    def verify_command(self) -> str:
        return f"sed -n '{self.first_line},{self.last_line}p' \"{self.source_txt}\" | sha256sum"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def make_excerpt(
    txt_path: Path,
    messages: list[WhatsAppMessage],
    start: date,
    end: date,
    out_dir: Path,
    *,
    zip_path: Optional[Path] = None,
) -> ExcerptResult:
    """Grava em *out_dir* as linhas de *txt_path* com mensagens de *start* a *end*.

    Raises:
        ValueError: se nao houver mensagem no periodo.
    """
    txt_path = Path(txt_path)
    ordered = sorted(messages, key=lambda m: m.line_number)
    inside = [m for m in ordered if start <= m.timestamp.date() <= end]
    if not inside:
        raise ValueError(f"Nenhuma mensagem entre {start:%d/%m/%Y} e {end:%d/%m/%Y}")

    data = txt_path.read_bytes()
    raw_lines = data.split(b"\n")
    first_line = inside[0].line_number
    after = next((m for m in ordered if m.line_number > inside[-1].line_number), None)
    last_line = (after.line_number - 1) if after else len(raw_lines)
    # Linhas em branco no fim do bloco pertencem a mensagem seguinte ou ao EOF.
    while last_line > first_line and not raw_lines[last_line - 1].strip():
        last_line -= 1

    block = raw_lines[first_line - 1:last_line]
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"{txt_path.stem} - recorte {start:%d-%m-%Y} a {end:%d-%m-%Y}.txt"
    excerpt_path = out_dir / name
    # Mesmo formato do "sed -n 'A,Bp'": cada linha terminada em \n, exceto a
    # ultima linha do arquivo quando ele nao termina com quebra de linha.
    content = b"".join(line + b"\n" for line in block)
    if last_line == len(raw_lines) and not data.endswith(b"\n"):
        content = content[:-1]
    excerpt_path.write_bytes(content)

    result = ExcerptResult(
        source_txt=txt_path.name,
        source_txt_sha256=_sha256(txt_path),
        source_zip=zip_path.name if zip_path else "",
        source_zip_sha256=_sha256(zip_path) if zip_path and zip_path.exists() else "",
        start=start,
        end=end,
        total_messages=len(ordered),
        kept_messages=len(inside),
        first_line=first_line,
        last_line=last_line,
        excerpt_path=excerpt_path,
        excerpt_sha256=_sha256(excerpt_path),
    )
    attached = {m.group(1).strip() for msg in inside for m in _ATTACHMENT_RE.finditer(msg.content)}
    result.kept_attachments = [txt_path.parent / a for a in sorted(attached) if (txt_path.parent / a).exists()]
    return result


def discard_outside(result: ExcerptResult, files: list[Path]) -> None:
    """Apaga *files* (copia completa e midias fora do periodo), registrando os nomes."""
    keep = {p.resolve() for p in result.kept_attachments}
    for path in files:
        path = Path(path)
        if not path.exists() or path.resolve() in keep:
            continue
        try:
            path.unlink()
            result.removed_files.append(path.name)
        except OSError as exc:
            logger.warning("Nao foi possivel apagar %s: %s", path, exc)
    result.discarded = True


def write_excerpt_record(result: ExcerptResult, path: Path) -> Path:
    """Registro legivel do recorte; entra no manifesto carimbado."""
    lines = [
        "RECORTE DA CONVERSA EXPORTADA",
        "=" * 29,
        "",
        f"Periodo de interesse: {result.start:%d/%m/%Y} a {result.end:%d/%m/%Y}",
        f"Mensagens no periodo: {result.kept_messages} de {result.total_messages}",
        "",
        "Arquivo completo recebido:",
    ]
    if result.source_zip:
        lines.append(f"  ZIP:  {result.source_zip}")
        lines.append(f"        SHA-256 {result.source_zip_sha256}")
    lines += [
        f"  TXT:  {result.source_txt}",
        f"        SHA-256 {result.source_txt_sha256}",
        "",
        f"Recorte: linhas {result.first_line} a {result.last_line} do TXT, copiadas byte a byte",
        f"  Arquivo: {result.excerpt_path.name if result.excerpt_path else '-'}",
        f"  SHA-256 {result.excerpt_sha256}",
        "",
        "Para conferir com o arquivo completo (em poder do cliente ou de um perito):",
        "",
        f"  sha256sum \"{result.source_txt}\"      -> deve dar o SHA-256 do TXT acima",
        f"  {result.verify_command}",
        "                                         -> deve dar o SHA-256 do recorte acima",
        "",
    ]
    if result.discarded:
        lines += [
            "O restante da conversa foi DESCARTADO desta pasta, por privacidade. Ficaram",
            "apenas os hashes acima. A conferencia do recorte depende de alguem ainda ter",
            "o arquivo completo.",
            f"Arquivos apagados: {len(result.removed_files)}",
        ]
    else:
        lines += [
            "O arquivo completo foi guardado, lacrado, na pasta do caso; o relatorio mostra",
            "apenas o periodo de interesse.",
        ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
