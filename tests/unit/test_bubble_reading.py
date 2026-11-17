"""Leitura dos prints por baloes e explicacoes das divergencias.

Os prints aqui sao desenhados pelo proprio teste (cores do WhatsApp, textos e
nomes inventados). Os casos reproduzem erros reais de leitura: horario pequeno
ilegivel no tema escuro, horario escrito no texto, previa de link, legenda de
midia e nome do contato cortado no topo.
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from lexproof.parsers.whatsapp_parser import WhatsAppParser
from lexproof.triangulation.bubble_detector import detect_bubbles
from lexproof.triangulation.matcher import (
    HINT_JOINED,
    HINT_OTHER_DEVICE,
    HINT_TIME_DIGIT,
    HINT_TIME_IN_TEXT,
    CheckStatus,
    ScreenshotMatcher,
    is_ocr_noise,
    names_match,
    split_urls,
)
from lexproof.triangulation.screenshot_reader import (
    ScreenBubble,
    ScreenshotReader,
    ScreenshotReading,
    _time_consensus,
    _trailing_time_index,
)
from lexproof.triangulation.stitcher import ScreenshotStitcher, bridge_gaps_with_export

TZ = ZoneInfo("America/Sao_Paulo")

EXPORT = """\
02/05/2026 09:41 - Rodrigo Albuquerque Neves: Bom dia, tudo certo?
02/05/2026 09:41 - Rodrigo Albuquerque Neves: Que horas te encontro na feira?
02/05/2026 09:45 - Helena: Podemos falar às 15:00 hoje
02/05/2026 09:50 - Rodrigo Albuquerque Neves: Fechado, chego em 1h com as caixas
02/05/2026 10:02 - Helena: <Mídia oculta>
02/05/2026 10:05 - Rodrigo Albuquerque Neves: <Mídia oculta>
02/05/2026 10:06 - Helena: Valeu, até sábado
05/05/2026 08:10 - Helena: Segue o link https://exemplo.com.br/sala/abc123def456?entrar=sim Clique para entrar.
05/05/2026 08:12 - Rodrigo Albuquerque Neves: Valeu, até sábado
"""


@pytest.fixture
def export_file(tmp_path: Path) -> Path:
    path = tmp_path / "Conversa do WhatsApp com Rodrigo Albuquerque Neves.txt"
    path.write_text(EXPORT, encoding="utf-8")
    return path


@pytest.fixture
def messages(export_file: Path):
    return WhatsAppParser().parse(export_file)


def _reading(bubbles, name="Screenshot_20260505090000.jpg", contact="Rodrigo Albuquerq...", method="baloes"):
    return ScreenshotReading(
        path=Path(name), contact=contact, bubbles=bubbles, method=method,
        captured_at=datetime(2026, 5, 5, 9, 0, tzinfo=TZ),
    )


def _b(text, time, day=date(2026, 5, 2), kind="text", **kw):
    return ScreenBubble(text=text, time=time, top=0, kind=kind, date=day, **kw)


# ----------------------------------------------------------------------
# Prints desenhados

DARK = {
    "bg": (11, 20, 26), "doodle": (28, 32, 36), "header": (31, 44, 52),
    "in": (31, 39, 42), "out": (18, 76, 54), "pill": (24, 34, 40), "card": (12, 50, 36),
    "text": (233, 237, 239), "meta": (150, 160, 165),
}
LIGHT = {
    "bg": (239, 234, 226), "doodle": (222, 214, 204), "header": (255, 255, 255),
    "in": (255, 255, 255), "out": (217, 253, 211), "pill": (255, 250, 235), "card": (196, 236, 190),
    "text": (17, 27, 33), "meta": (102, 119, 129),
}
W, H = 752, 1600
FOOTER = 1420


def _font(size: int):
    for name in ("DejaVuSans.ttf", "LiberationSans-Regular.ttf", "NotoSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    pytest.skip("sem fonte TrueType para desenhar o print")


def _draw_print(path: Path, theme: dict, bubbles: list[dict], date_label: str = "") -> Path:
    """Tela de conversa com papel de parede, cabecalho, baloes e barra de digitacao."""
    img = Image.new("RGB", (W, H), theme["bg"])
    d = ImageDraw.Draw(img)
    for y in range(110, FOOTER, 45):  # desenhos do papel de parede, encostando nas bordas
        d.line([(2, y), (40, y + 25)], fill=theme["doodle"], width=3)
        d.arc([W - 70, y, W - 20, y + 40], 0, 270, fill=theme["doodle"], width=3)
    d.rectangle([0, 0, W, 95], fill=theme["header"])
    d.text((110, 25), "Rodrigo Albuquerq...", font=_font(40), fill=theme["text"])
    body, small = _font(36), _font(24)
    y = 110
    if date_label:
        d.rounded_rectangle([230, y, 520, y + 55], radius=12, fill=theme["pill"])
        d.text((255, y + 10), date_label, font=small, fill=theme["meta"])
        y += 80
    for spec in bubbles:
        lines = spec["lines"]
        height = 30 + 48 * len(lines) + (spec.get("card", 0)) + (10 if spec.get("time") else 0)
        width = spec.get("width", 520)
        left = 30 if spec["side"] == "left" else W - 30 - width
        color = theme["in"] if spec["side"] == "left" else theme["out"]
        d.rounded_rectangle([left, y, left + width, y + height], radius=16, fill=color)
        ty = y + 15
        if spec.get("card"):
            d.rounded_rectangle([left + 10, y + 10, left + width - 10, y + spec["card"]], radius=10,
                                fill=theme["card"])
            d.text((left + 25, y + 25), "Pré-visualização", font=small, fill=theme["text"])
            ty = y + spec["card"] + 10
        for i, line in enumerate(lines):
            d.text((left + 18, ty + 48 * i), line, font=body, fill=theme["text"])
        if spec.get("time"):
            tx = left + width - (130 if spec["side"] == "right" else 90)
            d.text((tx, y + height - 38), spec["time"], font=small, fill=theme["meta"])
            if spec["side"] == "right":
                d.text((tx + 72, y + height - 38), "✓✓", font=small, fill=(83, 189, 235))
        y += height + 12
    # Barra de digitacao por cima da conversa: corta o que passar dela
    d.rectangle([0, FOOTER, W, H], fill=theme["bg"])
    d.rounded_rectangle([15, FOOTER + 10, 640, FOOTER + 90], radius=40, fill=theme["in"])
    d.text((90, FOOTER + 30), "Mensagem", font=body, fill=theme["meta"])
    img.save(path)
    return path


def _detect(path: Path):
    rgb = np.asarray(Image.open(path).convert("RGB"))
    return [b for b in detect_bubbles(rgb, 96, FOOTER) if b.side != "center"]


class TestBubbleDetector:
    @pytest.mark.parametrize("theme", [DARK, LIGHT], ids=["escuro", "claro"])
    def test_finds_each_bubble_and_side(self, tmp_path, theme):
        path = _draw_print(tmp_path / "p.png", theme, [
            {"side": "left", "lines": ["Bom dia, tudo certo?"], "time": "09:41", "width": 420},
            {"side": "left", "lines": ["Que horas te encontro na feira?"], "time": "09:41", "width": 480},
            {"side": "right", "lines": ["Podemos falar às 15:00 hoje"], "time": "09:45", "width": 560},
        ], date_label="2 de maio de 2026")
        bubbles = _detect(path)
        # Dois baloes recebidos seguidos nao se fundem num so
        assert [b.side for b in bubbles] == ["left", "left", "right"]
        assert not any(b.cut_top or b.cut_bottom for b in bubbles)

    def test_link_preview_is_an_inner_card(self, tmp_path):
        path = _draw_print(tmp_path / "p.png", DARK, [
            {"side": "right", "lines": ["Segue o link", "https://exemplo.com.br"], "time": "08:10",
             "width": 600, "card": 140},
        ])
        (bubble,) = _detect(path)
        assert len(bubble.inner) == 1
        left, top, right, bottom = bubble.inner[0]
        assert bottom - top >= 100 and right - left > 400

    def test_bubble_cut_by_typing_bar(self, tmp_path):
        many = ["linha de texto comprida"] * 30
        path = _draw_print(tmp_path / "p.png", DARK, [
            {"side": "left", "lines": ["Bom dia"], "time": "09:41", "width": 300},
            {"side": "right", "lines": many, "time": "09:45", "width": 600},
        ])
        first, second = _detect(path)
        assert not first.cut_bottom
        assert second.cut_bottom


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract nao instalado")
class TestReaderOnDrawnPrint:
    def test_time_written_in_text_is_not_the_bubble_time(self, tmp_path):
        langs = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout
        if "por" not in langs.split():
            pytest.skip("Tesseract sem portugues")
        path = _draw_print(tmp_path / "Screenshot_20260505090000.png", DARK, [
            {"side": "left", "lines": ["Bom dia, tudo certo?"], "time": "09:41", "width": 420},
            {"side": "right", "lines": ["Podemos falar às 15:00 hoje"], "time": "09:45", "width": 560},
        ], date_label="2 de maio de 2026")
        reading = ScreenshotReader().read(path)
        assert reading.method == "baloes"
        assert len(reading.bubbles) == 2
        times = [b.time for b in reading.bubbles]
        # Ler errado e pior que nao ler: horario ilegivel e aceito, trocado nao.
        assert times[0] in ("09:41", None) and times[1] in ("09:45", None)
        assert "15:00" in reading.bubbles[1].text
        assert [b.side for b in reading.bubbles] == ["left", "right"]


# ----------------------------------------------------------------------
# Horario do balao


class TestTimeReading:
    def test_two_agreeing_reads_win(self):
        assert _time_consensus(["n:34", "1:34", "11:34", "11:34"], final=False) == ("11:34", "")

    def test_lost_digit_is_not_padded_with_zero(self):
        # "1:34" e "11:34" com um digito perdido, nunca "01:34"
        time, partial = _time_consensus(["1:34", ":34", "1:34"], final=True)
        assert time is None and partial == "1:34"

    def test_read_contradicting_partial_is_rejected(self):
        # "1237" (sem dois-pontos) contradiz "1:37"
        assert _time_consensus(["1237", "1:37", "1:37"], final=True)[0] is None

    def test_tick_read_as_digit_is_dropped(self):
        assert _time_consensus(["09:564", "09:56"], final=False)[0] == "09:56"

    def test_trailing_ticks_skipped_and_time_must_be_in_corner(self):
        def w(text, left):
            return {"text": text, "left": left, "width": 60, "top": 0, "height": 20}

        # "pode vir agora 14:55 4" -> o "4" e o tique
        assert _trailing_time_index([w("agora", 300), w("14:55", 470), w("4", 560)], 600, 752) == 1
        # horario escrito no meio do texto, longe do canto, nao conta
        assert _trailing_time_index([w("às", 100), w("15:00", 160), w("hoje", 260)], 600, 752) is None


# ----------------------------------------------------------------------
# Conferencia


class TestMatcherCases:
    def test_lookalike_letters_are_ocr_noise(self):
        assert is_ocr_noise([("lh", "1h")])
        assert is_ocr_noise([("2O26", "2026")])
        assert not is_ocr_noise([("5h", "1h")])

    def test_truncated_contact_with_one_wrong_letter_matches(self):
        assert names_match("Rodrigo Albuquerg...", "Rodrigo Albuquerque Neves")
        assert not names_match("Rodrigo Mendes", "Rodrigo Albuquerque Neves")
        assert not names_match("Xodrigo Albuquerq...", "Rodrigo Albuquerque Neves")

    def test_caption_of_media_is_not_a_divergence(self, messages, export_file):
        # Legenda enviada com uma foto: a exportacao sem midia so tem "<Midia oculta>"
        reading = _reading([_b("segue a foto do documento", "10:02", side="right")])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.LEGENDA_DE_MIDIA
        assert check.checks[0].status.ok and not check.checks[0].status.counted
        assert check.total == 0

    def test_audio_bubble_matches_media_by_time(self, messages, export_file):
        reading = _reading([_b("", "10:05", kind="audio", side="left")])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.CONFERE

    def test_cut_media_without_time_is_not_checked(self, messages, export_file):
        reading = _reading([_b("", None, day=date(2026, 5, 5), kind="media", cut=True)])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.NAO_CONFERIDO

    def test_partial_time_compatible_is_noted(self, messages, export_file):
        reading = _reading([_b("Fechado, chego em 1h com as caixas", None, time_partial="9:50")])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.CONFERE_SEM_HORARIO
        assert any("compatível com 09:50" in n for n in check.checks[0].notes)

    def test_link_read_with_small_ocr_errors_confers(self, messages, export_file):
        text = ("Segue o link https://exemplo.com.br sala/abc123deƒ456 ?entrar=sim v Clique para entrar.")
        reading = _reading([_b(text, "08:10", day=date(2026, 5, 5))])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.CONFERE
        assert any("Link lido com pequenas diferenças" in n for n in check.checks[0].notes)

    def test_changed_link_is_divergent(self, messages, export_file):
        text = "Segue o link https://golpe.example.net/pagar?valor=9999 Clique para entrar."
        reading = _reading([_b(text, "08:10", day=date(2026, 5, 5))])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.TEXTO_DIVERGENTE

    def test_split_urls_joins_broken_link(self):
        text, urls = split_urls("veja https://ex.com l/sala/19%3a N2JMYj %40x?y=1 Clique aqui")
        assert text == "veja link Clique aqui"
        assert urls == ["https://ex.coml/sala/19%3aN2JMYj%40x?y=1"]


class TestDivergenceHints:
    def test_joined_bubbles(self, messages, export_file):
        reading = _reading([_b("Bom dia, tudo certo? n13 Que horas te encontro na feira?", "09:41")])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.NAO_ENCONTRADA
        assert HINT_JOINED in check.checks[0].hints
        assert HINT_OTHER_DEVICE in check.checks[0].hints

    def test_time_one_digit_off_and_time_in_text(self, messages, export_file):
        reading = _reading([_b("Podemos falar às 15:00 hoje", "15:00")])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.HORARIO_DIVERGENTE
        assert HINT_TIME_IN_TEXT in check.checks[0].hints

        reading = _reading([_b("Podemos falar às 15:00 hoje", "09:46")])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert HINT_TIME_DIGIT in check.checks[0].hints

    def test_confirmed_bubbles_have_no_hints(self, messages, export_file):
        reading = _reading([_b("Bom dia, tudo certo?", "09:41")])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.checks[0].status == CheckStatus.CONFERE
        assert check.checks[0].hints == []

    def test_omission_next_to_unrecognized_bubble_is_explained(self, messages, export_file):
        reading = _reading([
            _b("Bom dia, tudo certo?", "09:41"),
            _b("xx yy zz", "09:43"),
            _b("Fechado, chego em 1h com as caixas", "09:50"),
        ])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        assert check.hidden_messages
        assert any("não foram reconhecidos" in h for h in check.hidden_hints)


class TestStitchWithShortRepeatedText:
    def test_untimed_short_phrase_does_not_borrow_date(self):
        # "Valeu, até sábado" de outro dia nao pode dar a data ao balao sem horario
        a = _reading([_b("Valeu, até sábado", "08:12", day=date(2026, 5, 5))], name="a.jpg")
        b = _reading([_b("Valeu, até sábado", None, day=None)], name="b.jpg")
        ScreenshotStitcher().stitch([a, b])
        assert b.bubbles[0].date is None

    def test_gap_bridged_by_export_lines(self, messages, export_file):
        a = _reading([_b("Bom dia, tudo certo?", "09:41"), _b("Que horas te encontro", None, cut=True)],
                     name="a.jpg")
        b = _reading([_b("encontro na feira?", None, day=None, cut=True),
                      _b("Podemos falar às 15:00 hoje", "09:45")], name="b.jpg")
        result = ScreenshotStitcher().stitch([a, b])
        assert len(result.gaps) == 1  # sem a exportacao, parece faltar um trecho
        matcher = ScreenshotMatcher(messages, export_file)
        bridge_gaps_with_export(result, [matcher.check(a), matcher.check(b)])
        assert result.gaps == []


class TestReportDisclaimer:
    def test_divergence_gets_asterisk_and_explanation(self, tmp_path, messages, export_file):
        from PyPDF2 import PdfReader

        from lexproof.models.quality_grade import QualityGrade
        from lexproof.reports.pdf_report import PDFReportGenerator
        from lexproof.reports.report_data import build_report_data

        reading = _reading([_b("Bom dia, tudo certo? n13 Que horas te encontro na feira?", "09:41")])
        check = ScreenshotMatcher(messages, export_file).check(reading)
        data = build_report_data(
            evidences=[], messages=messages, ocr_results=[], hash_results=[], timeline=[],
            correlations=[], verification_results=[], quality_grade=QualityGrade.C if hasattr(
                QualityGrade, "C") else "C",
            session_id="LEX-TESTE", screenshot_checks=[check],
        )
        out = tmp_path / "relatorio.pdf"
        PDFReportGenerator().generate(data, out)
        text = " ".join(page.extract_text() or "" for page in PdfReader(str(out)).pages)
        text = " ".join(text.split())
        assert "Antes de concluir" in text
        assert "O que pode ter ocorrido" in text
        assert "NÃO ENCONTRADA *" in text
        assert "lidos como um só" in text


class TestDocumentBubble:
    def test_file_name_marks_document_but_word_pdf_in_text_does_not(self):
        from lexproof.triangulation.screenshot_reader import _DOCUMENT_RE

        assert _DOCUMENT_RE.search("Contrato de locação (1).pdf")
        assert _DOCUMENT_RE.search("12 páginas")
        assert not _DOCUMENT_RE.search("me manda o pdf do contrato")
