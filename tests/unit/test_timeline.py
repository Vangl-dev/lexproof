"""Testes unitários para o módulo de linha do tempo."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lexproof.models.message import MessageType, WhatsAppMessage
from lexproof.models.ocr_result import OCRResult
from lexproof.models.timeline import TimelineEntry, TimelineEntryType
from lexproof.timeline.timeline_builder import TimelineBuilder


@pytest.fixture
def builder() -> TimelineBuilder:
    return TimelineBuilder(gap_threshold_seconds=3600.0)


@pytest.fixture
def short_gap_builder() -> TimelineBuilder:
    return TimelineBuilder(gap_threshold_seconds=60.0)


@pytest.fixture
def sample_messages_for_timeline() -> list[WhatsAppMessage]:
    return [
        WhatsAppMessage(
            line_number=1,
            timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
            sender="João",
            content="Mensagem 1",
        ),
        WhatsAppMessage(
            line_number=2,
            timestamp=datetime(2024, 3, 15, 10, 5, tzinfo=timezone.utc),
            sender="Maria",
            content="Mensagem 2",
        ),
        WhatsAppMessage(
            line_number=3,
            timestamp=datetime(2024, 3, 15, 10, 10, tzinfo=timezone.utc),
            sender="João",
            content="Mensagem 3",
        ),
    ]


class TestBuildTimeline:
    def test_build_timeline(self, builder, sample_messages_for_timeline):
        entries = builder.build_timeline(sample_messages_for_timeline)
        assert len(entries) == 3
        assert all(isinstance(e, TimelineEntry) for e in entries)

    def test_build_timeline_sorted(self, builder, sample_messages_for_timeline):
        entries = builder.build_timeline(sample_messages_for_timeline)
        timestamps = [e.timestamp for e in entries]
        assert timestamps == sorted(timestamps)

    def test_build_timeline_preserves_data(self, builder, sample_messages_for_timeline):
        entries = builder.build_timeline(sample_messages_for_timeline)
        assert entries[0].sender == "João"
        assert entries[0].content == "Mensagem 1"
        assert entries[0].line_in_source == 1

    def test_build_timeline_empty_messages(self, builder):
        entries = builder.build_timeline([])
        assert entries == []

    def test_build_timeline_single_message(self, builder):
        msg = WhatsAppMessage(
            line_number=1,
            timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
            sender="João",
            content="Única mensagem",
        )
        entries = builder.build_timeline([msg])
        assert len(entries) == 1
        assert entries[0].content == "Única mensagem"


class TestSortTimeline:
    def test_sort_timeline(self, builder):
        msg1 = WhatsAppMessage(
            line_number=3,
            timestamp=datetime(2024, 3, 15, 10, 10, tzinfo=timezone.utc),
            sender="João",
            content="Terceira",
        )
        msg2 = WhatsAppMessage(
            line_number=1,
            timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
            sender="Maria",
            content="Primeira",
        )
        msg3 = WhatsAppMessage(
            line_number=2,
            timestamp=datetime(2024, 3, 15, 10, 5, tzinfo=timezone.utc),
            sender="João",
            content="Segunda",
        )
        entries = builder.build_timeline([msg1, msg2, msg3])
        timestamps = [e.timestamp for e in entries]
        assert timestamps[0] < timestamps[1] < timestamps[2]

    def test_sort_maintains_stability(self, builder):
        ts = datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc)
        msg1 = WhatsAppMessage(line_number=1, timestamp=ts, sender="A", content="First")
        msg2 = WhatsAppMessage(line_number=2, timestamp=ts, sender="B", content="Second")
        entries = builder.build_timeline([msg1, msg2])
        assert entries[0].sender == "A"
        assert entries[1].sender == "B"


class TestDetectDuplicates:
    def test_detect_duplicates(self, builder, tmp_path):
        ts = datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc)
        msg1 = WhatsAppMessage(line_number=1, timestamp=ts, sender="João", content="Olá")
        msg2 = WhatsAppMessage(
            line_number=2,
            timestamp=ts + timedelta(seconds=0.5),
            sender="João",
            content="Olá",
        )
        msg3 = WhatsAppMessage(
            line_number=3, timestamp=ts + timedelta(minutes=1), sender="Maria", content="Oi"
        )
        entries = builder.build_timeline([msg1, msg2, msg3])
        duplicate_entries = [
            e for e in entries if any("Duplicata" in i for i in e.inconsistencies)
        ]
        assert len(duplicate_entries) == 1

    def test_no_duplicates_different_content(self, builder):
        ts = datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc)
        msg1 = WhatsAppMessage(line_number=1, timestamp=ts, sender="João", content="Olá")
        msg2 = WhatsAppMessage(
            line_number=2,
            timestamp=ts + timedelta(seconds=0.5),
            sender="João",
            content="Oi",
        )
        entries = builder.build_timeline([msg1, msg2])
        duplicate_entries = [
            e for e in entries if any("Duplicata" in i for i in e.inconsistencies)
        ]
        assert len(duplicate_entries) == 0

    def test_no_duplicates_different_senders(self, builder):
        ts = datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc)
        msg1 = WhatsAppMessage(line_number=1, timestamp=ts, sender="João", content="Olá")
        msg2 = WhatsAppMessage(
            line_number=2,
            timestamp=ts + timedelta(seconds=0.5),
            sender="Maria",
            content="Olá",
        )
        entries = builder.build_timeline([msg1, msg2])
        duplicate_entries = [
            e for e in entries if any("Duplicata" in i for i in e.inconsistencies)
        ]
        assert len(duplicate_entries) == 0


class TestDetectGaps:
    def test_detect_gaps(self, short_gap_builder):
        ts1 = datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc)
        ts2 = datetime(2024, 3, 15, 12, 0, tzinfo=timezone.utc)
        msg1 = WhatsAppMessage(line_number=1, timestamp=ts1, sender="João", content="Antes")
        msg2 = WhatsAppMessage(line_number=2, timestamp=ts2, sender="Maria", content="Depois")
        entries = short_gap_builder.build_timeline([msg1, msg2])

        gap_entries = [
            e for e in entries if e.entry_type == TimelineEntryType.TIMESTAMP_GAP
        ]
        assert len(gap_entries) == 1

    def test_no_gap_small_difference(self, builder):
        ts1 = datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc)
        ts2 = datetime(2024, 3, 15, 10, 30, tzinfo=timezone.utc)
        msg1 = WhatsAppMessage(line_number=1, timestamp=ts1, sender="João", content="Primeira")
        msg2 = WhatsAppMessage(line_number=2, timestamp=ts2, sender="Maria", content="Segunda")
        entries = builder.build_timeline([msg1, msg2])

        gap_entries = [
            e for e in entries if e.entry_type == TimelineEntryType.TIMESTAMP_GAP
        ]
        assert len(gap_entries) == 0

    def test_gap_marks_inconsistencies(self, short_gap_builder):
        ts1 = datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc)
        ts2 = datetime(2024, 3, 15, 15, 0, tzinfo=timezone.utc)
        msg1 = WhatsAppMessage(line_number=1, timestamp=ts1, sender="João", content="A")
        msg2 = WhatsAppMessage(line_number=2, timestamp=ts2, sender="Maria", content="B")
        entries = short_gap_builder.build_timeline([msg1, msg2])

        normal_entries = [
            e
            for e in entries
            if e.entry_type in (TimelineEntryType.MESSAGE,)
            and any("Lacuna" in i for i in e.inconsistencies)
        ]
        assert len(normal_entries) >= 1

    def test_detect_gaps_returns_count(self, short_gap_builder):
        ts1 = datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc)
        ts2 = datetime(2024, 3, 15, 12, 0, tzinfo=timezone.utc)
        ts3 = datetime(2024, 3, 15, 14, 0, tzinfo=timezone.utc)
        msg1 = WhatsAppMessage(line_number=1, timestamp=ts1, sender="A", content="1")
        msg2 = WhatsAppMessage(line_number=2, timestamp=ts2, sender="B", content="2")
        msg3 = WhatsAppMessage(line_number=3, timestamp=ts3, sender="C", content="3")
        builder = TimelineBuilder(gap_threshold_seconds=60.0)
        builder.build_timeline([msg1, msg2, msg3])
        gap_count = builder.detect_gaps()
        assert gap_count >= 2


class TestTimelineWithOCR:
    def test_timeline_with_ocr(self, builder, sample_messages_for_timeline):
        ocr = OCRResult(
            source_image="screenshot.png",
            extracted_text="15/03/2024 11:00, Pedro: Texto OCR",
            confidence=0.9,
            detected_timestamps=["15/03/2024 11:00"],
            detected_senders=["Pedro"],
            detected_messages=["Texto OCR"],
            engine_used="tesseract",
            processing_time=1.0,
        )
        entries = builder.build_timeline(
            sample_messages_for_timeline, ocr_results=[ocr]
        )
        assert len(entries) > 3

    def test_ocr_entries_sorted_with_messages(self, builder):
        msg = WhatsAppMessage(
            line_number=1,
            timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
            sender="João",
            content="Mensagem TXT",
        )
        ocr = OCRResult(
            source_image="img.png",
            extracted_text="15/03/2024 12:00, Pedro: OCR",
            confidence=0.8,
            detected_timestamps=["15/03/2024 12:00"],
            detected_senders=["Pedro"],
            detected_messages=["OCR"],
            engine_used="tesseract",
        )
        entries = builder.build_timeline([msg], ocr_results=[ocr])
        assert entries[0].sender == "João"
        assert entries[1].sender == "Pedro" or entries[-1].sender == "Pedro"

    def test_ocr_without_timestamps(self, builder):
        msg = WhatsAppMessage(
            line_number=1,
            timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
            sender="João",
            content="Mensagem",
        )
        ocr = OCRResult(
            source_image="img.png",
            extracted_text="Texto sem timestamp",
            confidence=0.7,
            detected_timestamps=[],
            detected_senders=[],
            detected_messages=[],
        )
        entries = builder.build_timeline([msg], ocr_results=[ocr])
        anomaly_entries = [
            e for e in entries if e.entry_type == TimelineEntryType.ANOMALY
        ]
        assert len(anomaly_entries) == 1


class TestGetInconsistencies:
    def test_get_inconsistencies(self, short_gap_builder):
        ts1 = datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc)
        ts2 = datetime(2024, 3, 15, 12, 0, tzinfo=timezone.utc)
        msg1 = WhatsAppMessage(line_number=1, timestamp=ts1, sender="A", content="1")
        msg2 = WhatsAppMessage(line_number=2, timestamp=ts2, sender="B", content="2")
        short_gap_builder.build_timeline([msg1, msg2])
        inconsistencies = short_gap_builder.get_inconsistencies()
        assert len(inconsistencies) > 0

    def test_get_inconsistencies_empty(self, builder, sample_messages_for_timeline):
        builder.build_timeline(sample_messages_for_timeline)
        inconsistencies = builder.get_inconsistencies()
        assert inconsistencies == []


class TestMessageTypeMapping:
    def test_deleted_message_maps_to_deletion(self, builder):
        msg = WhatsAppMessage(
            line_number=1,
            timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
            sender="João",
            content="<Esta mensagem foi apagada>",
            message_type=MessageType.DELETED,
            is_deleted=True,
        )
        entries = builder.build_timeline([msg])
        assert entries[0].entry_type == TimelineEntryType.DELETION

    def test_system_message_maps_to_system_event(self, builder):
        msg = WhatsAppMessage(
            line_number=1,
            timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
            sender="Sistema",
            content="Você foi adicionado",
            message_type=MessageType.SYSTEM,
        )
        entries = builder.build_timeline([msg])
        assert entries[0].entry_type == TimelineEntryType.SYSTEM_EVENT

    def test_media_message_maps_to_media(self, builder):
        msg = WhatsAppMessage(
            line_number=1,
            timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
            sender="João",
            content="<Mídia ocultada>",
            message_type=MessageType.MEDIA,
            media_reference="image",
        )
        entries = builder.build_timeline([msg])
        assert entries[0].entry_type == TimelineEntryType.MEDIA

    def test_edited_message_maps_to_edit(self, builder):
        msg = WhatsAppMessage(
            line_number=1,
            timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
            sender="João",
            content="<Esta mensagem foi editada>",
            message_type=MessageType.EDITED,
            is_edited=True,
        )
        entries = builder.build_timeline([msg])
        assert entries[0].entry_type == TimelineEntryType.EDIT
