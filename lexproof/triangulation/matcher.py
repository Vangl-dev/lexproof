"""Confronto dos baloes de um print com as mensagens da exportacao."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from pathlib import Path
from typing import Optional

from lexproof.models.message import MessageType, WhatsAppMessage
from lexproof.triangulation.screenshot_reader import ScreenBubble, ScreenshotReading

_TEXT_THRESHOLD = 0.75
_EXPORT_CONTACT_RE = re.compile(
    r"(?:Conversa do WhatsApp com|WhatsApp Chat with|Chat de WhatsApp con)\s+(.+?)(?:\.txt)?$",
    re.IGNORECASE,
)


class CheckStatus(str, Enum):
    """Resultado da conferencia de um balao."""

    CONFERE = "confere"
    CONFERE_SEM_HORARIO = "confere_sem_horario"
    HORARIO_DIVERGENTE = "horario_divergente"
    TEXTO_DIVERGENTE = "texto_divergente"
    NAO_CONFERIDO = "nao_conferido"
    DATA_DIVERGENTE = "data_divergente"
    NAO_ENCONTRADA = "nao_encontrada"

    @property
    def label(self) -> str:
        return {
            "confere": "Confere",
            "confere_sem_horario": "Confere (horário ilegível no print)",
            "horario_divergente": "Horário diferente",
            "texto_divergente": "Texto diferente",
            "nao_conferido": "Cortado no print (não conferido)",
            "data_divergente": "Data diferente",
            "nao_encontrada": "Não encontrada na exportação",
        }[self.value]

    @property
    def ok(self) -> bool:
        return self in (CheckStatus.CONFERE, CheckStatus.CONFERE_SEM_HORARIO, CheckStatus.NAO_CONFERIDO)


@dataclass
class BubbleCheck:
    """Conferencia de um balao do print."""

    bubble: ScreenBubble
    status: CheckStatus
    message: Optional[WhatsAppMessage] = None
    similarity: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass
class ScreenshotCheck:
    """Conferencia completa de um print."""

    reading: ScreenshotReading
    checks: list[BubbleCheck] = field(default_factory=list)
    export_contact: Optional[str] = None
    contact_matches: Optional[bool] = None
    captured_after_messages: Optional[bool] = None
    order_ok: bool = True
    hidden_messages: list[WhatsAppMessage] = field(default_factory=list)
    hidden_media: int = 0

    @property
    def total(self) -> int:
        """Baloes conferiveis (exclui os cortados demais para conferir)."""
        return sum(1 for c in self.checks if c.status != CheckStatus.NAO_CONFERIDO)

    @property
    def confirmed(self) -> int:
        return sum(1 for c in self.checks if c.status.ok and c.status != CheckStatus.NAO_CONFERIDO)

    @property
    def divergent(self) -> list[BubbleCheck]:
        return [c for c in self.checks if not c.status.ok]

    @property
    def all_ok(self) -> bool:
        return (
            self.total > 0
            and not self.divergent
            and self.order_ok
            and not self.hidden_messages
            and self.contact_matches is not False
            and self.captured_after_messages is not False
        )


def export_contact_name(export_path: Path) -> Optional[str]:
    """Nome do contato a partir do nome do arquivo exportado."""
    m = _EXPORT_CONTACT_RE.search(Path(export_path).stem + ".txt")
    return m.group(1).strip() if m else None


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"<\s*mensagem editada\s*>|<\s*edited\s*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _similarity(a: str, b: str) -> float:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def text_differences(screen: str, export: str) -> list[tuple[str, str]]:
    """Trechos que diferem entre o print e a exportacao (acentos e pontuacao ignorados)."""
    a, b = _norm(screen).split(), _norm(export).split()
    diffs = []
    for op, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != "equal":
            diffs.append((" ".join(a[i1:i2]), " ".join(b[j1:j2])))
    return diffs


def names_match(a: str, b: str) -> bool:
    """Mesmo contato, tolerando o nome truncado no cabecalho ("Paulo Ricardo Sou...")."""
    fa = _norm(a).replace(" ", "")
    fb = _norm(b).replace(" ", "")
    if not fa or not fb:
        return False
    if fa == fb:
        return True
    shorter, longer = sorted((fa, fb), key=len)
    return len(shorter) >= 6 and longer.startswith(shorter)


def is_ocr_noise(diffs: list[tuple[str, str]]) -> bool:
    """Diferencas que parecem erro de leitura, nao alteracao do texto.

    Vale para letras trocadas numa palavra ("cyujo" x "cujo") e letras soltas
    sobrando. Qualquer diferenca em numeros, ou palavra inteira a mais, a menos
    ou trocada, NAO e ruido.
    """
    for a, b in diffs:
        if re.sub(r"\D", "", a) != re.sub(r"\D", "", b):
            return False
        if a.replace(" ", "") == b.replace(" ", ""):
            continue  # palavras grudadas ou separadas pelo OCR ("comisto" x "com isto")
        if a and b:
            if len(a.split()) != len(b.split()):
                return False
            if SequenceMatcher(None, a, b).ratio() < 0.6:
                return False
        elif any(len(t) > 1 for t in (a or b).split()):
            return False
    return True


def aligned_match(screen: str, export: str, may_be_cut: bool) -> tuple[float, list[tuple[str, str]], bool]:
    """Semelhanca e diferencas entre o texto do print e a mensagem.

    Balao cortado na borda do print (ou com "Ler mais") mostra so o comeco ou o
    fim da mensagem; nesse caso compara com o trecho correspondente.
    Retorna (semelhanca, diferencas, comparou_so_um_trecho).
    """
    sw, ew = _norm(screen).split(), _norm(export).split()
    if not sw or not ew:
        return 0.0, [], False
    s_text = " ".join(sw)
    best = (SequenceMatcher(None, s_text, " ".join(ew)).ratio(), ew, False)
    if may_be_cut and len(sw) >= 3 and len(sw) < len(ew):
        for size in (len(sw) - 1, len(sw), len(sw) + 1):
            if not 0 < size < len(ew):
                continue
            for window in (ew[:size], ew[-size:]):
                ratio = SequenceMatcher(None, s_text, " ".join(window)).ratio()
                if ratio > best[0]:
                    best = (ratio, window, True)
    return best[0], text_differences(s_text, " ".join(best[1])), best[2]


def _hhmm(msg: WhatsAppMessage) -> str:
    return msg.timestamp.strftime("%H:%M")


def _is_call_line(msg: WhatsAppMessage) -> bool:
    # Na exportacao, ligacoes aparecem como mensagem sem conteudo.
    return not msg.content.strip() or bool(
        re.search(r"liga[cç][aã]o|chamada|call", msg.content, re.IGNORECASE)
        and len(msg.content) < 40
    )


class ScreenshotMatcher:
    """Confere os baloes de um print com a conversa exportada."""

    def __init__(self, messages: list[WhatsAppMessage], export_path: Optional[Path] = None) -> None:
        self._messages = [
            m for m in messages if m.message_type != MessageType.SYSTEM
        ]
        self._export_contact = export_contact_name(export_path) if export_path else None

    def check(self, reading: ScreenshotReading) -> ScreenshotCheck:
        result = ScreenshotCheck(reading=reading, export_contact=self._export_contact)
        used: set[int] = set()
        last = len(reading.bubbles) - 1
        for idx, bubble in enumerate(reading.bubbles):
            # Primeiro e ultimo baloes podem estar cortados pela borda da tela.
            self._may_be_cut = bubble.truncated or idx in (0, last)
            check = self._check_bubble(bubble, reading, used)
            if check.message is not None:
                used.add(check.message.line_number)
            result.checks.append(check)

        if self._export_contact and reading.contact:
            result.contact_matches = names_match(self._export_contact, reading.contact)

        matched = [c.message for c in result.checks if c.message is not None]
        if reading.captured_at and matched:
            result.captured_after_messages = reading.captured_at >= max(m.timestamp for m in matched)

        lines = [m.line_number for m in matched]
        result.order_ok = lines == sorted(lines)

        if matched:
            lo, hi = min(lines), max(lines)
            for m in self._messages:
                if lo < m.line_number < hi and m.line_number not in used:
                    if m.message_type == MessageType.MEDIA or m.media_reference:
                        result.hidden_media += 1
                    else:
                        result.hidden_messages.append(m)
        return result

    # ------------------------------------------------------------------

    def _check_bubble(
        self, bubble: ScreenBubble, reading: ScreenshotReading, used: set[int]
    ) -> BubbleCheck:
        pool = [m for m in self._messages if m.line_number not in used]
        if bubble.kind == "call":
            return self._check_call(bubble, pool)
        if bubble.kind == "document":
            return self._check_document(bubble, pool)
        if bubble.truncated and len(_norm(bubble.text).split()) < 3:
            return BubbleCheck(bubble, CheckStatus.NAO_CONFERIDO, notes=[
                "Balão cortado na borda do print; o trecho visível é curto demais para conferir."])

        if bubble.date is not None:
            same_day = [m for m in pool if m.timestamp.date() == bubble.date]
            best, score = self._best(bubble, same_day)
            if best is not None:
                return self._with_time(bubble, best, score)
            best, score = self._best(bubble, pool)
            if best is not None:
                return BubbleCheck(
                    bubble, CheckStatus.DATA_DIVERGENTE, best, score,
                    [f"Na exportacao a mensagem e de {best.timestamp:%d/%m/%Y %H:%M}."],
                )
            return BubbleCheck(bubble, CheckStatus.NAO_ENCONTRADA)

        # Sem separador de data acima do balao: a data e anterior ao primeiro
        # separador do print e o horario desempata textos repetidos.
        limit = reading.first_separator_date
        candidates = [m for m in pool if limit is None or m.timestamp.date() <= limit]
        best, score = self._best(bubble, candidates)
        if best is None:
            return BubbleCheck(bubble, CheckStatus.NAO_ENCONTRADA)
        check = self._with_time(bubble, best, score)
        check.notes.append("Data deduzida: o print nao mostra o separador de data deste balao.")
        return check

    def _best(
        self, bubble: ScreenBubble, pool: list[WhatsAppMessage]
    ) -> tuple[Optional[WhatsAppMessage], float]:
        cut = getattr(self, "_may_be_cut", False)
        scored = [(aligned_match(bubble.text, m.content, cut)[0], m) for m in pool]
        scored = [(s, m) for s, m in scored if s >= _TEXT_THRESHOLD]
        if not scored:
            return None, 0.0
        top = max(s for s, _ in scored)
        # Empate de texto (ex.: "ta demorando?" repetido): prefere o mesmo horario.
        tied = [(s, m) for s, m in scored if s >= top - 0.02]
        for s, m in tied:
            if bubble.time and _hhmm(m) == bubble.time:
                return m, s
        s, m = max(tied, key=lambda t: t[0])
        return m, s

    def _with_time(self, bubble: ScreenBubble, msg: WhatsAppMessage, score: float) -> BubbleCheck:
        notes = []
        if msg.is_edited:
            notes.append("A exportacao marca esta mensagem como editada.")
        diffs: list[tuple[str, str]] = []
        if bubble.kind == "text":
            _, diffs, partial = aligned_match(bubble.text, msg.content, getattr(self, "_may_be_cut", False))
            if partial:
                notes.append("Balão cortado na borda do print: conferido o trecho visível.")
            if diffs and is_ocr_noise(diffs):
                pairs = "; ".join(f"\"{a or '(nada)'}\" x \"{b or '(nada)'}\"" for a, b in diffs)
                notes.append(f"Pequena diferença de leitura do OCR, sem alterar palavras ou números: {pairs}.")
                diffs = []
        if diffs:
            for screen, export in diffs:
                notes.append(f"Print: \"{screen or '(nada)'}\" | Exportacao: \"{export or '(nada)'}\"")
            if bubble.time is not None and bubble.time != _hhmm(msg):
                notes.append(f"Print mostra {bubble.time}; exportacao registra {_hhmm(msg)}.")
            return BubbleCheck(bubble, CheckStatus.TEXTO_DIVERGENTE, msg, score, notes)
        if bubble.time is None:
            return BubbleCheck(bubble, CheckStatus.CONFERE_SEM_HORARIO, msg, score, notes)
        if bubble.time == _hhmm(msg):
            return BubbleCheck(bubble, CheckStatus.CONFERE, msg, score, notes)
        notes.append(f"Print mostra {bubble.time}; exportacao registra {_hhmm(msg)}.")
        return BubbleCheck(bubble, CheckStatus.HORARIO_DIVERGENTE, msg, score, notes)

    def _check_document(self, bubble: ScreenBubble, pool: list[WhatsAppMessage]) -> BubbleCheck:
        """Documento anexado (PDF etc.): confere pelo horario com a midia da exportacao."""
        media = [
            m for m in pool
            if (m.message_type == MessageType.MEDIA or "(arquivo anexado)" in m.content
                or "(file attached)" in m.content)
            and (bubble.date is None or m.timestamp.date() == bubble.date)
        ]
        note = "Documento anexado: conferido pelo horário (o nome do arquivo no print não é legível)."
        if bubble.time:
            exact = [m for m in media if _hhmm(m) == bubble.time]
            if exact:
                return BubbleCheck(bubble, CheckStatus.CONFERE, exact[-1], 1.0, [note])
        elif len(media) == 1:
            return BubbleCheck(bubble, CheckStatus.CONFERE_SEM_HORARIO, media[0], 1.0, [note])
        return BubbleCheck(bubble, CheckStatus.NAO_ENCONTRADA, notes=["Documento anexado sem mídia correspondente."])

    def _check_call(self, bubble: ScreenBubble, pool: list[WhatsAppMessage]) -> BubbleCheck:
        calls = [
            m for m in pool
            if _is_call_line(m) and (bubble.date is None or m.timestamp.date() == bubble.date)
        ]
        if bubble.time:
            exact = [m for m in calls if _hhmm(m) == bubble.time]
            if exact:
                return BubbleCheck(bubble, CheckStatus.CONFERE, exact[0], 1.0)
        if len(calls) == 1:
            return self._with_time(bubble, calls[0], 1.0)
        return BubbleCheck(bubble, CheckStatus.NAO_ENCONTRADA)
