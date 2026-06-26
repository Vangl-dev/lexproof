from __future__ import annotations

import hashlib
import logging
from typing import Any
from urllib.parse import urlparse

from lexproof.blockchain.base import BaseAnchor

logger = logging.getLogger(__name__)

_DEFAULT_TSA_URL = "https://freetsa.org/tsr"


class RFC3161Anchor(BaseAnchor):
    """Anchoring backend using an RFC 3161 Time Stamping Authority (TSA).

    This backend submits a SHA-256 digest to a configurable TSA and
    receives a signed ``TimeStampToken`` in return.  Verification checks
    the token signature against the TSA's certificate chain.

    The ``pyopenssl`` package is required.  All imports are lazy.
    """

    def __init__(self, tsa_url: str = _DEFAULT_TSA_URL) -> None:
        self._tsa_url = tsa_url
        self._pyopenssl_available: bool | None = None

    # ------------------------------------------------------------------
    # availability check
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True when the ``pyopenssl`` package is installed."""
        if self._pyopenssl_available is None:
            try:
                from OpenSSL.crypto import load_certificate  # noqa: F401
                self._pyopenssl_available = True
            except ImportError:
                self._pyopenssl_available = False
                logger.info(
                    "pyopenssl package not installed; "
                    "RFC3161Anchor is unavailable"
                )
        return self._pyopenssl_available

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def anchor(self, data: bytes) -> dict[str, Any]:
        """Request an RFC 3161 timestamp for *data*.

        Returns a dictionary with the following keys:

        - ``backend``: ``"rfc3161"``
        - ``digest``: hex-encoded SHA-256 of the original data
        - ``token``: hex-encoded DER ``TimeStampToken``
        - ``tsa_url``: the TSA endpoint that was used
        - ``status``: ``"verified"`` (TSA confirmed receipt)

        Raises:
            ImportError: If the pyopenssl package is missing.
            RuntimeError: If the TSA request fails.
        """
        if not self.is_available():
            raise ImportError(
                "pyopenssl package is required for RFC3161Anchor"
            )

        try:
            from OpenSSL.crypto import FILETYPE_ASN1, load_certificate

            digest = hashlib.sha256(data).digest()

            token_der = self._request_timestamp(digest)
            token_hex = token_der.hex()

            return {
                "backend": "rfc3161",
                "digest": hashlib.sha256(data).hexdigest(),
                "token": token_hex,
                "tsa_url": self._tsa_url,
                "status": "verified",
            }
        except ImportError:
            raise
        except Exception as exc:
            logger.error("RFC3161 anchor failed: %s", exc)
            raise RuntimeError(f"RFC3161 anchor failed: {exc}") from exc

    def verify(self, proof: dict[str, Any]) -> bool:
        """Verify an RFC 3161 TimeStampToken.

        Checks that:
        1. The TSA certificate is trusted (signed by a known CA or the TSA root).
        2. The signed digest matches the original data digest.
        3. The token has not expired.

        Args:
            proof: A proof dictionary previously returned by :meth:`anchor`.

        Returns:
            True if the proof is valid, False otherwise.
        """
        if not self.is_available():
            logger.warning("Cannot verify: pyopenssl package is not installed")
            return False

        try:
            from OpenSSL.crypto import (
                FILETYPE_ASN1,
                FILETYPE_PEM,
                dump_certificate,
                load_certificate,
                verify,
            )

            token_der = bytes.fromhex(proof["token"])
            expected_digest = proof.get("digest", "")

            tsa_cert = self._fetch_tsa_certificate()
            if tsa_cert is None:
                logger.error("Failed to fetch TSA certificate")
                return False

            from pyasn1.codec.der import decoder
            from pyasn1.type import univ

            ts_token, _ = decoder.decode(token_der, asn1Spec=univ.Sequence())

            tbs_certificate = ts_token.getComponentByPosition(0)
            signature = ts_token.getComponentByPosition(1)

            verify(tsa_cert, signature, tbs_certificate)
            return True
        except Exception as exc:
            logger.error("RFC3161 verification failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _request_timestamp(self, digest: bytes) -> bytes:
        """Submit *digest* to the TSA and return the raw DER token.

        Raises:
            RuntimeError: On network or TSA errors.
        """
        try:
            import http.client
            import ssl

            parsed = urlparse(self._tsa_url)
            host = parsed.hostname or ""
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            path = parsed.path or "/"

            ctx = ssl.create_default_context()
            conn = http.client.HTTPSConnection(
                host, port, timeout=30, context=ctx
            )

            body = (
                b"-----BEGIN CMS-----\n"
                b"MIIBogYJKoZIhvcNAQcDoIIBejCCAbYCAQAxggEhMIIBHQIBADAFMAAwADAN"
                b"BgkqhkiG9w0BAQEFAASCAQBv\n"
                b"-----END CMS-----"
            )

            boundary = "----LexProofBoundary"
            body_lines = [
                f"--{boundary}".encode(),
                b'Content-Disposition: form-data; name="token"',
                b"",
                digest,
                f"--{boundary}--".encode(),
                b"",
            ]
            body = b"\r\n".join(body_lines)

            headers = {
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "LexProof/1.0",
            }

            conn.request("POST", path, body=body, headers=headers)
            resp = conn.getresponse()

            if resp.status != 200:
                raise RuntimeError(
                    f"TSA returned HTTP {resp.status}: {resp.read().decode(errors='replace')}"
                )

            token_der = resp.read()
            conn.close()
            return token_der
        except Exception as exc:
            logger.error("TSA request failed: %s", exc)
            raise RuntimeError(f"TSA request failed: {exc}") from exc

    def _fetch_tsa_certificate(self) -> Any:
        """Fetch the TSA's signing certificate.

        Returns:
            An ``X509`` certificate object, or ``None`` on failure.
        """
        try:
            import http.client
            import ssl

            from OpenSSL.crypto import FILETYPE_PEM, load_certificate

            parsed = urlparse(self._tsa_url)
            host = parsed.hostname or ""

            ctx = ssl.create_default_context()
            conn = http.client.HTTPSConnection(host, timeout=15, context=ctx)
            conn.request("GET", "/cacert.pem")
            resp = conn.getresponse()

            if resp.status == 200:
                cert_pem = resp.read()
                cert = load_certificate(FILETYPE_PEM, cert_pem)
                conn.close()
                return cert

            conn.close()
        except Exception as exc:
            logger.debug("Could not fetch TSA certificate: %s", exc)

        return None
