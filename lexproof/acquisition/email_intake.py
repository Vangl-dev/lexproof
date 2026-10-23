"""Recebimento de arquivos por e-mail, com conferencia da assinatura DKIM.

Quando o cliente envia os prints por e-mail, o servidor dele (Gmail,
Outlook...) assina a mensagem, anexos incluidos, com DKIM. Conferindo essa
assinatura ao receber, o LexProof registra que *estes* anexos sairam *daquele*
dominio com *aqueles* cabecalhos (remetente, data).

As chaves DKIM sao trocadas pelos provedores de tempos em tempos. Por isso a
chave publica consultada no DNS e arquivada junto com o e-mail: entra no
manifesto carimbado e permite refazer a conferencia no futuro.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DnsFunc = Callable[..., Optional[bytes]]

_UNSAFE_NAME = re.compile(r"[^\w.\- ()]+", re.UNICODE)


@dataclass
class DkimSignatureCheck:
    """Resultado de uma assinatura DKIM do e-mail."""

    domain: str
    selector: str
    valid: bool
    error: str = ""
    signed_headers: list[str] = field(default_factory=list)
    body_length_limited: bool = False
    dns_name: str = ""
    dns_record: str = ""


@dataclass
class EmailAttachment:
    """Anexo extraido do e-mail."""

    name: str
    path: Path
    sha256: str
    size: int


@dataclass
class EmailEvidence:
    """E-mail recebido e o resultado da conferencia."""

    eml_path: Path
    sender: str = ""
    sender_domain: str = ""
    to: str = ""
    subject: str = ""
    date: Optional[datetime] = None
    message_id: str = ""
    signatures: list[DkimSignatureCheck] = field(default_factory=list)
    attachments: list[EmailAttachment] = field(default_factory=list)
    error: str = ""

    @property
    def aligned_signature(self) -> Optional[DkimSignatureCheck]:
        """Assinatura valida do proprio dominio do remetente (ou de um pai dele)."""
        for sig in self.signatures:
            if sig.valid and _aligned(sig.domain, self.sender_domain):
                return sig
        return None

    @property
    def verified(self) -> bool:
        """DKIM valido, alinhado ao remetente e cobrindo o corpo inteiro."""
        sig = self.aligned_signature
        return sig is not None and not sig.body_length_limited and "from" in sig.signed_headers


def _aligned(sig_domain: str, from_domain: str) -> bool:
    sig_domain, from_domain = sig_domain.lower().strip("."), from_domain.lower().strip(".")
    return bool(sig_domain) and (from_domain == sig_domain or from_domain.endswith("." + sig_domain))


def _safe_name(name: str, used: set[str]) -> str:
    name = _UNSAFE_NAME.sub("_", Path(name).name).strip() or "anexo"
    base, ext = Path(name).stem, Path(name).suffix
    candidate, n = name, 1
    while candidate.lower() in used:
        candidate = f"{base} ({n}){ext}"
        n += 1
    used.add(candidate.lower())
    return candidate


def _default_dnsfunc() -> DnsFunc:
    from dkim.dnsplug import get_txt

    return get_txt


def check_dkim(raw: bytes, dnsfunc: Optional[DnsFunc] = None) -> list[DkimSignatureCheck]:
    """Confere todas as assinaturas DKIM de *raw*, guardando a chave consultada."""
    import dkim

    dnsfunc = dnsfunc or _default_dnsfunc()
    results: list[DkimSignatureCheck] = []
    count = len(re.findall(rb"(?im)^dkim-signature:", raw))
    for idx in range(count):
        seen: dict[str, bytes] = {}

        def recording(name: bytes | str, timeout: int = 5, _seen: dict = seen) -> Optional[bytes]:
            value = dnsfunc(name, timeout=timeout)
            key = name.decode() if isinstance(name, bytes) else name
            _seen[key] = value or b""
            return value

        d = dkim.DKIM(raw)
        check = DkimSignatureCheck(domain="", selector="", valid=False)
        try:
            check.valid = bool(d.verify(idx=idx, dnsfunc=recording))
        except Exception as exc:
            check.error = str(exc)
        fields = getattr(d, "signature_fields", {}) or {}
        check.domain = fields.get(b"d", b"").decode(errors="replace")
        check.selector = fields.get(b"s", b"").decode(errors="replace")
        check.body_length_limited = b"l" in fields
        check.signed_headers = [h.decode().lower() for h in getattr(d, "include_headers", ())]
        if seen:
            check.dns_name, record = next(iter(seen.items()))
            check.dns_record = record.decode(errors="replace")
        if not check.valid and not check.error:
            check.error = "assinatura nao confere"
        results.append(check)
    return results


def read_email(
    eml_path: Path,
    attachments_dir: Path,
    *,
    dnsfunc: Optional[DnsFunc] = None,
) -> EmailEvidence:
    """Le *eml_path*, confere o DKIM e extrai os anexos em *attachments_dir*."""
    eml_path = Path(eml_path)
    raw = eml_path.read_bytes()
    evidence = EmailEvidence(eml_path=eml_path)

    msg = BytesParser(policy=policy.default).parsebytes(raw)
    evidence.sender = str(msg.get("From", ""))
    evidence.sender_domain = parseaddr(evidence.sender)[1].rpartition("@")[2].lower()
    evidence.to = str(msg.get("To", ""))
    evidence.subject = str(msg.get("Subject", ""))
    evidence.message_id = str(msg.get("Message-ID", ""))
    try:
        evidence.date = parsedate_to_datetime(str(msg.get("Date", "")))
    except (TypeError, ValueError):
        evidence.date = None

    try:
        evidence.signatures = check_dkim(raw, dnsfunc)
    except Exception as exc:
        logger.warning("Falha ao conferir DKIM de %s: %s", eml_path.name, exc)
        evidence.error = f"DKIM: {exc}"

    attachments_dir = Path(attachments_dir)
    used: set[str] = set()
    for part in msg.iter_attachments():
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        name = _safe_name(part.get_filename() or "anexo", used)
        attachments_dir.mkdir(parents=True, exist_ok=True)
        target = attachments_dir / name
        target.write_bytes(payload)
        evidence.attachments.append(EmailAttachment(
            name=name, path=target, sha256=hashlib.sha256(payload).hexdigest(), size=len(payload),
        ))
    return evidence


def write_dkim_archive(evidences: list[EmailEvidence], path: Path) -> Optional[Path]:
    """Grava as chaves DKIM consultadas, para conferencia futura."""
    lines = []
    for ev in evidences:
        for sig in ev.signatures:
            if sig.dns_name:
                lines.append(f"# {ev.eml_path.name} | d={sig.domain} s={sig.selector} | valida={sig.valid}")
                lines.append(f"{sig.dns_name} TXT \"{sig.dns_record}\"")
    if not lines:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "Chaves publicas DKIM consultadas no DNS no momento da preservacao.\n"
        "Este arquivo esta no manifesto carimbado; permite refazer a conferencia\n"
        "mesmo depois que o provedor trocar a chave.\n\n" + "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return path
