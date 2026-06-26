"""Construtor de linha do tempo consolidada a partir de mensagens e resultados OCR."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from lexproof.models.message import MessageType, WhatsAppMessage
from lexproof.models.ocr_result import OCRResult
from lexproof.models.timeline import TimelineEntry, TimelineEntryType

logger = logging.getLogger(__name__)


class TimelineBuilder:
    """Constrói uma linha do tempo consolidada a partir de múltiplas fontes.

    Responsável por mesclar mensagens extraídas de arquivos TXT com resultados
    de OCR, ordenar cronologicamente e detectar inconsistências como duplicatas,
    lacunas temporais e mensagens fora de ordem.
    """

    def __init__(self, gap_threshold_seconds: float = 3600.0) -> None:
        """Inicializa o construtor da linha do tempo.

        Args:
            gap_threshold_seconds: Limite em segundos para considerar uma lacuna
                temporal significativa. Padrão: 3600 (1 hora).
        """
        self._entries: list[TimelineEntry] = []
        self._gap_threshold_seconds = gap_threshold_seconds

    def build_timeline(
        self,
        messages: list[WhatsAppMessage],
        ocr_results: list[OCRResult] | None = None,
    ) -> list[TimelineEntry]:
        """Constrói a linha do tempo consolidada.

        Mescla mensagens extraídas de TXT com resultados de OCR, ordena por
        timestamp e detecta inconsistências.

        Args:
            messages: Lista de mensagens extraídas do arquivo TXT.
            ocr_results: Lista opcional de resultados OCR para mesclar.

        Returns:
            Lista de entradas da linha do tempo ordenadas cronologicamente
            e com inconsistências marcadas.
        """
        self._entries = []

        for msg in messages:
            entry = self._message_to_entry(msg)
            self._entries.append(entry)

        if ocr_results:
            for ocr in ocr_results:
                ocr_entries = self._ocr_to_entries(ocr)
                self._entries.extend(ocr_entries)

        self.sort()
        self.detect_duplicates()
        self.detect_gaps()

        logger.info(
            "Linha do tempo construída com %d entradas e %d inconsistências.",
            len(self._entries),
            sum(len(e.inconsistencies) for e in self._entries),
        )

        return list(self._entries)

    def add_entries(self, entries: list[TimelineEntry]) -> None:
        """Adiciona entradas externas à linha do tempo.

        Args:
            entries: Lista de entradas a serem adicionadas.
        """
        self._entries.extend(entries)
        logger.debug("Adicionadas %d entradas à linha do tempo.", len(entries))

    def sort(self) -> None:
        """Ordena as entradas da linha do tempo por timestamp.

        Em caso de empate, mantém a ordem original de inserção.
        """
        self._entries.sort(key=lambda e: e.timestamp)
        logger.debug("Entradas ordenadas por timestamp.")

    def detect_duplicates(self) -> int:
        """Detecta entradas duplicadas na linha do tempo.

        Considera duplicatas entradas com mesmo remetente, conteúdo e timestamp
        (com tolerância de 1 segundo).

        Returns:
            Número de duplicatas encontradas.
        """
        seen: list[TimelineEntry] = []
        duplicate_count = 0

        for entry in self._entries:
            is_dup = False
            for existing in seen:
                if (
                    entry.sender == existing.sender
                    and entry.content == existing.content
                    and entry.entry_type == existing.entry_type
                    and abs((entry.timestamp - existing.timestamp).total_seconds()) < 1.0
                ):
                    inconsistency = "Duplicata detectada: entrada similar já existe"
                    if inconsistency not in entry.inconsistencies:
                        entry.inconsistencies.append(inconsistency)
                    is_dup = True
                    duplicate_count += 1
                    break
            seen.append(entry)

        logger.debug("Detectadas %d entradas duplicadas.", duplicate_count)
        return duplicate_count

    def detect_gaps(self) -> int:
        """Detecta lacunas temporais significativas entre entradas consecutivas.

        Lacunas maiores que o threshold configurado são marcadas como
        inconsistências nas entradas adjacentes.

        Returns:
            Número de lacunas significativas encontradas.
        """
        if len(self._entries) < 2:
            return 0

        gap_count = 0
        for i in range(len(self._entries) - 1):
            current = self._entries[i]
            next_entry = self._entries[i + 1]
            delta = (next_entry.timestamp - current.timestamp).total_seconds()

            if delta > self._gap_threshold_seconds:
                hours = delta / 3600.0
                gap_msg = f"Lacuna temporal de {hours:.1f}h detectada"

                if gap_msg not in current.inconsistencies:
                    current.inconsistencies.append(gap_msg)
                if gap_msg not in next_entry.inconsistencies:
                    next_entry.inconsistencies.append(gap_msg)

                gap_entry = TimelineEntry(
                    entry_type=TimelineEntryType.TIMESTAMP_GAP,
                    timestamp=current.timestamp + timedelta(seconds=delta / 2),
                    content=f"Lacuna de {hours:.1f}h entre mensagens",
                    source_file=current.source_file,
                    notes=f"Gap entre linha {current.line_in_source or '?'} e {next_entry.line_in_source or '?'}",
                    inconsistencies=[],
                )
                self._entries.append(gap_entry)
                gap_count += 1

        if gap_count > 0:
            self.sort()

        logger.debug("Detectadas %d lacunas temporais.", gap_count)
        return gap_count

    def get_inconsistencies(self) -> list[TimelineEntry]:
        """Retorna apenas as entradas que possuem inconsistências.

        Returns:
            Lista de entradas com pelo menos uma inconsistência registrada.
        """
        return [e for e in self._entries if e.inconsistencies]

    def _message_to_entry(self, msg: WhatsAppMessage) -> TimelineEntry:
        """Converte uma WhatsAppMessage em uma TimelineEntry.

        Args:
            msg: Mensagem do WhatsApp a ser convertida.

        Returns:
            Entrada equivalente na linha do tempo.
        """
        entry_type_map: dict[MessageType, TimelineEntryType] = {
            MessageType.TEXT: TimelineEntryType.MESSAGE,
            MessageType.MEDIA: TimelineEntryType.MEDIA,
            MessageType.DELETED: TimelineEntryType.DELETION,
            MessageType.EDITED: TimelineEntryType.EDIT,
            MessageType.SYSTEM: TimelineEntryType.SYSTEM_EVENT,
            MessageType.STICKER: TimelineEntryType.MEDIA,
            MessageType.AUDIO: TimelineEntryType.MEDIA,
            MessageType.VIDEO: TimelineEntryType.MEDIA,
            MessageType.LINK: TimelineEntryType.MESSAGE,
            MessageType.MULTI: TimelineEntryType.MESSAGE,
        }

        entry_type = entry_type_map.get(msg.message_type, TimelineEntryType.MESSAGE)

        notes_parts: list[str] = []
        if msg.is_deleted:
            notes_parts.append("Mensagem deletada")
        if msg.is_edited:
            notes_parts.append("Mensagem editada")
        if msg.ocr_extracted:
            notes_parts.append("Conteúdo extraído via OCR")
        if msg.media_reference:
            notes_parts.append(f"Mídia: {msg.media_reference}")

        return TimelineEntry(
            entry_type=entry_type,
            timestamp=msg.timestamp,
            sender=msg.sender,
            content=msg.content,
            source_file=None,
            line_in_source=msg.line_number,
            notes="; ".join(notes_parts),
            inconsistencies=[],
        )

    def _ocr_to_entries(self, ocr: OCRResult) -> list[TimelineEntry]:
        """Converte um resultado OCR em uma ou mais TimelineEntries.

        Tenta parsear timestamps detectados para criar entradas individuais.
        Se não houver timestamps parseáveis, cria uma entrada consolidada.

        Args:
            ocr: Resultado do processamento OCR.

        Returns:
            Lista de entradas derivadas do resultado OCR.
        """
        entries: list[TimelineEntry] = []

        if ocr.detected_timestamps:
            for i, ts_str in enumerate(ocr.detected_timestamps):
                parsed_ts = self._parse_timestamp(ts_str)
                if parsed_ts is None:
                    continue

                sender = ocr.detected_senders[i] if i < len(ocr.detected_senders) else None
                content = ocr.detected_messages[i] if i < len(ocr.detected_messages) else ocr.extracted_text

                entry = TimelineEntry(
                    entry_type=TimelineEntryType.MESSAGE,
                    timestamp=parsed_ts,
                    sender=sender,
                    content=content,
                    source_file=ocr.source_image,
                    position_in_image=f"ocr_segment_{i}",
                    notes=f"Extraído via OCR (confiança: {ocr.confidence:.2f})",
                    inconsistencies=[],
                )
                entries.append(entry)

        if not entries:
            ts = datetime.now(timezone.utc)
            entries.append(
                TimelineEntry(
                    entry_type=TimelineEntryType.ANOMALY,
                    timestamp=ts,
                    content=ocr.extracted_text[:500] if ocr.extracted_text else "(texto não extraído)",
                    source_file=ocr.source_image,
                    notes=(
                        f"OCR sem timestamps parseáveis. "
                        f"Confiança: {ocr.confidence:.2f}. "
                        f"Remetentes detectados: {', '.join(ocr.detected_senders) or 'nenhum'}"
                    ),
                    inconsistencies=[
                        "Timestamps OCR não puderam ser parseados"
                    ] if ocr.detected_timestamps else [],
                )
            )

        return entries

    def _parse_timestamp(self, ts_str: str) -> datetime | None:
        """Tenta parsear uma string de timestamp em datetime.

        Suporta formatos comuns do WhatsApp:
        - DD/MM/YYYY HH:MM
        - DD/MM/YY HH:MM
        - YYYY-MM-DD HH:MM:SS
        - DD/MM/YYYY, HH:MM

        Args:
            ts_str: String do timestamp detectado.

        Returns:
            datetime parseado ou None se nenhum formato for reconhecido.
        """
        formats = [
            "%d/%m/%Y %H:%M",
            "%d/%m/%y %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y, %H:%M",
            "%d/%m/%y, %H:%M",
            "%m/%d/%Y %I:%M %p",
            "%m/%d/%y %I:%M %p",
        ]

        cleaned = ts_str.strip()

        for fmt in formats:
            try:
                return datetime.strptime(cleaned, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        logger.warning("Não foi possível parsear timestamp: %s", ts_str)
        return None
