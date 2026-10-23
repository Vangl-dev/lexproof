"""Conferencia dos prints entre si, sem a exportacao da conversa.

Quem tira varios prints de uma conversa rola a tela entre um e outro, e os
prints vizinhos repetem algumas mensagens. Costurando os prints por essas
repeticoes, o LexProof reconstroi o trecho da conversa e aponta:

- lacunas: prints consecutivos sem mensagem em comum;
- contradicoes: a mesma mensagem com texto diferente em dois prints;
- incoerencias: contato ou resolucao de tela diferentes, print anterior as
  mensagens que exibe.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, time
from difflib import SequenceMatcher
from typing import Optional

from lexproof.triangulation.matcher import _norm, is_ocr_noise, names_match, text_differences
from lexproof.triangulation.screenshot_reader import ScreenBubble, ScreenshotReading

# Texto repetido so prova "mesma mensagem" se for longo o bastante;
# "Te amo" ou "ok" repetem em qualquer conversa.
_MIN_DISTINCT_TEXT = 12


@dataclass
class StitchedMessage:
    """Mensagem distinta reconstruida a partir de um ou mais prints."""

    text: str
    date: Optional[date]
    time: Optional[str]
    kind: str
    sources: list[str] = field(default_factory=list)

    @property
    def when(self) -> str:
        if self.date:
            return f"{self.date:%d/%m/%Y} {self.time or '--:--'}"
        return self.time or "horário ilegível"


@dataclass
class Gap:
    """Prints consecutivos sem mensagem em comum."""

    before_print: str
    after_print: str
    last_before: StitchedMessage
    first_after: StitchedMessage


@dataclass
class Contradiction:
    """A mesma mensagem lida de forma diferente em dois prints."""

    print_a: str
    print_b: str
    text_a: str
    text_b: str
    when: str
    differences: list[tuple[str, str]]


@dataclass
class PrintIssue:
    print_name: str
    message: str
    # "info": observacao que nao indica problema por si so (ex.: tamanho de tela)
    severity: str = "warn"


@dataclass
class StitchResult:
    """Resultado da conferencia dos prints entre si."""

    order: list[ScreenshotReading] = field(default_factory=list)
    messages: list[StitchedMessage] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
    contradictions: list[Contradiction] = field(default_factory=list)
    issues: list[PrintIssue] = field(default_factory=list)
    unread: list[str] = field(default_factory=list)

    @property
    def continuous(self) -> bool:
        return not self.gaps

    @property
    def all_ok(self) -> bool:
        return bool(self.order) and not self.gaps and not self.contradictions and not self.warnings

    @property
    def warnings(self) -> list[PrintIssue]:
        return [i for i in self.issues if i.severity != "info"]

    def needs_attention(self, with_export: bool) -> bool:
        """Com a exportacao, cada print ja foi conferido com a conversa; lacunas
        entre prints so indicam que nem tudo foi printado."""
        if with_export:
            return bool(self.contradictions or self.warnings)
        return bool(self.gaps or self.contradictions or self.warnings)

    @property
    def first(self) -> Optional[StitchedMessage]:
        dated = [m for m in self.messages if m.date]
        return dated[0] if dated else None

    @property
    def last(self) -> Optional[StitchedMessage]:
        dated = [m for m in self.messages if m.date]
        return dated[-1] if dated else None


def _key(b: ScreenBubble) -> tuple[str, Optional[str]]:
    return _norm(b.text), b.time


def _same_message(a: ScreenBubble, b: ScreenBubble) -> bool:
    """Mesmo balao visto em dois prints (um deles pode estar cortado na borda)."""
    if a.kind != b.kind or (a.time and b.time and a.time != b.time):
        return False
    if a.date and b.date and a.date != b.date:
        return False
    na, nb = _norm(a.text), _norm(b.text)
    if a.kind == "document":
        return bool(a.time and a.time == b.time)
    if a.kind == "call":
        if a.time and b.time:
            return a.time == b.time
        # Horario ilegivel (coberto pelo botao de rolar): mesmo dia basta.
        return bool(a.date and a.date == b.date)
    if not na or not nb:
        return False
    if na == nb:
        return len(na) >= _MIN_DISTINCT_TEXT or bool(a.time and b.time)
    shorter, longer = sorted((na, nb), key=len)
    # Balao cortado na borda superior/inferior: um texto contem o outro.
    return len(shorter) >= _MIN_DISTINCT_TEXT and (longer.endswith(shorter) or longer.startswith(shorter))


def _aligned_variant(a: ScreenBubble, b: ScreenBubble) -> list[tuple[str, str]] | None:
    """Diferencas quando *a* e *b* sao o mesmo balao (mesmo horario) lido com textos
    diferentes, considerando que um deles pode estar cortado na borda do print.

    Retorna None se nao parecem o mesmo balao.
    """
    if a.kind != "text" or b.kind != "text" or not a.time or a.time != b.time:
        return None
    if a.date and b.date and a.date != b.date:
        return None
    wa, wb = _norm(a.text).split(), _norm(b.text).split()
    short, long_ = (wa, wb) if len(wa) <= len(wb) else (wb, wa)
    if len(short) < 3:
        return None
    best: tuple[float, list[str]] = (0.0, [])
    for window in (long_[: len(short)], long_[-len(short):], long_):
        ratio = SequenceMatcher(None, " ".join(short), " ".join(window)).ratio()
        if ratio > best[0]:
            best = (ratio, window)
    if best[0] < 0.6:
        return None
    a_words, b_words = (short, best[1]) if short is wa else (best[1], short)
    diffs = text_differences(" ".join(a_words), " ".join(b_words))
    # Erro de leitura entre dois prints do mesmo balao nao e contradicao.
    return [] if is_ocr_noise(diffs) else diffs


def _sort_key(b: ScreenBubble, seq: int) -> tuple[date, time, int]:
    t = datetime.strptime(b.time, "%H:%M").time() if b.time else time(0, 0)
    return (b.date or date.min, t, seq)


class ScreenshotStitcher:
    """Costura prints de uma mesma conversa."""

    def stitch(self, readings: list[ScreenshotReading]) -> StitchResult:
        result = StitchResult()
        usable = []
        for r in readings:
            (usable if r.bubbles else result.unread).append(r if r.bubbles else r.path.name)
        if not usable:
            return result

        self._inherit_dates(usable)
        result.order = sorted(usable, key=self._print_position)
        result.messages = self._merge(result.order)
        result.contradictions = self._contradictions(result.order)
        result.gaps = self._gaps(result.order, result.messages)
        result.issues = self._issues(result.order)
        return result

    # ------------------------------------------------------------------

    @staticmethod
    def _inherit_dates(readings: list[ScreenshotReading]) -> None:
        """Balao sem separador de data no print herda a data do mesmo balao em outro print."""
        dated = [b for r in readings for b in r.bubbles if b.date]
        for r in readings:
            for b in r.bubbles:
                if b.date is None:
                    for other in dated:
                        if _same_message(b, other) or _aligned_variant(b, other) is not None:
                            b.date = other.date
                            break

    @staticmethod
    def _print_position(r: ScreenshotReading) -> tuple:
        dated = [b for b in r.bubbles if b.date]
        if dated:
            return (0, _sort_key(dated[0], 0)[:2], r.captured_at or datetime.min.replace(tzinfo=None), r.path.name)
        sep = r.first_separator_date
        return (1, (sep or date.min, time(0, 0)), r.path.name)

    @staticmethod
    def _merge(order: list[ScreenshotReading]) -> list[StitchedMessage]:
        merged: list[tuple[ScreenBubble, StitchedMessage]] = []
        for r in order:
            for b in r.bubbles:
                found = next((m for ob, m in merged if _same_message(ob, b)), None)
                if found is not None:
                    if r.path.name not in found.sources:
                        found.sources.append(r.path.name)
                    if len(b.text) > len(found.text):
                        found.text = b.text  # versao nao cortada
                    continue
                merged.append((b, StitchedMessage(b.text, b.date, b.time, b.kind, [r.path.name])))
        indexed = [(m, i) for i, (_, m) in enumerate(merged)]
        indexed.sort(key=lambda t: (t[0].date or date.min, t[1]))
        return [m for m, _ in indexed]

    @staticmethod
    def _contradictions(order: list[ScreenshotReading]) -> list[Contradiction]:
        found: list[Contradiction] = []
        for i, ra in enumerate(order):
            for rb in order[i + 1:]:
                for a in ra.bubbles:
                    for b in rb.bubbles:
                        if _same_message(a, b):
                            continue
                        diffs = _aligned_variant(a, b)
                        if diffs:
                            day = a.date or b.date
                            found.append(Contradiction(
                                ra.path.name, rb.path.name, a.text, b.text,
                                f"{day:%d/%m/%Y} {a.time}" if day else f"{a.time}", diffs,
                            ))
        return found

    @staticmethod
    def _gaps(order: list[ScreenshotReading], messages: list[StitchedMessage]) -> list[Gap]:
        gaps = []
        for ra, rb in zip(order, order[1:]):
            shared = any(
                _same_message(a, b) or _aligned_variant(a, b) is not None
                for a in ra.bubbles for b in rb.bubbles
            )
            if shared:
                continue
            last = next((m for m in reversed(messages) if ra.path.name in m.sources), None)
            first = next((m for m in messages if rb.path.name in m.sources), None)
            if last is not None and first is not None:
                gaps.append(Gap(ra.path.name, rb.path.name, last, first))
        return gaps

    @staticmethod
    def _issues(order: list[ScreenshotReading]) -> list[PrintIssue]:
        issues: list[PrintIssue] = []
        named = [r.contact for r in order if r.contact]
        # O contato de referencia e o nome mais longo compativel com a maioria
        # (o cabecalho costuma truncar: "Paulo Ricardo Sou...").
        main_contact = max(
            named, key=lambda c: (sum(names_match(c, o) for o in named), len(c)), default=""
        )
        sizes = Counter(r.size for r in order if r.size)
        main_size = sizes.most_common(1)[0][0] if sizes else None
        for r in order:
            name = r.path.name
            if r.contact and main_contact and not names_match(r.contact, main_contact):
                issues.append(PrintIssue(name, f"Contato diferente dos demais prints: \"{r.contact}\""))
            if main_size and r.size and r.size != main_size and len(order) > 1:
                issues.append(PrintIssue(
                    name, f"Tamanho de imagem diferente ({r.size[0]}x{r.size[1]}; os demais são "
                          f"{main_size[0]}x{main_size[1]}). Pode ser outro aparelho, outro modo de "
                          f"captura (com ou sem a barra de status) ou imagem recortada",
                    severity="info"))
            if r.captured_at:
                dated = [b for b in r.bubbles if b.date and b.time]
                if dated:
                    latest = max(_sort_key(b, 0)[:2] for b in dated)
                    shown = datetime.combine(latest[0], latest[1], tzinfo=r.captured_at.tzinfo)
                    if shown > r.captured_at:
                        issues.append(PrintIssue(
                            name, f"O print foi tirado em {r.captured_at:%d/%m/%Y %H:%M}, antes da "
                                  f"mensagem de {shown:%d/%m/%Y %H:%M} que ele mostra"))
            if r.status_clock and r.captured_at and r.status_clock != f"{r.captured_at:%H:%M}":
                issues.append(PrintIssue(
                    name, f"Relógio do celular no print marca {r.status_clock}, mas o arquivo é "
                          f"de {r.captured_at:%H:%M}"))
        return issues
