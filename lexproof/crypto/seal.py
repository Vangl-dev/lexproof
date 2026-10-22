"""Selo de preservacao: manifesto de hashes + carimbo de tempo.

Grava em ``<caso>/preservacao/`` tudo o que um terceiro precisa para
conferir, sem o LexProof, que os arquivos nao mudaram desde o carimbo:

- ``manifesto-sha256.txt``: SHA-256 de cada original, no formato do
  ``sha256sum`` (conferivel com ``sha256sum -c``);
- ``manifesto-sha256.txt.tsq`` / ``.tsr``: requisicao e carimbo da TSA;
- certificados publicos da TSA;
- ``COMO_VERIFICAR.txt``: os comandos de conferencia.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from lexproof.blockchain.rfc3161 import RFC3161Anchor, TimestampProof

logger = logging.getLogger(__name__)

SEAL_DIR_NAME = "preservacao"
MANIFEST_NAME = "manifesto-sha256.txt"


@dataclass
class SealResult:
    """Resultado do selo de um caso."""

    seal_dir: Path
    manifest_path: Path
    manifest_sha256: str
    files: list[tuple[str, str]] = field(default_factory=list)
    timestamp: Optional[TimestampProof] = None
    timestamp_error: Optional[str] = None
    verify_command: str = ""

    @property
    def timestamped(self) -> bool:
        return self.timestamp is not None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def seal_case(
    case_dir: Path,
    files: list[Path],
    *,
    anchors: Sequence[RFC3161Anchor] | RFC3161Anchor | None = None,
    case_label: str = "",
    retry_delay: float = 2.0,
) -> SealResult:
    """Gera o manifesto dos *files* e o carimba com a primeira TSA que responder.

    Cada TSA recebe ate duas tentativas. Falha de todas nao impede o
    manifesto: fica registrada em ``timestamp_error`` para o relatorio.
    """
    if isinstance(anchors, RFC3161Anchor):
        anchors = [anchors]
    case_dir = Path(case_dir)
    seal_dir = case_dir / SEAL_DIR_NAME
    seal_dir.mkdir(parents=True, exist_ok=True)

    entries: list[tuple[str, str]] = []
    for path in sorted({Path(f).resolve() for f in files}):
        try:
            rel = path.relative_to(case_dir.resolve()).as_posix()
        except ValueError:
            rel = path.name
        entries.append((_sha256_file(path), rel))

    # Caminhos relativos a pasta do caso: "sha256sum -c" roda de dentro dela.
    manifest_path = seal_dir / MANIFEST_NAME
    lines = [f"{digest}  {rel}" for digest, rel in entries]
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest_sha256 = _sha256_file(manifest_path)

    result = SealResult(
        seal_dir=seal_dir,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        files=entries,
    )

    used: Optional[RFC3161Anchor] = None
    errors: list[str] = []
    for anchor in anchors or []:
        for attempt in range(2):
            try:
                result.timestamp = anchor.stamp_file(manifest_path)
                used = anchor
                break
            except Exception as exc:
                logger.warning("Carimbo via %s falhou: %s", anchor.tsa_url, exc)
                if attempt == 0:
                    time.sleep(retry_delay)
                else:
                    errors.append(f"{anchor.tsa_url}: {exc}")
        if used is not None:
            break

    if used is not None:
        shutil.copy2(used.ca_file, seal_dir / used.ca_file.name)
        if used.tsa_cert is not None:
            shutil.copy2(used.tsa_cert, seal_dir / used.tsa_cert.name)
        result.verify_command = (
            f"openssl ts -verify -data {MANIFEST_NAME} -in {MANIFEST_NAME}.tsr {used.verify_args}"
        )
    elif errors:
        result.timestamp_error = "; ".join(errors)

    _write_instructions(result, used, case_label)
    return result


def _write_instructions(
    result: SealResult, anchor: Optional[RFC3161Anchor], case_label: str
) -> None:
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")
    text = [
        "COMO VERIFICAR ESTA PRESERVACAO",
        "=" * 31,
        "",
        f"Caso: {case_label or '-'}",
        f"Manifesto gerado em: {now}",
        f"SHA-256 do manifesto: {result.manifest_sha256}",
        "",
        "1) Conferir que os arquivos nao mudaram",
        "   Abra um terminal na pasta do caso (a pasta que contem 'evidence/')",
        "   e execute:",
        "",
        f"     sha256sum -c {SEAL_DIR_NAME}/{MANIFEST_NAME}",
        "",
        "   Cada linha deve terminar em 'OK'. No Windows (PowerShell), compare",
        "   o resultado de 'Get-FileHash -Algorithm SHA256 <arquivo>' com a",
        "   linha correspondente do manifesto.",
        "",
    ]
    if result.timestamp is not None and anchor is not None:
        ts = result.timestamp
        gen = ts.gen_time.strftime("%d/%m/%Y %H:%M:%S UTC") if ts.gen_time else "-"
        text += [
            "2) Conferir que o manifesto ja existia na data do carimbo",
            f"   Carimbo emitido por: {ts.tsa_url}",
            f"   Horario atestado pela TSA: {gen}",
            f"   Numero de serie: {ts.serial}",
            "",
            f"   Dentro da pasta '{SEAL_DIR_NAME}', execute:",
            "",
            f"     {result.verify_command}",
            "",
            "   O resultado deve ser 'Verification: OK'. Se qualquer byte do",
            "   manifesto (ou de um arquivo listado nele) tivesse mudado, a",
            "   conferencia falharia.",
            "",
            "   Para ver o horario do carimbo:",
            "",
            f"     openssl ts -reply -in {MANIFEST_NAME}.tsr -text",
            "",
        ]
    else:
        text += [
            "2) Carimbo de tempo",
            "   Nao foi obtido nesta preservacao"
            + (f" ({result.timestamp_error})." if result.timestamp_error else "."),
            "   Sem carimbo, o manifesto prova integridade a partir do momento em",
            "   que for entregue a um terceiro, mas nao a data da preservacao.",
            "",
        ]
    text += [
        "O que esta verificacao NAO prova: a autenticidade do conteudo antes",
        "de ele ser entregue ao LexProof.",
    ]
    (result.seal_dir / "COMO_VERIFICAR.txt").write_text("\n".join(text) + "\n", encoding="utf-8")
