"""Módulo de aquisição forense do LexProof."""

from lexproof.acquisition.acquirer import ForensicAcquirer
from lexproof.acquisition.zip_handler import SecureZipHandler

__all__ = ["ForensicAcquirer", "SecureZipHandler"]
