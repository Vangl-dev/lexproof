from __future__ import annotations

import logging
from typing import Any

from lexproof.blockchain.base import BaseAnchor

logger = logging.getLogger(__name__)


class AnchorManager:
    """Manages multiple blockchain anchoring backends.

    Backends are registered by name and can be used to create and verify
    timestamp proofs.  The manager gracefully handles backends that are
    unavailable (e.g. optional dependency not installed).

    Example::

        manager = AnchorManager()
        manager.register_anchor("ots", OpenTimestampsAnchor())
        manager.register_anchor("tsa", RFC3161Anchor())

        proofs = manager.anchor_all(b"document content")
        results = manager.verify_all(proofs)
    """

    def __init__(self) -> None:
        self._anchors: dict[str, BaseAnchor] = {}

    # ------------------------------------------------------------------
    # registration
    # ------------------------------------------------------------------

    def register_anchor(self, name: str, anchor: BaseAnchor) -> None:
        """Register an anchoring backend under *name*.

        Args:
            name: A short identifier for the backend (e.g. ``"ots"``).
            anchor: A :class:`BaseAnchor` instance.

        Raises:
            TypeError: If *anchor* is not a :class:`BaseAnchor` subclass.
        """
        if not isinstance(anchor, BaseAnchor):
            raise TypeError(
                f"Expected a BaseAnchor instance, got {type(anchor).__name__}"
            )
        self._anchors[name] = anchor
        logger.info("Registered anchoring backend: %s (%s)", name, type(anchor).__name__)

    def unregister_anchor(self, name: str) -> None:
        """Remove a previously registered backend.

        Args:
            name: The name of the backend to remove.

        Raises:
            KeyError: If *name* is not registered.
        """
        if name not in self._anchors:
            raise KeyError(f"No anchor registered with name '{name}'")
        del self._anchors[name]
        logger.info("Unregistered anchoring backend: %s", name)

    # ------------------------------------------------------------------
    # querying
    # ------------------------------------------------------------------

    def get_available_anchors(self) -> list[str]:
        """Return the names of all registered backends that are currently usable.

        Returns:
            A list of backend names whose :meth:`BaseAnchor.is_available`
            returns True.
        """
        available: list[str] = []
        for name, anchor in self._anchors.items():
            try:
                if anchor.is_available():
                    available.append(name)
            except Exception as exc:
                logger.debug(
                    "Error checking availability of anchor '%s': %s",
                    name,
                    exc,
                )
        return available

    def list_anchors(self) -> dict[str, bool]:
        """Return all registered backends and their availability status.

        Returns:
            A dictionary mapping backend name to its availability boolean.
        """
        result: dict[str, bool] = {}
        for name, anchor in self._anchors.items():
            try:
                result[name] = anchor.is_available()
            except Exception as exc:
                logger.debug(
                    "Error checking availability of anchor '%s': %s",
                    name,
                    exc,
                )
                result[name] = False
        return result

    # ------------------------------------------------------------------
    # anchoring
    # ------------------------------------------------------------------

    def anchor_all(self, data: bytes) -> dict[str, dict[str, Any]]:
        """Anchor *data* using every available backend.

        Backends that are unavailable or fail are silently skipped with a
        warning logged.  The returned dictionary always contains an entry
        for every *available* backend.

        Args:
            data: Raw bytes to anchor.

        Returns:
            A dictionary mapping backend name to its proof dictionary.
        """
        proofs: dict[str, dict[str, Any]] = {}
        for name, anchor in self._anchors.items():
            if not anchor.is_available():
                logger.debug("Skipping unavailable anchor: %s", name)
                continue
            try:
                proof = anchor.anchor(data)
                proofs[name] = proof
                logger.info("Anchored data with backend '%s'", name)
            except Exception as exc:
                logger.warning("Anchor '%s' failed: %s", name, exc)
        return proofs

    # ------------------------------------------------------------------
    # verification
    # ------------------------------------------------------------------

    def verify_all(self, proofs: dict[str, Any]) -> dict[str, bool]:
        """Verify proofs across all backends that have a matching entry.

        Each top-level key in *proofs* should be a backend name.  The
        value is passed to that backend's :meth:`BaseAnchor.verify` method.

        Args:
            proofs: A dictionary mapping backend names to proof objects.

        Returns:
            A dictionary mapping backend names to verification booleans.
            Missing backends are omitted.
        """
        results: dict[str, bool] = {}
        for name, proof in proofs.items():
            anchor = self._anchors.get(name)
            if anchor is None:
                logger.debug("No anchor registered for name '%s'", name)
                continue
            if not anchor.is_available():
                logger.debug("Skipping verification for unavailable anchor: %s", name)
                continue
            try:
                results[name] = anchor.verify(proof)
                logger.info(
                    "Verification result for '%s': %s",
                    name,
                    results[name],
                )
            except Exception as exc:
                logger.warning("Verification failed for '%s': %s", name, exc)
                results[name] = False
        return results

    # ------------------------------------------------------------------
    # convenience
    # ------------------------------------------------------------------

    def anchor_and_verify(self, data: bytes) -> dict[str, Any]:
        """Anchor *data* with all backends and immediately verify.

        Returns:
            A dictionary mapping backend names to dicts with ``"proof"``
            and ``"verified"`` keys.
        """
        proofs = self.anchor_all(data)
        results: dict[str, Any] = {}
        for name, proof in proofs.items():
            verified = False
            anchor = self._anchors.get(name)
            if anchor is not None:
                try:
                    verified = anchor.verify(proof)
                except Exception as exc:
                    logger.warning(
                        "Post-anchor verification failed for '%s': %s",
                        name,
                        exc,
                    )
            results[name] = {"proof": proof, "verified": verified}
        return results
