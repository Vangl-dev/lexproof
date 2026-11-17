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
    LEGENDA_DE_MIDIA = "legenda_de_midia"
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
            "legenda_de_midia": "Legenda de mídia (a exportação sem mídia não traz o texto)",
            "data_divergente": "Data diferente",
            "nao_encontrada": "Não encontrada na exportação",
        }[self.value]

    @property
    def ok(self) -> bool:
        return self in (CheckStatus.CONFERE, CheckStatus.CONFERE_SEM_HORARIO, CheckStatus.NAO_CONFERIDO,
                        CheckStatus.LEGENDA_DE_MIDIA)

    @property
    def counted(self) -> bool:
        """Entra na conta "X de Y conferem" (o que nao pode ser conferido, nao)."""
        return self not in (CheckStatus.NAO_CONFERIDO, CheckStatus.LEGENDA_DE_MIDIA)


@dataclass
class BubbleCheck:
    """Conferencia de um balao do print."""

    bubble: ScreenBubble
    status: CheckStatus
    message: Optional[WhatsAppMessage] = None
    similarity: float = 0.0
    notes: list[str] = field(default_factory=list)
    # O que pode explicar a divergencia sem alteracao da conversa (marcado com
    # * no relatorio)
    hints: list[str] = field(default_factory=list)


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
    # Explicacoes possiveis para contato diferente e mensagens omitidas
    contact_hints: list[str] = field(default_factory=list)
    hidden_hints: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Baloes conferiveis (exclui os cortados demais para conferir)."""
        return sum(1 for c in self.checks if c.status.counted)

    @property
    def confirmed(self) -> int:
        return sum(1 for c in self.checks if c.status.ok and c.status.counted)

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


_URL_START_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
_PLAIN_WORD_RE = re.compile(r"^[A-Za-zÀ-ÿ]{2,}[.,;:!?)]*$")
# Abaixo disto, o link do print e o da exportacao sao considerados diferentes
_URL_THRESHOLD = 0.85


def split_urls(text: str) -> tuple[str, list[str]]:
    """Separa os links do texto.

    No print, um link longo quebra em varias linhas e o OCR o devolve em
    pedacos ("https://exemplo.com.br l/sala/19%3a..."). Os pedacos
    seguintes ao comeco do link sao reconhecidos por terem %, /, =, ? ou
    digitos misturados com letras; a primeira palavra comum encerra o link.
    Devolve o texto com "link" no lugar e os links sem espacos.
    """
    tokens = text.split()
    out: list[str] = []
    urls: list[str] = []
    i = 0
    while i < len(tokens):
        if _URL_START_RE.search(tokens[i]):
            parts = [tokens[i]]
            i += 1
            while i < len(tokens) and not _PLAIN_WORD_RE.match(tokens[i]):
                parts.append(tokens[i])
                i += 1
            urls.append("".join(parts))
            out.append("link")
            continue
        out.append(tokens[i])
        i += 1
    return " ".join(out), urls


def url_similarity(screen: list[str], export: list[str], partial: bool) -> float:
    """Semelhanca entre os links do print e os da exportacao (1.0 = iguais)."""
    a, b = "".join(screen).lower(), "".join(export).lower()
    if not a or not b:
        return 1.0 if a == b else 0.0
    sm = SequenceMatcher(None, a, b, autojunk=False)
    if partial:
        # Balao cortado: o print mostra so um trecho do link.
        return sum(blk.size for blk in sm.get_matching_blocks()) / min(len(a), len(b))
    return sm.ratio()


def _norm(text: str) -> str:
    text = split_urls(text)[0]
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
    if len(shorter) < 6:
        return False
    if longer.startswith(shorter):
        return True
    # O OCR troca letras parecidas no cabecalho ("albuquerq..." lido "albuquerg...").
    # Tolera uma letra diferente, nunca no comeco do nome.
    prefix = longer[: len(shorter)]
    wrong = [i for i, (a, b) in enumerate(zip(shorter, prefix)) if a != b]
    return len(wrong) == 1 and wrong[0] >= 4


def is_ocr_noise(diffs: list[tuple[str, str]]) -> bool:
    """Diferencas que parecem erro de leitura, nao alteracao do texto.

    Vale para letras trocadas numa palavra ("cyujo" x "cujo") e letras soltas
    sobrando. Qualquer diferenca em numeros, ou palavra inteira a mais, a menos
    ou trocada, NAO e ruido.
    """
    for a, b in diffs:
        if _lookalike(a, b):
            continue  # "lh" x "1h", "2O26" x "2026"
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


# Letras que o OCR confunde com digitos ("1h" lido "lh", "2026" lido "2O26")
_LOOKALIKE = str.maketrans({"l": "1", "i": "1", "I": "1", "|": "1", "!": "1", "o": "0", "O": "0"})


def _lookalike(a: str, b: str) -> bool:
    """Mesmo texto se letras parecidas com digitos forem lidas como digitos."""
    return len(a) == len(b) and a.translate(_LOOKALIKE) == b.translate(_LOOKALIKE)


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


_MEDIA_TYPES = (MessageType.MEDIA, MessageType.AUDIO, MessageType.VIDEO, MessageType.STICKER)


def _is_media(msg: WhatsAppMessage) -> bool:
    return (msg.message_type in _MEDIA_TYPES or bool(msg.media_reference)
            or "(arquivo anexado)" in msg.content or "(file attached)" in msg.content)


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
        by_box = getattr(reading, "method", "") == "baloes"
        for idx, bubble in enumerate(reading.bubbles):
            # Balao cortado pela borda da tela mostra so parte da mensagem. Na
            # leitura por baloes o corte e medido; por linhas, supoe-se nas pontas.
            self._may_be_cut = bubble.truncated or getattr(bubble, "cut", False) or (
                not by_box and idx in (0, last))
            check = self._check_bubble(bubble, reading, used)
            if check.message is not None:
                used.add(check.message.line_number)
            if not check.status.ok:
                check.hints = divergence_hints(check, reading, self._messages)
            result.checks.append(check)

        if self._export_contact and reading.contact:
            result.contact_matches = names_match(self._export_contact, reading.contact)
            if not result.contact_matches:
                result.contact_hints = contact_hints(reading.contact, self._export_contact)

        matched = [c.message for c in result.checks if c.message is not None]
        if reading.captured_at and matched:
            result.captured_after_messages = reading.captured_at >= max(m.timestamp for m in matched)

        lines = [m.line_number for m in matched]
        result.order_ok = lines == sorted(lines)

        if matched:
            lo, hi = min(lines), max(lines)
            for m in self._messages:
                if lo < m.line_number < hi and m.line_number not in used:
                    if _is_media(m):
                        result.hidden_media += 1
                    else:
                        result.hidden_messages.append(m)
        if result.hidden_messages:
            result.hidden_hints = hidden_hints(result)
        return result

    # ------------------------------------------------------------------

    def _check_bubble(
        self, bubble: ScreenBubble, reading: ScreenshotReading, used: set[int]
    ) -> BubbleCheck:
        pool = [m for m in self._messages if m.line_number not in used]
        if bubble.kind == "call":
            return self._check_call(bubble, pool)
        if bubble.kind in ("document", "media", "audio"):
            return self._check_media(bubble, pool)
        cut = bubble.truncated or getattr(bubble, "cut", False)
        if cut and len(_norm(bubble.text).split()) < 3:
            check = self._check_text(bubble, reading, pool)
            if check.status.ok:
                return check
            return BubbleCheck(bubble, CheckStatus.NAO_CONFERIDO, notes=[
                "Balão cortado na borda do print; o trecho visível é curto demais para conferir."])
        return self._check_text(bubble, reading, pool)

    def _check_text(
        self, bubble: ScreenBubble, reading: ScreenshotReading, pool: list[WhatsAppMessage]
    ) -> BubbleCheck:

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
            return self._caption_or_missing(bubble, pool)

        # Sem separador de data acima do balao: a data e anterior ao primeiro
        # separador do print e o horario desempata textos repetidos.
        limit = reading.first_separator_date
        candidates = [m for m in pool if limit is None or m.timestamp.date() <= limit]
        best, score = self._best(bubble, candidates)
        if best is None:
            return self._caption_or_missing(bubble, candidates)
        check = self._with_time(bubble, best, score)
        check.notes.append("Data deduzida: o print nao mostra o separador de data deste balao.")
        return check

    def _caption_or_missing(self, bubble: ScreenBubble, pool: list[WhatsAppMessage]) -> BubbleCheck:
        """Texto que nao esta na exportacao, mas no horario de uma midia.

        Foto, video ou documento enviado com legenda aparece na exportacao sem
        midia so como "<Midia oculta>": a legenda se perde. O texto nao pode
        ser conferido, mas a mensagem existe.
        """
        if bubble.time:
            media = [m for m in pool if _is_media(m) and _hhmm(m) == bubble.time
                     and (bubble.date is None or m.timestamp.date() == bubble.date)]
            if media:
                return BubbleCheck(bubble, CheckStatus.LEGENDA_DE_MIDIA, media[0], 0.0, [
                    "Texto no horário de uma mídia da exportação. O WhatsApp, ao exportar sem "
                    "mídia, registra só \"<Mídia oculta>\" e descarta a legenda; por isso o texto "
                    "não pôde ser conferido."])
        return BubbleCheck(bubble, CheckStatus.NAO_ENCONTRADA)

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
        url_diff: Optional[tuple[str, str]] = None
        if bubble.kind == "text":
            cut = getattr(self, "_may_be_cut", False)
            _, diffs, partial = aligned_match(bubble.text, msg.content, cut)
            if partial:
                notes.append("Balão cortado na borda do print: conferido o trecho visível.")
            if diffs and is_ocr_noise(diffs):
                pairs = "; ".join(f"\"{a or '(nada)'}\" x \"{b or '(nada)'}\"" for a, b in diffs)
                notes.append(f"Pequena diferença de leitura do OCR, sem alterar palavras ou números: {pairs}.")
                diffs = []
            # Links sao comparados a parte (o OCR de link longo sublinhado e ruim).
            screen_urls, export_urls = split_urls(bubble.text)[1], split_urls(msg.content)[1]
            if screen_urls and export_urls:
                ratio = url_similarity(screen_urls, export_urls, cut)
                if ratio < _URL_THRESHOLD:
                    url_diff = ("".join(screen_urls)[:80], "".join(export_urls)[:80])
                    notes.append(f"Link do print só {ratio:.0%} igual ao da exportação.")
                elif "".join(screen_urls).lower() != "".join(export_urls).lower():
                    notes.append(f"Link lido com pequenas diferenças de OCR ({ratio:.0%} igual); links "
                                 f"longos e sublinhados são difíceis de ler.")
        if url_diff is not None:
            diffs.append(url_diff)
        if diffs:
            for screen, export in diffs:
                notes.append(f"Print: \"{screen or '(nada)'}\" | Exportacao: \"{export or '(nada)'}\"")
            if bubble.time is not None and bubble.time != _hhmm(msg):
                notes.append(f"Print mostra {bubble.time}; exportacao registra {_hhmm(msg)}.")
            return BubbleCheck(bubble, CheckStatus.TEXTO_DIVERGENTE, msg, score, notes)
        if bubble.time is None:
            partial = getattr(bubble, "time_partial", "")
            if partial and _hhmm(msg).endswith(partial):
                notes.append(f"Horário lido só em parte no print (\"{partial}\"), compatível com "
                             f"{_hhmm(msg)} da exportação.")
            return BubbleCheck(bubble, CheckStatus.CONFERE_SEM_HORARIO, msg, score, notes)
        if bubble.time == _hhmm(msg):
            return BubbleCheck(bubble, CheckStatus.CONFERE, msg, score, notes)
        notes.append(f"Print mostra {bubble.time}; exportacao registra {_hhmm(msg)}.")
        return BubbleCheck(bubble, CheckStatus.HORARIO_DIVERGENTE, msg, score, notes)

    def _check_media(self, bubble: ScreenBubble, pool: list[WhatsAppMessage]) -> BubbleCheck:
        """Documento, foto, video ou audio: confere pelo horario com a midia da exportacao."""
        media = [
            m for m in pool
            if _is_media(m) and (bubble.date is None or m.timestamp.date() == bubble.date)
        ]
        what = {"document": "Documento anexado", "audio": "Áudio"}.get(bubble.kind, "Mídia")
        note = f"{what}: conferido pelo horário (o conteúdo da mídia não é lido)."
        if bubble.time:
            exact = [m for m in media if _hhmm(m) == bubble.time]
            if exact:
                return BubbleCheck(bubble, CheckStatus.CONFERE, exact[-1], 1.0, [note])
        elif len(media) == 1:
            return BubbleCheck(bubble, CheckStatus.CONFERE_SEM_HORARIO, media[0], 1.0, [note])
        if getattr(bubble, "cut", False) and not bubble.time:
            return BubbleCheck(bubble, CheckStatus.NAO_CONFERIDO, notes=[
                f"{what} cortado na borda do print, sem horário visível: não conferido."])
        return BubbleCheck(bubble, CheckStatus.NAO_ENCONTRADA, notes=[f"{what} sem mídia correspondente."])

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


# ----------------------------------------------------------------------
# O que pode explicar uma divergencia (marcado com * no relatorio)
#
# A leitura do print e automatica (OCR). Antes de tratar uma divergencia como
# indicio de alteracao, o relatorio aponta as causas tecnicas que produzem o
# mesmo resultado sem que a conversa tenha mudado. Sao hipoteses para conferir
# olhando o print, nao conclusoes.

HINT_JOINED = (
    "O texto lido parece juntar mensagens seguidas da conversa: dois ou mais balões "
    "podem ter sido lidos como um só."
)
HINT_PARTIAL = (
    "O texto lido corresponde a só uma parte de uma mensagem da conversa: o balão pode "
    "ter sido lido pela metade ou partido em dois."
)
HINT_GARBLED = (
    "O texto lido tem muitos caracteres sem sentido: pode ser ícone, figurinha, prévia "
    "de link ou outro elemento da tela lido como texto."
)
HINT_LINES = (
    "Este print foi lido por linhas, não por balões (papel de parede com foto ou tela "
    "fora do padrão), o que aumenta o risco de balões juntados ou partidos."
)
HINT_TIME_DIGIT = (
    "Os horários diferem em um só dígito, típico de erro de leitura dos números "
    "pequenos do balão (sobretudo no tema escuro)."
)
HINT_TIME_IN_TEXT = (
    "O horário lido aparece no próprio texto da mensagem: o OCR pode ter tomado um "
    "horário escrito na mensagem pelo horário do balão."
)
HINT_TIME_ZONE = (
    "A diferença é de horas exatas: pode ser fuso horário diferente entre o celular do "
    "print e o celular que exportou a conversa."
)
HINT_LOOKALIKE = (
    "A diferença envolve letras e números parecidos (l e 1, O e 0, rn e m), comuns em "
    "erro de leitura."
)
HINT_SCREEN_ELEMENT = (
    "O balão tem prévia de link, mensagem citada ou a marca “Encaminhada”, que "
    "não fazem parte do texto exportado e podem ter sido lidas junto."
)
HINT_DATE_LABEL = (
    "O separador de data acima do balão pode ter sido lido errado; “Hoje”, "
    "“Ontem” e dias da semana dependem da data em que o print foi tirado."
)
HINT_OTHER_DEVICE = (
    "Também acontece quando a mensagem foi apagada depois do print, ou quando a "
    "exportação foi feita em outro aparelho ou a partir de um backup."
)


def _letters_ratio(text: str) -> float:
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 0.0
    words = [w for w in re.findall(r"[^\W\d_]{3,}", text)]
    return sum(len(w) for w in words) / len(chars)


def divergence_hints(
    check: BubbleCheck, reading: ScreenshotReading, messages: list[WhatsAppMessage]
) -> list[str]:
    """Causas tecnicas que explicariam a divergencia sem alteracao da conversa."""
    b = check.bubble
    hints: list[str] = []
    if check.status == CheckStatus.NAO_ENCONTRADA and b.kind == "text":
        words = _norm(b.text).split()
        joined = partial = False
        for i in range(len(messages) - 1):
            pair = f"{messages[i].content} {messages[i + 1].content}"
            if len(words) >= 3 and _similarity(b.text, pair) >= _TEXT_THRESHOLD - 0.1:
                joined = True
                break
        if not joined and len(words) >= 2:
            for m in messages:
                mw = _norm(m.content).split()
                if len(mw) > len(words) and aligned_match(b.text, m.content, True)[0] >= _TEXT_THRESHOLD:
                    partial = True
                    break
                if len(mw) < len(words) and len(mw) >= 2 and " ".join(mw) in " ".join(words):
                    joined = True
                    break
        if joined:
            hints.append(HINT_JOINED)
        if partial:
            hints.append(HINT_PARTIAL)
        if _letters_ratio(b.text) < 0.6:
            hints.append(HINT_GARBLED)
    if check.status == CheckStatus.HORARIO_DIVERGENTE and check.message is not None and b.time:
        shown, exported = b.time, _hhmm(check.message)
        if sum(x != y for x, y in zip(shown, exported)) == 1:
            hints.append(HINT_TIME_DIGIT)
        if shown in b.text or shown in check.message.content:
            hints.append(HINT_TIME_IN_TEXT)
        if shown[3:] == exported[3:] and shown[:2] != exported[:2]:
            hints.append(HINT_TIME_ZONE)
    if check.status == CheckStatus.TEXTO_DIVERGENTE and check.message is not None:
        diffs = text_differences(b.text, check.message.content)
        if any(_lookalike(a.replace(" ", ""), e.replace(" ", ""))
               or (a and e and SequenceMatcher(None, a, e).ratio() >= 0.6) for a, e in diffs):
            hints.append(HINT_LOOKALIKE)
    if check.status == CheckStatus.DATA_DIVERGENTE:
        hints.append(HINT_DATE_LABEL)
    if getattr(b, "forwarded", False) or getattr(b, "card_text", ""):
        hints.append(HINT_SCREEN_ELEMENT)
    if getattr(reading, "method", "") == "linhas":
        hints.append(HINT_LINES)
    if check.status == CheckStatus.NAO_ENCONTRADA:
        hints.append(HINT_OTHER_DEVICE)
    return hints


def contact_hints(shown: str, exported: str) -> list[str]:
    """Por que o nome no topo do print pode diferir do nome da exportacao."""
    hints = []
    if shown.rstrip().endswith(("...", "…")):
        hints.append("O topo do print corta nomes longos (“...”) e o OCR pode trocar "
                     "letras parecidas no trecho visível (q e g, rn e m).")
    hints.append("A conversa exportada e o topo do print mostram o nome salvo na agenda de "
                 "cada celular; se o print e a exportação vieram de aparelhos diferentes, o nome "
                 "pode ser outro para o mesmo contato. A tela de perfil, com o número, desfaz a dúvida.")
    return hints


def hidden_hints(result: ScreenshotCheck) -> list[str]:
    """Por que mensagens da exportacao podem parecer ausentes do print."""
    hints = []
    if any(c.status == CheckStatus.NAO_ENCONTRADA for c in result.checks):
        hints.append("Este print tem balões que não foram reconhecidos (marcados como não "
                     "encontrados). A mensagem “omitida” pode ser um deles, lido com erro.")
    if getattr(result.reading, "method", "") == "linhas":
        hints.append(HINT_LINES)
    hints.append("Confira olhando o print: se a mensagem aparece nele, a omissão é erro de leitura.")
    return hints
