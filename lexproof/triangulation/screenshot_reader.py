"""Leitura estruturada de prints de conversa do WhatsApp.

Extrai do print o nome do contato, os separadores de data ("16 de marco de
2026", "Ontem", "Segunda-feira") e cada balao com seu texto e horario. Os
horarios sao relidos em recorte ampliado, porque sao pequenos demais para o
OCR da pagina inteira.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from lexproof.core.constants import DEFAULT_TIMEZONE

logger = logging.getLogger(__name__)

_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
_WEEKDAYS = {
    "segunda": 0, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "domingo": 6,
}
_FULL_DATE_RE = re.compile(r"^(\d{1,2}) de ([a-z]+)(?: de (\d{4}))?$")
_SLASH_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$")
_WEEKDAY_RE = re.compile(r"^(segunda|terca|quarta|quinta|sexta)(?:-?feira)?$|^(sabado|domingo)$")
_TIME_LIKE_RE = re.compile(r"^[\dOoSlI|:;.,\->]{3,8}$")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_CALL_RE = re.compile(
    r"(liga[cç][aã]o|chamada) (de voz|de v[ií]deo|perdida)|voice call|video call|missed",
    re.IGNORECASE,
)
_DOCUMENT_RE = re.compile(
    r"\b\d+\s+p[aá]ginas?\b|\b\d+(?:[.,]\d+)?\s?[kKmM]B\b|\bPDF\b|\bDOCX?\b"
    r"|\.(?i:pdf|docx?|xlsx?|pptx?|odt|zip|rar)\b"
)
_FORWARDED_RE = re.compile(r"^\W*\w{0,2}\W*(encaminhada|forwarded)\b", re.IGNORECASE)
_AUDIO_RE = re.compile(r"\b(transcrever|transcribe)\b|^\W*\d{1,2}:\d{2}\W*$", re.IGNORECASE)
_FOOTER_RE = re.compile(r"\b(mensagem|message)\b", re.IGNORECASE)
_READ_MORE_RE = re.compile(r"\s*(?:\.{2,}|…)?\s*(?:Ler mais|Read more)\s*$", re.IGNORECASE)
# Palavras com confianca do Tesseract abaixo disto sao lixo de OCR (linha cortada
# na borda, miniatura de documento); o texto legivel fica acima de 80.
_MIN_WORD_CONFIDENCE = 30

_CAPTURE_NAME_RE = re.compile(
    r"(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})[-_. ]?(?:at )?(\d{2})[-_.:h]?(\d{2})[-_.:m]?(\d{2})"
)

# Margem acrescentada ao recorte de cada balao antes do OCR
_BOX_BORDER = 16

# Balao recebido comeca rente a borda esquerda; o enviado, mais para dentro.
_LEFT_SIDE_MAX = 0.11

# Faixas de cabecalho (nome do contato) e rodape (campo "Mensagem")
_HEADER_FRACTION = 0.06
# Com barra de status (relogio) visivel, a barra do contato fica mais abaixo.
_HEADER_FRACTION_WITH_STATUS = 0.09
_FOOTER_FRACTION = 0.90


@dataclass
class ScreenBubble:
    """Um balao de mensagem visivel no print."""

    text: str
    time: Optional[str]
    top: int
    kind: str = "text"  # text, call, document, audio ou media
    date: Optional[date] = None
    date_label: Optional[str] = None
    # Mensagem longa mostrada pela metade ("... Ler mais")
    truncated: bool = False
    # "left": recebida (contato); "right": enviada (dono do celular que fez o print)
    side: Optional[str] = None
    # Balao cortado pela borda de cima ou de baixo do print
    cut: bool = False
    forwarded: bool = False
    # Texto de cartao dentro do balao (previa de link, mensagem citada,
    # nome do documento). Nao faz parte da mensagem na exportacao.
    card_text: str = ""
    # Horario lido so em parte ("1:34": o primeiro digito se perdeu)
    time_partial: str = ""


@dataclass
class ScreenshotReading:
    """Conteudo estruturado de um print."""

    path: Path
    contact: str = ""
    captured_at: Optional[datetime] = None
    captured_at_source: str = ""
    dark_mode: bool = False
    size: Optional[tuple[int, int]] = None
    status_clock: Optional[str] = None
    # Data informada pelo usuario para resolver "Ontem" e dias da semana quando
    # o arquivo nao traz a data do print
    reference_date: Optional[date] = None
    bubbles: list[ScreenBubble] = field(default_factory=list)
    date_labels: list[str] = field(default_factory=list)
    error: Optional[str] = None
    # "baloes": baloes recortados pela cor; "linhas": deduzidos do texto
    # (papel de parede com foto ou layout nao reconhecido; menos confiavel)
    method: str = ""

    @property
    def first_separator_date(self) -> Optional[date]:
        for b in self.bubbles:
            if b.date is not None:
                return b.date
        return None


def _fold(text: str) -> str:
    """Minusculas, sem acentos e com espacos normalizados."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text.lower()).strip()


