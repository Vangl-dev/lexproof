"""Carimbo de tempo RFC 3161 emitido por uma Autoridade de Carimbo do Tempo (TSA).

Usa o utilitario ``openssl`` de linha de comando para montar a requisicao e
verificar a resposta. Os mesmos comandos podem ser executados por qualquer
pessoa para conferir o carimbo de forma independente do LexProof.
"""

from __future__ import annotations

import hashlib
import logging
import re
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lexproof.blockchain.base import BaseAnchor

logger = logging.getLogger(__name__)

_DEFAULT_TSA_URL = "https://freetsa.org/tsr"
_CERTS_DIR = Path(__file__).resolve().parent / "certs"
FREETSA_CA_FILE = _CERTS_DIR / "freetsa_cacert.pem"
FREETSA_TSA_CERT = _CERTS_DIR / "freetsa_tsa.crt"
DIGICERT_CA_FILE = _CERTS_DIR / "digicert_roots.pem"
SECTIGO_CA_FILE = _CERTS_DIR / "sectigo_roots.pem"

_GEN_TIME_RE = re.compile(r"^Time stamp:\s*(.+?)\s*$", re.MULTILINE)
_SERIAL_RE = re.compile(r"^Serial number:\s*(\S+)", re.MULTILINE)
_STATUS_RE = re.compile(r"^Status:\s*(.+?)\s*$", re.MULTILINE)


@dataclass
class TimestampProof:
    """Carimbo de tempo obtido para um arquivo."""

    tsa_url: str
    digest_sha256: str
    gen_time: datetime
    serial: str
    tsq_path: Path
    tsr_path: Path


