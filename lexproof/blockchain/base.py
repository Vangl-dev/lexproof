from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAnchor(ABC):
    """Abstract base class for blockchain anchoring backends.

    All anchoring implementations must subclass this and provide
    concrete implementations for anchor, verify, and is_available.
    """

    @abstractmethod
    def anchor(self, data: bytes) -> dict[str, Any]:
        """Create a timestamp anchor proof for the given data.

        Args:
            data: Raw bytes to anchor.

        Returns:
            A dictionary containing the anchor proof (structure depends on
            the backend implementation).

        Raises:
            RuntimeError: If the anchoring operation fails.
        """
        ...

    @abstractmethod
    def verify(self, proof: dict[str, Any]) -> bool:
        """Verify that a previously created anchor proof is valid.

        Args:
            proof: The proof dictionary returned by :meth:`anchor`.

        Returns:
            True if the proof is valid, False otherwise.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether this anchoring backend is usable.

        Returns:
            True if all required dependencies are installed and the backend
            can perform its operations.
        """
        ...
