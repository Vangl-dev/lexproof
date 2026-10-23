"""Álbum dos prints em ordem cronológica, para anexar a uma peça.

Capa, índice de datas e os prints, quatro por página, cada um com etiqueta de
data/hora e a impressão digital (SHA-256) do arquivo preservado. A ordem e as
datas vêm da leitura do LexProof: o separador de data do próprio print ou,
quando ele não aparece, a sobreposição com os prints vizinhos ou a conversa
exportada.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas

from lexproof.reports import pdf_report as base
from lexproof.reports.analysis_export import long_date
from lexproof.reports.text import local_time, safe_text

W, H = A4
M = 1.6 * cm
DAY_COLORS = ["#1a237e", "#00695c", "#6a1b9a", "#ad1457", "#e65100", "#2e7d32", "#283593", "#4e342e"]
INDEX_ROWS = 34


@dataclass
class AlbumItem:
    path: Path
    first: Optional[tuple[date, Optional[str]]]
    last: Optional[tuple[date, Optional[str]]]
    sha256: str
    label: str = ""
    deduced: bool = False

    @property
    def day(self) -> Optional[date]:
        return self.first[0] if self.first else None

    @property
    def when(self) -> str:
        if not self.first:
            return "data não identificada"
        (d1, t1), (d2, t2) = self.first, self.last or self.first
        start = f"{d1:%d/%m/%Y} {t1 or ''}".strip()
        if d2 != d1:
            return f"{start} a {d2:%d/%m/%Y} {t2 or ''}".strip()
        return f"{start} a {t2}" if t2 and t2 != t1 else start


def _key(it: AlbumItem) -> Any:
    """Grupo do print no índice: "perfil", a data, ou None (sem data)."""
    return "perfil" if it.label else it.day


def _group_label(key: Any) -> str:
    if key == "perfil":
        return "Perfil do contato"
    return long_date(key) if key else "Sem data identificada"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def album_items(d: dict[str, Any]) -> list[AlbumItem]:
    """Prints na ordem do conteúdo, com o período que cada um mostra."""
    st = d.get("stitch")
    checks = {c.reading.path.name: c for c in d.get("screenshot_checks") or []}
    readings = list(st.order) if st is not None and st.order else [c.reading for c in checks.values()]
    items = []
    for r in readings:
        stamps: list[tuple[date, Optional[str]]] = []
        deduced = False
        chk = checks.get(r.path.name)
        for idx, b in enumerate(r.bubbles):
            day = b.date
            if day is None and chk is not None and chk.checks[idx].message is not None:
                day, deduced = chk.checks[idx].message.timestamp.date(), True
            if day is not None:
                stamps.append((day, b.time))
        first = stamps[0] if stamps else None
        last = stamps[-1] if stamps else None
        items.append(AlbumItem(r.path, first, last, _sha256(r.path), deduced=deduced))
    for link in d.get("contacts") or []:
        items.insert(0, AlbumItem(link.profile.path, None, None, _sha256(link.profile.path),
                                  label="Perfil do contato"))
    dated = sorted((i for i in items if i.day and not i.label),
                   key=lambda i: (i.first[0], i.first[1] or ""))
    profiles = [i for i in items if i.label]
    undated = [i for i in items if not i.day and not i.label]
    return profiles + dated + undated


def generate_album(d: dict[str, Any], output_path: Path) -> Optional[Path]:
    items = album_items(d)
    if not items:
        return None
    base._register_fonts()
    font, bold = base._FONT, base._FONT_BOLD
    meta = d.get("metadata", {})
    title = safe_text(meta.get("title", "Caso"))
    seal = d.get("seal")

    days: list[Any] = []
    for it in items:
        key = _key(it)
        if key not in days:
            days.append(key)
    color_of = {day: DAY_COLORS[i % len(DAY_COLORS)] for i, day in enumerate(days)}
    index_pages = max(1, math.ceil(len(days) / INDEX_ROWS))
    first_print_page = 2 + index_pages
    page_of_day: dict[Any, int] = {}
    for n, it in enumerate(items):
        page_of_day.setdefault(_key(it), first_print_page + n // 4)
    total_pages = first_print_page - 1 + math.ceil(len(items) / 4)

    c = rl_canvas.Canvas(str(output_path), pagesize=A4)
    c.setTitle(f"Álbum dos prints - {title}")
    c.setAuthor("LexProof")

    def footer(page: int) -> None:
        c.setFont(font, 7)
        c.setFillColor(base.MUTED)
        c.drawString(M, 1.0 * cm, f"Álbum dos prints · {title}"[:100])
        c.drawRightString(W - M, 1.0 * cm, f"Página {page} de {total_pages}")
        c.setFont(font, 6)
        c.drawCentredString(W / 2, 0.6 * cm, "Cópias dos arquivos preservados pelo LexProof; a impressão digital "
                                             "de cada print permite conferi-lo contra o original.")

    # Capa
    c.setFillColor(base.PRIMARY)
    c.roundRect(M, H - 7.5 * cm, W - 2 * M, 4.6 * cm, 10, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(bold, 26)
    c.drawString(M + 0.8 * cm, H - 4.6 * cm, "ÁLBUM DOS PRINTS")
    c.setFont(font, 12)
    c.drawString(M + 0.8 * cm, H - 5.6 * cm, "em ordem cronológica")
    c.drawString(M + 0.8 * cm, H - 6.5 * cm, title[:70])
    dated = [i for i in items if i.day]
    rows = [
        ("Prints", str(len(items))),
        ("Período", f"{dated[0].day:%d/%m/%Y} a {max(i.last[0] for i in dated):%d/%m/%Y}" if dated else "-"),
        ("Dias", str(len([x for x in days if isinstance(x, date)]))),
        ("Carimbo de tempo", local_time(seal.timestamp.gen_time, with_utc=False)
         if seal is not None and seal.timestamp is not None else "não obtido"),
        ("Gerado em", local_time(datetime.now(timezone.utc), with_utc=False)),
    ]
    y = H - 9.2 * cm
    for k, v in rows:
        c.setFillColor(base.MUTED)
        c.setFont(bold, 9)
        c.drawString(M, y, k)
        c.setFillColor(base.INK)
        c.setFont(font, 10)
        c.drawString(M + 4.5 * cm, y, v)
        y -= 0.75 * cm
    c.setFont(font, 8.5)
    c.setFillColor(base.MUTED)
    text = c.beginText(M, y - 0.6 * cm)
    for line in (
        "Cada print traz a data e a hora das mensagens que mostra, lidas no separador de data do",
        "próprio print. Datas marcadas com * foram deduzidas pela conversa exportada ou pelos prints",
        "vizinhos, porque o separador não aparece no print. A integridade e a conferência de cada",
        "mensagem estão no Relatório de Preservação e Integridade do mesmo caso.",
    ):
        text.textLine(line)
    c.drawText(text)
    footer(1)
    c.showPage()

    # Índice
    for p in range(index_pages):
        c.setFont(bold, 16)
        c.setFillColor(base.PRIMARY)
        c.drawString(M, H - 2.4 * cm, "Índice por data" + (" (continuação)" if p else ""))
        y = H - 3.6 * cm
        for day in days[p * INDEX_ROWS:(p + 1) * INDEX_ROWS]:
            n = sum(1 for it in items if (_key(it)) == day)
            label = _group_label(day)
            c.setFillColor(colors.HexColor(color_of[day]))
            c.rect(M, y - 0.05 * cm, 0.25 * cm, 0.4 * cm, fill=1, stroke=0)
            c.setFillColor(base.INK)
            c.setFont(font, 9.5)
            c.drawString(M + 0.5 * cm, y, f"{label}  ({n} print{'s' if n > 1 else ''})")
            c.drawRightString(W - M, y, f"página {page_of_day[day]}")
            c.setStrokeColor(base.LINE)
            c.line(M + 0.5 * cm, y - 0.15 * cm, W - M, y - 0.15 * cm)
            y -= 0.62 * cm
        footer(2 + p)
        c.showPage()

    # Prints, 2 x 2 por página
    cell_w = (W - 2 * M - 0.6 * cm) / 2
    cell_h = (H - 2 * M - 1.2 * cm) / 2
    page = first_print_page
    for start in range(0, len(items), 4):
        for k, it in enumerate(items[start:start + 4]):
            col, row = k % 2, k // 2
            x = M + col * (cell_w + 0.6 * cm)
            top = H - M - row * (cell_h + 0.6 * cm)
            day = _key(it)
            c.setFillColor(colors.HexColor(color_of[day]))
            c.roundRect(x, top - 0.75 * cm, cell_w, 0.75 * cm, 4, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont(bold, 8.5)
            head = _group_label(day)
            c.drawString(x + 0.25 * cm, top - 0.5 * cm, f"{start + k + 1}. {head}"[:58])
            c.setFillColor(base.INK)
            c.setFont(font, 7.5)
            when = "" if it.label else it.when + (" *" if it.deduced else "")
            c.drawString(x, top - 1.15 * cm, when[:70])
            c.setFillColor(base.MUTED)
            c.setFont(font, 6.5)
            c.drawString(x, top - 1.5 * cm, f"{it.path.name}"[:64])
            c.drawString(x, top - 1.8 * cm, f"SHA-256 {it.sha256[:32]}…")
            try:
                img = ImageReader(str(it.path))
                iw, ih = img.getSize()
                box_h = cell_h - 2.1 * cm
                scale = min(cell_w / iw, box_h / ih)
                dw, dh = iw * scale, ih * scale
                ix = x + (cell_w - dw) / 2
                iy = top - 2.0 * cm - dh
                c.drawImage(img, ix, iy, dw, dh)
                c.setStrokeColor(base.LINE)
                c.rect(ix, iy, dw, dh, fill=0, stroke=1)
            except Exception:
                c.drawString(x, top - 2.5 * cm, "imagem indisponível")
        footer(page)
        c.showPage()
        page += 1
    c.save()
    return output_path
