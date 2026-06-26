"""Comparador de linhas do tempo para análise forense."""

from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Optional

from lexproof.models.timeline import TimelineEntry

logger = logging.getLogger(__name__)


class TimelineComparator:
    """Compara duas linhas do tempo para identificar convergências e divergências.

    Útil para validar a integridade de evidências comparando a versão
    extraída de TXT com a versão obtida via OCR, ou comparando cópias
    independentes da mesma conversa.
    """

    def __init__(self, match_threshold: float = 0.85) -> None:
        """Inicializa o comparador.

        Args:
            match_threshold: Limiar de similaridade para considerar duas entradas
                como correspondentes (0.0 a 1.0). Padrão: 0.85.
        """
        self._match_threshold = match_threshold

    def compare(
        self,
        timeline_a: list[TimelineEntry],
        timeline_b: list[TimelineEntry],
    ) -> dict:
        """Compara duas linhas do tempo e retorna análise detalhada.

        Args:
            timeline_a: Primeira linha do tempo (ex.: extraída de TXT).
            timeline_b: Segunda linha do tempo (ex.: extraída de OCR).

        Returns:
            Dicionário com:
            - matches: pares de entradas correspondentes
            - only_in_a: entradas presentes apenas em A
            - only_in_b: entradas presentes apenas em B
            - modified: entradas presentes em ambos mas com diferenças
            - match_percentage: percentual geral de correspondência
        """
        matches: list[dict[str, Optional[TimelineEntry]]] = []
        only_in_a: list[TimelineEntry] = []
        only_in_b: list[TimelineEntry] = []
        modified: list[dict[str, Optional[TimelineEntry]]] = []

        used_b: set[int] = set()

        for entry_a in timeline_a:
            best_match_idx: int | None = None
            best_score: float = 0.0

            for idx, entry_b in enumerate(timeline_b):
                if idx in used_b:
                    continue

                score = self._calculate_similarity(entry_a, entry_b)
                if score > best_score:
                    best_score = score
                    best_match_idx = idx

            if best_match_idx is not None and best_score >= self._match_threshold:
                used_b.add(best_match_idx)
                entry_b = timeline_b[best_match_idx]

                diffs = self._find_differences(entry_a, entry_b)
                if diffs:
                    modified.append(
                        {
                            "entry_a": entry_a,
                            "entry_b": entry_b,
                            "differences": diffs,
                            "similarity": best_score,
                        }
                    )
                else:
                    matches.append(
                        {
                            "entry_a": entry_a,
                            "entry_b": entry_b,
                            "similarity": best_score,
                        }
                    )
            else:
                only_in_a.append(entry_a)

        for idx, entry_b in enumerate(timeline_b):
            if idx not in used_b:
                only_in_b.append(entry_b)

        total = max(len(timeline_a), len(timeline_b), 1)
        match_pct = (len(matches) / total) * 100.0

        result = {
            "matches": matches,
            "only_in_a": only_in_a,
            "only_in_b": only_in_b,
            "modified": modified,
            "match_percentage": round(match_pct, 2),
        }

        logger.info(
            "Comparação concluída: %d correspondências, %d apenas em A, "
            "%d apenas em B, %d modificados (%.1f%% correspondência)",
            len(matches),
            len(only_in_a),
            len(only_in_b),
            len(modified),
            match_pct,
        )

        return result

    def _calculate_similarity(self, a: TimelineEntry, b: TimelineEntry) -> float:
        """Calcula pontuação de similaridade entre duas entradas.

        Considera timestamp, remetente e conteúdo com pesos diferentes.

        Args:
            a: Primeira entrada.
            b: Segunda entrada.

        Returns:
            Pontuação de similaridade entre 0.0 e 1.0.
        """
        score = 0.0
        weight_sum = 0.0

        ts_weight = 3.0
        weight_sum += ts_weight
        time_diff = abs((a.timestamp - b.timestamp).total_seconds())
        if time_diff < 60:
            score += ts_weight
        elif time_diff < 300:
            score += ts_weight * 0.8
        elif time_diff < 3600:
            score += ts_weight * 0.5
        else:
            score += ts_weight * max(0.0, 1.0 - time_diff / 86400.0)

        sender_weight = 2.0
        weight_sum += sender_weight
        if a.sender and b.sender:
            if a.sender == b.sender:
                score += sender_weight
            elif self._normalize(a.sender) == self._normalize(b.sender):
                score += sender_weight * 0.9
            else:
                ratio = SequenceMatcher(None, a.sender.lower(), b.sender.lower()).ratio()
                score += sender_weight * ratio
        elif not a.sender and not b.sender:
            score += sender_weight

        content_weight = 2.0
        weight_sum += content_weight
        if a.content and b.content:
            content_ratio = SequenceMatcher(None, a.content, b.content).ratio()
            score += content_weight * content_ratio
        elif not a.content and not b.content:
            score += content_weight

        return score / weight_sum if weight_sum > 0 else 0.0

    def _find_differences(
        self, a: TimelineEntry, b: TimelineEntry
    ) -> list[dict[str, str]]:
        """Identifica diferenças específicas entre duas entradas correspondentes.

        Args:
            a: Primeira entrada.
            b: Segunda entrada.

        Returns:
            Lista de diferenças encontradas, cada uma com campo, valor_a e valor_b.
        """
        diffs: list[dict[str, str]] = []

        if a.sender != b.sender:
            diffs.append(
                {
                    "field": "sender",
                    "value_a": a.sender or "(vazio)",
                    "value_b": b.sender or "(vazio)",
                }
            )

        if a.content != b.content:
            diffs.append(
                {
                    "field": "content",
                    "value_a": a.content,
                    "value_b": b.content,
                }
            )

        if a.entry_type != b.entry_type:
            diffs.append(
                {
                    "field": "entry_type",
                    "value_a": a.entry_type.value,
                    "value_b": b.entry_type.value,
                }
            )

        time_diff = abs((a.timestamp - b.timestamp).total_seconds())
        if time_diff >= 1.0:
            diffs.append(
                {
                    "field": "timestamp",
                    "value_a": a.timestamp.isoformat(),
                    "value_b": b.timestamp.isoformat(),
                }
            )

        return diffs

    def _normalize(self, text: str) -> str:
        """Normaliza uma string para comparação flexível.

        Args:
            text: String a ser normalizada.

        Returns:
            String normalizada em minúsculas, sem espaços extras.
        """
        return " ".join(text.lower().split())
