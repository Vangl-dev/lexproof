from __future__ import annotations

import hashlib
import logging
from typing import Any

from lexproof.blockchain.base import BaseAnchor

logger = logging.getLogger(__name__)


class OpenTimestampsAnchor(BaseAnchor):
    """Anchoring backend using OpenTimestamps.

    OpenTimestamps provides a decentralized, public timestamping protocol.
    Timestamps are initially *unpaid* (pending calendar aggregation) and
    can later be upgraded to *paid* Bitcoin-anchored proofs.

    All ``opentimestamps`` imports are lazy so the application remains
    fully functional without the dependency installed.
    """

    def __init__(self) -> None:
        self._ots_available: bool | None = None

    # ------------------------------------------------------------------
    # availability check
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True when the ``opentimestamps`` package is installed."""
        if self._ots_available is None:
            try:
                import opentimestamps  # noqa: F401
                self._ots_available = True
            except ImportError:
                self._ots_available = False
                logger.info(
                    "opentimestamps package not installed; "
                    "OpenTimestampsAnchor is unavailable"
                )
        return self._ots_available

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def anchor(self, data: bytes) -> dict[str, Any]:
        """Create an OpenTimestamps timestamp proof for *data*.

        Returns a dictionary with the following keys:

        - ``backend``: ``"opentimestamps"``
        - ``digest``: hex-encoded SHA-256 of the original data
        - ``proof``: hex-encoded serialized proof bytes
        - ``calendar_id``: the calendar URI used
        - ``status``: ``"pending"`` (unpaid) or ``"verified"``

        Raises:
            ImportError: If the opentimestamps package is missing.
            RuntimeError: If timestamp creation fails.
        """
        if not self.is_available():
            raise ImportError(
                "opentimestamps package is required for OpenTimestampsAnchor"
            )

        from opentimestamps.calendar import Calendar
        from opentimestamps.timestamp import Timestamp

        digest = hashlib.sha256(data).hexdigest()

        try:
            stamp = Timestamp(hashlib.sha256(data).digest())
            calendar = Calendar("https://timestamp.opentimestamps.org")

            attestation = calendar.stamp(stamp)
            proof_bytes = attestation.serialize()

            return {
                "backend": "opentimestamps",
                "digest": digest,
                "proof": proof_bytes.hex(),
                "calendar_id": "https://timestamp.opentimestamps.org",
                "status": "pending",
            }
        except Exception as exc:
            logger.error("OpenTimestamps anchor failed: %s", exc)
            raise RuntimeError(f"OpenTimestamps anchor failed: {exc}") from exc

    def verify(self, proof: dict[str, Any]) -> bool:
        """Verify an OpenTimestamps proof.

        Args:
            proof: A proof dictionary previously returned by :meth:`anchor`.

        Returns:
            True if the proof verifies, False otherwise.
        """
        if not self.is_available():
            logger.warning(
                "Cannot verify: opentimestamps package is not installed"
            )
            return False

        try:
            from opentimestamps.calendar import Calendar
            from opentimestamps.timestamp import Timestamp

            proof_bytes = bytes.fromhex(proof["proof"])
            digest = proof.get("digest", "")
            calendar_id = proof.get(
                "calendar_id", "https://timestamp.opentimestamps.org"
            )

            stamp = Timestamp(bytes.fromhex(digest))
            attestation = stamp.deserialize_attestation(proof_bytes)

            calendar = Calendar(calendar_id)
            result = calendar.get_verification(attestation)

            return result is not None
        except Exception as exc:
            logger.error("OpenTimestamps verification failed: %s", exc)
            return False
