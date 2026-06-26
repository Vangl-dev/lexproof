"""Ponto de entrada principal do LexProof."""

from __future__ import annotations

import sys

from lexproof.core.application import LexProofApplication


def main() -> int:
    """Inicia o aplicativo LexProof.

    Returns:
        Código de retorno do aplicativo.
    """
    app = LexProofApplication(sys.argv)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
