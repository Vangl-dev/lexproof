"""Ponto de entrada principal do LexProof."""

import sys
from lexproof.core.application import LexProofApplication


def main() -> int:
    """Inicia o aplicativo LexProof.

    Returns:
        Código de retorno do aplicativo.
    """
    app = LexProofApplication(sys.argv)
    return app.run()