class RFC3161Anchor(BaseAnchor):
    """Carimbo de tempo RFC 3161 via TSA (padrao: FreeTSA).

    Para validade ICP-Brasil, basta apontar ``tsa_url`` e os certificados
    para uma ACT credenciada.
    """

    def __init__(
        self,
        tsa_url: str = _DEFAULT_TSA_URL,
        ca_file: Path = FREETSA_CA_FILE,
        tsa_cert: Path | None = FREETSA_TSA_CERT,
        timeout: float = 30.0,
    ) -> None:
        self._tsa_url = tsa_url
        self._ca_file = Path(ca_file)
        self._tsa_cert = Path(tsa_cert) if tsa_cert else None
        self._timeout = timeout

    @property
    def tsa_url(self) -> str:
        return self._tsa_url

    @property
    def verify_args(self) -> str:
        """Argumentos de certificado para ``openssl ts -verify`` (nomes de arquivo)."""
        args = f"-CAfile {self._ca_file.name}"
        if self._tsa_cert is not None:
            args += f" -untrusted {self._tsa_cert.name}"
        return args

    @property
    def ca_file(self) -> Path:
        return self._ca_file

    @property
    def tsa_cert(self) -> Path | None:
        return self._tsa_cert

    def is_available(self) -> bool:
        """Retorna True quando o utilitario ``openssl`` esta instalado."""
        return shutil.which("openssl") is not None

    # ------------------------------------------------------------------
    # API por arquivo (usada pelo pipeline)
    # ------------------------------------------------------------------

    def stamp_file(self, path: Path) -> TimestampProof:
        """Solicita carimbo de tempo para *path*.

        Grava ``<arquivo>.tsq`` (requisicao) e ``<arquivo>.tsr`` (resposta
        assinada pela TSA) ao lado do arquivo.

        Raises:
            RuntimeError: Se o openssl faltar, a TSA recusar ou a rede falhar.
        """
        if not self.is_available():
            raise RuntimeError("openssl nao encontrado no sistema")

        path = Path(path)
        tsq_path = path.with_name(path.name + ".tsq")
        tsr_path = path.with_name(path.name + ".tsr")

        self._openssl(
            "ts", "-query", "-data", str(path), "-sha256", "-cert",
            "-out", str(tsq_path),
        )
        request = urllib.request.Request(
            self._tsa_url,
            data=tsq_path.read_bytes(),
            headers={
                "Content-Type": "application/timestamp-query",
                "User-Agent": "LexProof",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as resp:
                tsr_path.write_bytes(resp.read())
        except Exception as exc:
            raise RuntimeError(f"Falha ao contatar a TSA {self._tsa_url}: {exc}") from exc

        info = self.describe(tsr_path)
        if not info["status"].lower().startswith("granted"):
            raise RuntimeError(f"TSA recusou o carimbo: {info['status']}")
        if not self.verify_file(path, tsr_path):
            raise RuntimeError("Carimbo recebido nao confere com o arquivo")

        return TimestampProof(
            tsa_url=self._tsa_url,
            digest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            gen_time=info["gen_time"],
            serial=info["serial"],
            tsq_path=tsq_path,
            tsr_path=tsr_path,
        )

    def verify_file(self, path: Path, tsr_path: Path) -> bool:
        """Confere se *tsr_path* e um carimbo valido da TSA para *path*."""
        if not self.is_available():
            return False
        args = [
            "ts", "-verify", "-data", str(path), "-in", str(tsr_path),
            "-CAfile", str(self._ca_file),
        ]
        if self._tsa_cert is not None:
            args += ["-untrusted", str(self._tsa_cert)]
        try:
            out = self._openssl(*args)
        except RuntimeError as exc:
            logger.warning("Carimbo nao confere: %s", exc)
            return False
        return "Verification: OK" in out

    def describe(self, tsr_path: Path) -> dict[str, Any]:
        """Le status, horario e numero de serie de uma resposta da TSA."""
        text = self._openssl("ts", "-reply", "-in", str(tsr_path), "-text")
        status = _STATUS_RE.search(text)
        gen_time = _GEN_TIME_RE.search(text)
        serial = _SERIAL_RE.search(text)
        return {
            "status": status.group(1) if status else "desconhecido",
            "gen_time": _parse_openssl_time(gen_time.group(1)) if gen_time else None,
            "serial": serial.group(1) if serial else "",
        }

    # ------------------------------------------------------------------
    # API generica de BaseAnchor
    # ------------------------------------------------------------------

    def anchor(self, data: bytes) -> dict[str, Any]:
        """Carimba *data* e devolve a prova em formato de dicionario."""
        with tempfile.TemporaryDirectory(prefix="lexproof_tsa_") as tmp:
            path = Path(tmp) / "data.bin"
            path.write_bytes(data)
            proof = self.stamp_file(path)
            return {
                "backend": "rfc3161",
                "digest": proof.digest_sha256,
                "token": proof.tsr_path.read_bytes().hex(),
                "tsa_url": proof.tsa_url,
                "gen_time": proof.gen_time.isoformat() if proof.gen_time else None,
                "serial": proof.serial,
                "status": "verified",
            }

    def verify(self, proof: dict[str, Any]) -> bool:
        """Confere uma prova produzida por :meth:`anchor`.

        A prova precisa trazer os dados originais em ``data`` (bytes), pois
        o carimbo atesta o hash e nao pode ser conferido sem o conteudo.
        """
        data = proof.get("data")
        token = proof.get("token")
        if not isinstance(data, (bytes, bytearray)) or not token:
            return False
        with tempfile.TemporaryDirectory(prefix="lexproof_tsa_") as tmp:
            path = Path(tmp) / "data.bin"
            tsr = Path(tmp) / "data.bin.tsr"
            path.write_bytes(bytes(data))
            tsr.write_bytes(bytes.fromhex(token))
            return self.verify_file(path, tsr)

    # ------------------------------------------------------------------

    def _openssl(self, *args: str) -> str:
        try:
            proc = subprocess.run(
                ["openssl", *args],
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"openssl falhou: {exc}") from exc
        output = proc.stdout + proc.stderr
        if proc.returncode != 0:
            raise RuntimeError(output.strip().splitlines()[-1] if output.strip() else "openssl falhou")
        return output


def default_anchors() -> list[RFC3161Anchor]:
    """TSAs gratuitas, em ordem de preferencia. As seguintes so sao usadas se a
    anterior falhar (fora do ar, limite de pedidos)."""
    return [
        RFC3161Anchor(),
        RFC3161Anchor("http://timestamp.digicert.com", DIGICERT_CA_FILE, None),
        RFC3161Anchor("http://timestamp.sectigo.com", SECTIGO_CA_FILE, None),
    ]


def _parse_openssl_time(value: str) -> datetime | None:
    """Converte 'Oct 22 18:42:16 2026 GMT' (com fracao opcional) em datetime UTC."""
    # strptime("%b") depende do locale, que o Qt altera; o openssl sempre
    # escreve os meses em ingles.
    m = re.match(r"(\w{3})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?\s+(\d{4})", value)
    if not m or m.group(1) not in _MONTHS:
        logger.warning("Horario do carimbo nao reconhecido: %s", value)
        return None
    mon, day, hh, mm, ss, year = m.groups()
    return datetime(
        int(year), _MONTHS.index(mon) + 1, int(day), int(hh), int(mm), int(ss),
        tzinfo=timezone.utc,
    )


_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
