"""Gerador de relatórios de verificação do LexProof."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from lexproof.models.verification import VerificationResult, VerificationStatus

logger = logging.getLogger(__name__)


class VerificationReporter:
    """Gera relatórios humanos e estruturados a partir de resultados de verificação.

    Formata resultados para exibição em terminal, gera dicionários para
    serialização JSON e produz resumos estatísticos.
    """

    _STATUS_SYMBOLS: dict[VerificationStatus, str] = {
        VerificationStatus.PASS: "[PASS]",
        VerificationStatus.FAIL: "[FAIL]",
        VerificationStatus.WARNING: "[WARN]",
        VerificationStatus.INCONCLUSIVE: "[????]",
        VerificationStatus.NOT_APPLICABLE: "[N/A]",
    }

    _STATUS_COLORS: dict[VerificationStatus, str] = {
        VerificationStatus.PASS: "\033[92m",
        VerificationStatus.FAIL: "\033[91m",
        VerificationStatus.WARNING: "\033[93m",
        VerificationStatus.INCONCLUSIVE: "\033[96m",
        VerificationStatus.NOT_APPLICABLE: "\033[90m",
    }

    RESET_COLOR = "\033[0m"

    def format_results(self, results: list[VerificationResult]) -> str:
        """Formata os resultados de verificação em texto legível.

        Args:
            results: Lista de resultados de verificação.

        Returns:
            Texto formatado com o resultado de cada verificação.
        """
        if not results:
            return "Nenhuma verificação executada."

        lines: list[str] = []
        lines.append("=" * 70)
        lines.append("RELATORIO DE VERIFICACAO - LexProof")
        lines.append(f"Gerado em: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("=" * 70)
        lines.append("")

        summary = self.get_summary(results)
        lines.append(
            f"Resumo: {summary['pass']} PASS | {summary['fail']} FAIL | "
            f"{summary['warning']} WARN | {summary['inconclusive']} INCONCLUSIVE | "
            f"{summary['not_applicable']} N/A"
        )
        lines.append("-" * 70)
        lines.append("")

        for i, result in enumerate(results, 1):
            symbol = self._STATUS_SYMBOLS.get(result.status, "[????]")
            lines.append(f"{i}. {symbol} {result.check_name}")

            if result.expected:
                lines.append(f"   Esperado: {result.expected}")
            if result.actual:
                lines.append(f"   Encontrado: {result.actual}")

            if result.details:
                details_str = self._format_details(result.details)
                if details_str:
                    lines.append(f"   Detalhes: {details_str}")

            lines.append("")

        lines.append("=" * 70)
        total = len(results)
        pass_pct = (summary["pass"] / total * 100) if total > 0 else 0
        lines.append(f"Total: {total} verificacoes | {pass_pct:.1f}% de aprovacao")
        lines.append("=" * 70)

        return "\n".join(lines)

    def format_results_colored(self, results: list[VerificationResult]) -> str:
        """Formata os resultados com cores ANSI para exibição em terminal.

        Args:
            results: Lista de resultados de verificação.

        Returns:
            Texto formatado com cores ANSI.
        """
        if not results:
            return "Nenhuma verificacao executada."

        lines: list[str] = []
        lines.append("\033[1m" + "=" * 70 + self.RESET_COLOR)
        lines.append("\033[1mRELATORIO DE VERIFICACAO - LexProof\033[0m")
        lines.append(f"Gerado em: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("\033[1m" + "=" * 70 + self.RESET_COLOR)
        lines.append("")

        for i, result in enumerate(results, 1):
            color = self._STATUS_COLORS.get(result.status, "")
            symbol = self._STATUS_SYMBOLS.get(result.status, "[????]")
            lines.append(f"{color}{i}. {symbol}{self.RESET_COLOR} {result.check_name}")

            if result.expected:
                lines.append(f"   Esperado: {result.expected}")
            if result.actual:
                lines.append(f"   Encontrado: {result.actual}")

            lines.append("")

        summary = self.get_summary(results)
        total = len(results)
        pass_pct = (summary["pass"] / total * 100) if total > 0 else 0

        lines.append(
            f"{self._STATUS_COLORS[VerificationStatus.PASS]}"
            f"{summary['pass']} PASS{self.RESET_COLOR} | "
            f"{self._STATUS_COLORS[VerificationStatus.FAIL]}"
            f"{summary['fail']} FAIL{self.RESET_COLOR} | "
            f"{self._STATUS_COLORS[VerificationStatus.WARNING]}"
            f"{summary['warning']} WARN{self.RESET_COLOR} | "
            f"{pass_pct:.1f}% aprovacao"
        )

        return "\n".join(lines)

    def to_dict(self, results: list[VerificationResult]) -> dict:
        """Converte os resultados de verificação em dicionário serializável.

        Args:
            results: Lista de resultados de verificação.

        Returns:
            Dicionário com a lista de resultados e um resumo.
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": self.get_summary(results),
            "results": [result.model_dump(mode="json") for result in results],
        }

    def get_summary(self, results: list[VerificationResult]) -> dict[str, int]:
        """Gera resumo estatístico dos resultados de verificação.

        Args:
            results: Lista de resultados de verificação.

        Returns:
            Dicionário com contagens por status: pass, fail, warning,
            inconclusive, not_applicable.
        """
        counts: dict[str, int] = {
            "pass": 0,
            "fail": 0,
            "warning": 0,
            "inconclusive": 0,
            "not_applicable": 0,
        }

        status_to_key: dict[VerificationStatus, str] = {
            VerificationStatus.PASS: "pass",
            VerificationStatus.FAIL: "fail",
            VerificationStatus.WARNING: "warning",
            VerificationStatus.INCONCLUSIVE: "inconclusive",
            VerificationStatus.NOT_APPLICABLE: "not_applicable",
        }

        for result in results:
            key = status_to_key.get(result.status, "inconclusive")
            counts[key] += 1

        counts["total"] = len(results)

        logger.debug(
            "Resumo: %d pass, %d fail, %d warn, %d inconclusive, %d N/A",
            counts["pass"],
            counts["fail"],
            counts["warning"],
            counts["inconclusive"],
            counts["not_applicable"],
        )

        return counts

    def _format_details(self, details: dict[str, Any]) -> str:
        """Formata detalhes de verificação em string legível.

        Args:
            details: Dicionário de detalhes.

        Returns:
            String formatada com os detalhes relevantes.
        """
        parts: list[str] = []

        for key, value in details.items():
            if key == "issues" and isinstance(value, list):
                if value:
                    parts.append(f"{len(value)} problema(s) encontrado(s)")
            elif key == "mismatch_details" and isinstance(value, list):
                if value:
                    parts.append(f"{len(value)} divergencia(s) de hash")
            elif key == "out_of_order_examples" and isinstance(value, list):
                if value:
                    parts.append(f"{len(value)} exemplo(s) fora de ordem")
            elif isinstance(value, (int, float)):
                if key.endswith("_ratio") or key.endswith("_percentage"):
                    parts.append(f"{key}: {value * 100:.1f}%")
                elif key.endswith("_count"):
                    parts.append(f"{key}: {value}")
            elif isinstance(value, str) and value and key == "reason":
                parts.append(value)

        return "; ".join(parts) if parts else ""