def capture_time_from_file(path: Path, tz: ZoneInfo) -> tuple[Optional[datetime], str]:
    """Horario em que o print foi tirado: nome do arquivo ou EXIF."""
    m = _CAPTURE_NAME_RE.search(path.name)
    if m:
        try:
            y, mo, d, hh, mi, ss = (int(g) for g in m.groups())
            return datetime(y, mo, d, hh, mi, ss, tzinfo=tz), "nome do arquivo"
        except ValueError:
            pass
    try:
        from PIL import Image

        with Image.open(path) as img:
            exif = img.getexif()
            raw = exif.get_ifd(0x8769).get(0x9003) or exif.get(0x0132)
        if raw:
            return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S").replace(tzinfo=tz), "EXIF"
    except Exception:
        pass
    return None, ""


def resolve_date_label(label: str, captured: Optional[date]) -> Optional[date]:
    """Converte um separador de data do WhatsApp em data.

    Rotulos relativos ("Hoje", "Ontem", dia da semana) e datas sem ano
    dependem da data do print.
    """
    folded = _fold(label)
    m = _FULL_DATE_RE.match(folded)
    if m and m.group(2) in _MONTHS:
        day, month = int(m.group(1)), _MONTHS[m.group(2)]
        if m.group(3):
            year = int(m.group(3))
        elif captured is not None:
            year = captured.year
            if (month, day) > (captured.month, captured.day):
                year -= 1
        else:
            return None
        try:
            return date(year, month, day)
        except ValueError:
            return None
    m = _SLASH_DATE_RE.match(folded)
    if m:
        year = int(m.group(3))
        year += 2000 if year < 100 else 0
        try:
            return date(year, int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    if captured is None:
        return None
    if folded == "hoje":
        return captured
    if folded == "ontem":
        return captured - timedelta(days=1)
    m = _WEEKDAY_RE.match(folded)
    if m:
        target = _WEEKDAYS[m.group(1) or m.group(2)]
        delta = (captured.weekday() - target) % 7 or 7
        return captured - timedelta(days=delta)
    return None


def is_date_label(text: str) -> bool:
    folded = _fold(text)
    if folded in ("hoje", "ontem"):
        return True
    m = _FULL_DATE_RE.match(folded)
    if m and m.group(2) in _MONTHS:
        return True
    return bool(_SLASH_DATE_RE.match(folded) or _WEEKDAY_RE.match(folded))


class ScreenshotReader:
    """Le prints de conversa com Tesseract."""

    def __init__(self, timezone_name: str = DEFAULT_TIMEZONE, lang: str = "por") -> None:
        self._tz = ZoneInfo(timezone_name)
        self._lang = lang

    def read(self, path: Path, reference_date: Optional[date] = None) -> ScreenshotReading:
        path = Path(path)
        reading = ScreenshotReading(path=path)
        reading.captured_at, reading.captured_at_source = capture_time_from_file(path, self._tz)
        if reading.captured_at is None:
            reading.reference_date = reference_date
        try:
            self._read_into(reading)
        except Exception as exc:
            logger.warning("Falha ao ler print %s: %s", path.name, exc)
            reading.error = str(exc)
        return reading

    # ------------------------------------------------------------------

    def _read_into(self, reading: ScreenshotReading) -> None:
        import numpy as np
        import pytesseract
        from PIL import Image, ImageOps, ImageStat
        from pytesseract import Output

        from lexproof.triangulation.bubble_detector import detect_bubbles

        with Image.open(reading.path) as img:
            rgb = np.asarray(img.convert("RGB"))
            gray = img.convert("L")
            reading.size = img.size
        reading.dark_mode = ImageStat.Stat(gray).mean[0] < 110
        page = ImageOps.invert(gray) if reading.dark_mode else gray
        height = page.height

        data = pytesseract.image_to_data(
            page, lang=self._lang, config="--psm 4", output_type=Output.DICT
        )
        lines = _group_lines(data)
        header_limit = self._read_header(reading, lines, height)
        footer_limit = height * _FOOTER_FRACTION
        for line in lines:
            if line["top"] > height * 0.75 and _FOOTER_RE.search(" ".join(w["text"] for w in line["words"])):
                footer_limit = min(footer_limit, line["top"] - 4)
                break
        body = [ln for ln in lines if header_limit <= ln["top"] <= footer_limit]

        captured_date = reading.captured_at.date() if reading.captured_at else reading.reference_date
        try:
            boxes = detect_bubbles(rgb, int(header_limit), int(footer_limit))
        except Exception as exc:  # pragma: no cover - layout inesperado
            logger.debug("Deteccao de baloes falhou em %s: %s", reading.path.name, exc)
            boxes = []
        if any(b.side != "center" for b in boxes):
            reading.method = "baloes"
            self._read_boxes(reading, gray, boxes, body, captured_date)
        else:
            reading.method = "linhas"
            self._read_lines(reading, page, body, captured_date)

    def _read_header(self, reading: ScreenshotReading, lines: list[dict[str, Any]], height: int) -> float:
        """Nome do contato e relogio da barra de status; devolve onde o corpo comeca."""
        header_limit = height * _HEADER_FRACTION
        for line in lines:
            if line["top"] >= header_limit:
                break
            first = _normalize_time(line["words"][0]["text"])
            if reading.status_clock is None and not reading.contact and _TIME_RE.match(first):
                reading.status_clock = first
                header_limit = height * _HEADER_FRACTION_WITH_STATUS
            elif not reading.contact:
                reading.contact = _clean_contact(line["words"])
        return header_limit

    # ------------------------------------------------------------------
    # Leitura por baloes (recortados pela cor)

    def _read_boxes(
        self,
        reading: ScreenshotReading,
        gray: Any,
        boxes: list[Any],
        body: list[dict[str, Any]],
        captured_date: Optional[date],
    ) -> None:
        from PIL import ImageOps

        inverted = ImageOps.invert(gray)
        messages = [b for b in boxes if b.side != "center"]

        def inside_bubble(line: dict[str, Any]) -> bool:
            mid = line["top"] + max(w["height"] for w in line["words"]) // 2
            return any(b.top <= mid <= b.bottom for b in messages)

        # Separadores de data ficam fora dos baloes (pilula centralizada).
        events: list[tuple[int, str, Any]] = []
        for line in body:
            if inside_bubble(line):
                continue
            text = " ".join(w["text"] for w in line["words"]).strip()
            if is_date_label(text):
                events.append((line["top"], "date", text))
        for b in messages:
            events.append((b.top, "bubble", b))
        events.sort(key=lambda e: e[0])

        current_date: Optional[date] = None
        current_label: Optional[str] = None
        for _, kind, item in events:
            if kind == "date":
                current_label = item
                current_date = resolve_date_label(item, captured_date)
                reading.date_labels.append(item)
                continue
            bubble = self._read_box(inverted if item.dark else gray, item)
            if bubble is None:
                continue
            bubble.date, bubble.date_label = current_date, current_label
            reading.bubbles.append(bubble)

    def _read_box(self, page: Any, box: Any) -> Optional[ScreenBubble]:
        """Le um balao: texto, horario (canto inferior direito) e tipo."""
        import pytesseract
        from pytesseract import Output

        from PIL import ImageOps

        crop = page.crop((box.left, box.top, box.right, box.bottom))
        # O Tesseract le mal texto encostado na borda da imagem: margem com a
        # cor do proprio balao (balao curto, como "Ok", saia como lixo).
        fill = max(range(256), key=crop.histogram().__getitem__)
        padded = ImageOps.expand(crop, border=_BOX_BORDER, fill=fill)
        data = pytesseract.image_to_data(
            padded, lang=self._lang, config="--psm 6", output_type=Output.DICT
        )
        for key in ("left", "top"):
            data[key] = [v - _BOX_BORDER for v in data[key]]
        lines = [ln for ln in (_clean_body_line(ln) for ln in _group_lines(data)) if ln is not None]
        if box.cut_top:
            # Linha cortada pela borda de cima: so metade das letras, lixo de OCR.
            lines = [ln for ln in lines if ln["top"] > 4]

        cards = [(l - box.left, t - box.top, r - box.left, b - box.top) for l, t, r, b in box.inner]

        def in_card(w: dict[str, Any]) -> bool:
            cx, cy = w["left"] + w["width"] / 2, w["top"] + w["height"] / 2
            return any(l <= cx <= r and t <= cy <= b for l, t, r, b in cards)

        card_words: list[str] = []
        body_lines: list[list[dict[str, Any]]] = []
        for ln in lines:
            kept = []
            for w in ln["words"]:
                if in_card(w):
                    card_words.append(w["text"])
                else:
                    kept.append(w)
            if kept:
                body_lines.append(kept)

        forwarded = False
        if body_lines and _FORWARDED_RE.match(" ".join(w["text"] for w in body_lines[0])):
            forwarded = True
            body_lines = body_lines[1:]

        time: Optional[str] = None
        time_partial = ""
        if not box.cut_bottom:
            word = None
            last = body_lines[-1] if body_lines else []
            idx = _trailing_time_index(last, crop.width, page.width) if last else None
            if idx is not None:
                first = last[idx]
                word = {
                    "text": " ".join(w["text"] for w in last[idx:]),
                    "left": box.left + first["left"],
                    "top": box.top + min(w["top"] for w in last[idx:]),
                    "width": box.right - box.left - first["left"],
                    "height": max(w["height"] for w in last[idx:]),
                }
                body_lines[-1] = last[:idx]
            else:
                # O OCR do balao nao enxergou o horario: recorta o canto
                # inferior direito, onde ele sempre fica.
                band = int(page.height * 0.032)
                x0 = box.right - int(page.width * 0.17)
                for w in last:
                    if w["top"] + w["height"] > box.height - band:
                        x0 = max(x0, box.left + w["left"] + w["width"] + 6)
                if x0 < box.right - 20:
                    word = {"text": "", "left": x0, "top": box.bottom - band,
                            "width": box.right - 4 - x0, "height": band - 12}
            if word is not None:
                time, time_partial = self._read_time_parts(page, word)

        text = "\n".join(" ".join(w["text"] for w in ln) for ln in body_lines if ln).strip()
        text = re.sub(r"\s*\n\s*", " ", text)
        card_text = " ".join(card_words)
        truncated = bool(_READ_MORE_RE.search(text))
        if truncated:
            text = _READ_MORE_RE.sub("", text).rstrip(" .…")

        if _CALL_RE.search(text):
            kind, text = "call", _CALL_RE.search(text).group(0)
        elif _AUDIO_RE.search(text) and len(text) < 40:
            kind, text = "audio", ""
        elif _DOCUMENT_RE.search(f"{card_text} {text}"):
            kind = "document"
        elif not text and cards:
            kind = "media"
        else:
            kind = "text"
        if not text and kind == "text":
            return None
        return ScreenBubble(
            text=text, time=time, top=box.top, kind=kind, truncated=truncated,
            side=box.side, cut=box.cut_top or box.cut_bottom, forwarded=forwarded,
            card_text=card_text, time_partial=time_partial,
        )

    # ------------------------------------------------------------------
    # Leitura por linhas (reserva: papel de parede com foto)

    def _read_lines(
        self,
        reading: ScreenshotReading,
        page: Any,
        body: list[dict[str, Any]],
        captured_date: Optional[date],
    ) -> None:
        width = page.width
        current_date: Optional[date] = None
        current_label: Optional[str] = None
        pending: list[str] = []
        pending_top: Optional[int] = None
        pending_left: Optional[int] = None

        for line in body:
            line = _clean_body_line(line)
            if line is None:
                continue

            text = " ".join(w["text"] for w in line["words"]).strip()
            if is_date_label(text):
                self._flush_call(reading, pending, pending_top, current_date, current_label)
                pending, pending_top, pending_left = [], None, None
                current_label = text
                current_date = resolve_date_label(text, captured_date)
                reading.date_labels.append(text)
                continue

            time_idx = _find_time_token(line["words"])
            line_left = min(w["left"] for w in line["words"])
            if time_idx is None:
                if len(text) >= 2:
                    pending.append(text)
                    pending_top = line["top"] if pending_top is None else pending_top
                    pending_left = line_left if pending_left is None else min(pending_left, line_left)
                continue

            body_text = " ".join(w["text"] for w in line["words"][:time_idx]).strip()
            if body_text:
                pending.append(body_text)
                pending_top = line["top"] if pending_top is None else pending_top
                pending_left = line_left if pending_left is None else min(pending_left, line_left)
            time_word = line["words"][time_idx]
            bubble_text = " ".join(pending).strip()
            truncated = bool(_READ_MORE_RE.search(bubble_text))
            if truncated:
                bubble_text = _READ_MORE_RE.sub("", bubble_text).rstrip(" .…")
            kind = "call" if _CALL_RE.search(bubble_text) else "text"
            if kind == "text" and _DOCUMENT_RE.search(bubble_text):
                kind = "document"
            if kind == "call":
                bubble_text = _CALL_RE.search(bubble_text).group(0)
            if bubble_text or kind == "call":
                reading.bubbles.append(ScreenBubble(
                    text=bubble_text,
                    time=self._read_time(page, time_word),
                    top=pending_top if pending_top is not None else line["top"],
                    kind=kind,
                    date=current_date,
                    date_label=current_label,
                    truncated=truncated,
                    side=None if pending_left is None else (
                        "left" if pending_left < width * _LEFT_SIDE_MAX else "right"),
                ))
            pending, pending_top, pending_left = [], None, None

        self._flush_call(reading, pending, pending_top, current_date, current_label)

    @staticmethod
    def _flush_call(
        reading: ScreenshotReading,
        pending: list[str],
        top: Optional[int],
        current_date: Optional[date],
        current_label: Optional[str],
    ) -> None:
        """Registra balao de ligacao cujo horario ficou ilegivel."""
        m = _CALL_RE.search(" ".join(pending))
        if m:
            reading.bubbles.append(ScreenBubble(
                text=m.group(0), time=None, top=top or 0, kind="call",
                date=current_date, date_label=current_label,
            ))

    def _read_time(self, page: Any, word: dict[str, Any]) -> Optional[str]:
        return self._read_time_parts(page, word)[0]

    def _read_time_parts(self, page: Any, word: dict[str, Any]) -> tuple[Optional[str], str]:
        """Rele o horario de um balao em recortes ampliados so com digitos.

        O OCR erra horarios pequenos de varios jeitos ("11:34" sai "1:34",
        ":34" ou "n:34"). Cada variante de recorte e lida e o resultado so e
        aceito quando duas leituras concordam e nenhuma leitura parcial o
        contradiz. Sem consenso, o horario fica ilegivel: melhor do que um
        horario errado, que apareceria como divergencia. Devolve tambem a
        melhor leitura parcial ("1:34"), anotada no relatorio.
        """
        import pytesseract
        from PIL import Image, ImageOps

        box = (
            max(word["left"] - 12, 0), max(word["top"] - 8, 0),
            word["left"] + word["width"] + 12, word["top"] + word["height"] + 8,
        )
        try:
            base = ImageOps.expand(page.crop(box), border=20, fill=255)
        except Exception as exc:
            logger.debug("Recorte do horario falhou: %s", exc)
            return None, ""
        reads: list[str] = [word["text"]]
        for psm, scale, threshold in _TIME_VARIANTS:
            crop = base.resize((base.width * scale, base.height * scale), Image.LANCZOS)
            if threshold:
                crop = crop.point(lambda p, t=threshold: 0 if p < t else 255)
            try:
                text = pytesseract.image_to_string(
                    crop, config=f"--psm {psm} -c tessedit_char_whitelist=0123456789:"
                ).strip()
            except Exception as exc:
                logger.debug("Releitura de horario falhou: %s", exc)
                continue
            reads.append(text)
            if _time_consensus(reads, final=False)[0]:
                break
        return _time_consensus(reads, final=True)


# Variantes de releitura do horario: (modo do Tesseract, ampliacao, limiar)
_TIME_VARIANTS = (
    (7, 3, 0), (7, 3, 150), (8, 3, 0), (8, 4, 150),
    (7, 2, 0), (7, 4, 150), (8, 2, 0), (8, 4, 0),
)


def _time_consensus(reads: list[str], final: bool) -> tuple[Optional[str], str]:
    """Horario aceito a partir de varias leituras do mesmo recorte.

    O WhatsApp em portugues mostra a hora sempre com dois digitos ("09:56");
    leitura com um digito so ("1:34") e digito perdido, nao outra hora. Um
    candidato precisa terminar com cada leitura parcial (":34", "1:34") e ter
    duas leituras a favor (uma basta no fim, se vier com os dois-pontos e nada
    a contradisser). Devolve (horario ou None, melhor leitura parcial).
    """
    table = str.maketrans({"O": "0", "o": "0", "S": "5", "l": "1", "I": "1", "|": "1",
                           ";": ":", ".": ":", ",": ":"})
    full: Counter = Counter()
    with_colon: set[str] = set()
    partial: set[str] = set()
    for raw in reads:
        t = re.sub(r"\s+", "", raw).translate(table)
        m = re.fullmatch(r"(\d{2}):(\d{2})\d?", t)  # o tique as vezes vira um digito
        if m and _TIME_RE.match(f"{m.group(1)}:{m.group(2)}"):
            hhmm = f"{m.group(1)}:{m.group(2)}"
            full[hhmm] += 1
            with_colon.add(hhmm)
            continue
        if re.fullmatch(r"\d{4,5}", t) and _TIME_RE.match(f"{t[:2]}:{t[2:4]}"):
            full[f"{t[:2]}:{t[2:4]}"] += 1
            continue
        m = re.search(r"(\d?:\d{2})\d?$", t)
        if m:
            partial.add(m.group(1))
    best_partial = max(partial, key=len, default="")
    ok = [t for t in full if all(t.endswith(p) for p in partial)]
    if not ok:
        return None, best_partial
    best = max(ok, key=lambda t: (full[t], t in with_colon))
    if full[best] >= 2 and best in with_colon:
        return best, ""
    if final and (full[best] >= 2 or best in with_colon):
        return best, ""
    return None, best_partial


def _group_lines(data: dict[str, list[Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[int, int, int], dict[str, Any]] = {}
    for i, raw in enumerate(data["text"]):
        text = str(raw).strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except (KeyError, TypeError, ValueError):
            conf = 100.0
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        word = {
            "text": text, "conf": conf,
            "left": data["left"][i], "top": data["top"][i],
            "width": data["width"][i], "height": data["height"][i],
        }
        line = groups.setdefault(key, {"top": word["top"], "words": []})
        line["top"] = min(line["top"], word["top"])
        line["words"].append(word)
    return sorted(groups.values(), key=lambda ln: ln["top"])


def _clean_body_line(line: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Linha do corpo da conversa sem o lixo de OCR.

    Descarta palavras com confianca baixa (linha cortada na borda, miniatura de
    documento), exceto horarios, que sao relidos depois; e linhas so de letras
    soltas ("d D D D"), que sao icones lidos como texto.
    """
    words = [
        w for w in line["words"]
        if w.get("conf", 100.0) >= _MIN_WORD_CONFIDENCE or sum(c.isdigit() for c in w["text"]) >= 2
    ]
    if not any(len(w["text"]) > 1 for w in words):
        return None
    return {"top": line["top"], "words": words}


def _find_time_token(words: list[dict[str, Any]]) -> Optional[int]:
    """Indice do horario do balao: um dos ultimos tokens da linha.

    O que vem depois dele sao os tiques de leitura, lidos como lixo.
    """
    for idx in range(len(words) - 1, max(len(words) - 4, -1), -1):
        t = words[idx]["text"]
        if _TIME_LIKE_RE.match(t) and sum(c.isdigit() for c in t) >= 2:
            return idx
    return None


def _trailing_time_index(words: list[dict[str, Any]], crop_width: int, page_width: int) -> Optional[int]:
    """Indice de onde comeca o horario na ultima linha do balao.

    O horario fica encostado na borda direita do balao (seguido, nas enviadas,
    dos tiques de leitura, que o OCR le como lixo: "v", "&", "/"). So o que
    esta nesse canto conta; um numero no meio do texto ("as 15:00") nao.
    """
    corner = crop_width - page_width * 0.2
    idx = len(words) - 1
    # Tiques de leitura depois do horario: o OCR le como "v", "&", "Z", "4"
    while idx > 0 and len(words[idx]["text"]) <= 2:
        idx -= 1
    if idx < 0 or len(words[idx]["text"]) < 3 or not any(c.isdigit() for c in words[idx]["text"]):
        return None
    if words[idx]["left"] < corner:
        return None
    return idx


def _normalize_time(text: str) -> str:
    table = str.maketrans({"O": "0", "o": "0", "S": "5", "l": "1", "I": "1", "|": "1", ";": ":", ".": ":", ",": ":"})
    t = text.translate(table)
    digits = re.sub(r"\D", "", t)
    if ":" not in t and len(digits) >= 4:
        # Horario sem os dois-pontos, as vezes seguido do tique lido como digito
        return f"{digits[:2]}:{digits[2:4]}"
    m = re.search(r"(\d{1,2}):(\d{2})", t)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return t


def _clean_contact(words: list[dict[str, Any]]) -> str:
    """Nome no cabecalho da conversa, sem os icones lidos como texto."""
    kept: list[str] = []
    for w in words:
        t = w["text"]
        if len(t) < 2 or not any(c.isalpha() for c in t):
            continue
        kept.append(t)
        if t.endswith(("...", "…")):
            break  # nome truncado; o que vem depois sao os icones
    # Icones de video/ligacao a direita costumam virar tokens curtos ("R.", "M").
    while len(kept) > 1 and len(kept[-1].strip(".")) <= 2:
        kept.pop()
    return " ".join(kept).strip()
