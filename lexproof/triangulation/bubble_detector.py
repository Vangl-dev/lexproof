"""Localiza os baloes de mensagem num print do WhatsApp pela cor de fundo.

Ler o print inteiro com OCR e deduzir os baloes pelo texto falha quando o
horario pequeno do balao sai ilegivel (comum no tema escuro): o balao "nao
fecha" e o texto dele se junta ao do seguinte. Aqui os baloes sao recortados
pela cor de preenchimento, que e uniforme (verde para as enviadas, cinza ou
branco para as recebidas, outra cor para avisos e separadores de data), e cada
um e lido separadamente.

Se o papel de parede for uma foto, ou o layout for outro, nenhum balao e
encontrado e o leitor volta para a leitura por linhas.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

# Diferenca maxima por canal entre pixels vizinhos de uma mesma faixa lisa
_RUN_STEP = 6
# Faixa lisa minima (fracao da largura) para a cor contar como preenchimento
_MIN_RUN = 0.15
# Distancia maxima (por canal) para um pixel pertencer a uma cor de preenchimento
_COLOR_TOL = 12
# Balao minimo (fracao da largura e da altura do print)
_MIN_WIDTH = 0.12
_MIN_HEIGHT = 0.018
# Separador de data e aviso do sistema ficam centralizados
_CENTER_TOL = 0.04


@dataclass
class BubbleBox:
    """Retangulo de um balao no print (coordenadas da imagem inteira)."""

    left: int
    top: int
    right: int
    bottom: int
    color: tuple[int, int, int]
    # "left" (recebida), "right" (enviada) ou "center" (data ou aviso do sistema)
    side: str
    cut_top: bool = False
    cut_bottom: bool = False
    # Cartoes dentro do balao: previa de link, mensagem citada, miniatura de midia
    inner: list[tuple[int, int, int, int]] = field(default_factory=list)

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def dark(self) -> bool:
        r, g, b = self.color
        return 0.299 * r + 0.587 * g + 0.114 * b < 110


def _dist(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    return max(abs(int(x) - int(y)) for x, y in zip(a, b))


def _margin(region: np.ndarray) -> np.ndarray:
    """Faixa da borda esquerda, onde so ha papel de parede (baloes comecam depois)."""
    return region[:, : max(4, int(region.shape[1] * 0.015))].reshape(-1, 3)


def _background(region: np.ndarray) -> tuple[int, int, int]:
    """Cor do papel de parede: a mais comum na faixa da borda esquerda."""
    strip = _margin(region) // 4 * 4
    color, _ = Counter(map(tuple, strip.tolist())).most_common(1)[0]
    return tuple(int(c) + 2 for c in color)  # type: ignore[return-value]


def _is_wallpaper(region: np.ndarray, color: tuple[int, int, int]) -> bool:
    """Cor presente na borda da tela: e do papel de parede (desenhos), nao de balao."""
    near = np.abs(_margin(region) - np.array(color, np.int16)).max(axis=1) <= _COLOR_TOL // 2
    return float(near.mean()) > 0.15


def _fill_colors(region: np.ndarray, bg: tuple[int, int, int]) -> list[tuple[int, int, int]]:
    """Cores que formam faixas lisas longas em varias linhas (preenchimento de balao)."""
    h, w, _ = region.shape
    min_run = int(w * _MIN_RUN)
    counts: Counter = Counter()
    sums: dict[tuple[int, int, int], np.ndarray] = {}
    for y in range(0, h, 2):
        row = region[y]
        breaks = np.flatnonzero(np.abs(np.diff(row, axis=0)).max(axis=1) > _RUN_STEP) + 1
        edges = np.concatenate(([0], breaks, [w]))
        lengths = np.diff(edges)
        for i in np.flatnonzero(lengths >= min_run):
            mid = row[(edges[i] + edges[i + 1]) // 2]
            key = tuple(int(c) for c in mid // 6)
            counts[key] += 1
            sums[key] = sums.get(key, 0) + mid.astype(np.int64)  # int16 estoura em balao alto
    colors: list[tuple[tuple[int, int, int], int]] = []
    for key, n in counts.most_common():
        mean = tuple(int(c) for c in sums[key] / n)
        for i, (kept, kept_n) in enumerate(colors):
            if _dist(kept, mean) <= 8:
                colors[i] = (kept, kept_n + n)
                break
        else:
            colors.append((mean, n))  # type: ignore[arg-type]
    return [c for c, n in colors
            if n >= 6 and _dist(c, bg) > 8 and not _is_wallpaper(region, c)]


def detect_bubbles(rgb: np.ndarray, top: int, bottom: int) -> list[BubbleBox]:
    """Baloes entre o cabecalho (top) e o campo de digitacao (bottom).

    Retorna lista vazia quando nao reconhece o layout.
    """
    import cv2

    h_img, w = rgb.shape[:2]
    region = rgb[top:bottom].astype(np.int16)
    if region.size == 0:
        return []
    bg = _background(region)
    kernel = np.ones((5, 15), np.uint8)
    found: list[BubbleBox] = []
    for color in _fill_colors(region, bg):
        mask = (np.abs(region - np.array(color, np.int16)).max(axis=2) <= _COLOR_TOL).astype(np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        n, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        for i in range(1, n):
            x, y, bw, bh, area = stats[i]
            if bw < w * _MIN_WIDTH or bh < h_img * _MIN_HEIGHT:
                continue
            # Balao e um retangulo quase cheio (so o texto fura); desenho do
            # papel de parede e ralo.
            if area < 0.5 * bw * bh:
                continue
            found.append(BubbleBox(
                left=int(x), top=int(y) + top, right=int(x + bw), bottom=int(y + bh) + top,
                color=color, side="",
            ))
    bubbles = _nest(_merge_split(_nest(_dedupe(found)), rgb, bg))
    for b in bubbles:
        _extend_thin_edges(rgb, b, top, bottom)
        b.cut_top = b.top <= top + 3
        b.cut_bottom = b.bottom >= bottom - 3
        measured = _own_color(rgb, b)
        # A medida pode cair num cartao interno (previa de link no topo); so
        # ajusta o tom quando fica perto da cor em que o balao foi achado.
        if _dist(measured, b.color) <= 12:
            b.color = measured
        # Balao inteiro tem cantos arredondados; cortado pela borda da tela ou
        # pela barra de digitacao, cantos retos. (O "rabinho" deixa um canto de
        # cima reto, por isso exige os dois.)
        b.cut_top = b.cut_top or _square_corners(rgb, b, b.top + 1)
        b.cut_bottom = b.cut_bottom or _square_corners(rgb, b, b.bottom - 4)
        for card in _cards(rgb, b):
            if not any(_rect_overlap(card, other) > 0.8 for other in b.inner):
                b.inner.append(card)
        b.side = _side(b, w)
    return sorted(bubbles, key=lambda b: b.top)


def _rect_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    iw = min(a[2], b[2]) - max(a[0], b[0])
    ih = min(a[3], b[3]) - max(a[1], b[1])
    if iw <= 0 or ih <= 0:
        return 0.0
    return iw * ih / min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))


def _extend_thin_edges(rgb: np.ndarray, b: BubbleBox, top: int, bottom: int) -> None:
    """Recupera a faixa fina do balao acima ou abaixo de um cartao interno.

    Com uma previa de link no topo, sobra so uma faixa de poucos pixels da cor
    do balao acima dela, baixa demais para virar componente. Sem ela o topo do
    balao parece reto (cortado).
    """
    def same_width(y: int) -> bool:
        edges = _row_edges(rgb, b, y)
        return edges is not None and edges[1] - edges[0] >= b.width * 0.8

    for _ in range(24):
        if b.top - 1 <= top or not same_width(b.top - 1):
            break
        b.top -= 1
    for _ in range(24):
        if b.bottom + 1 >= bottom or not same_width(b.bottom):
            break
        b.bottom += 1


def _row_edges(rgb: np.ndarray, b: BubbleBox, y: int) -> Optional[tuple[int, int]]:
    """Primeira e ultima coluna com a cor do balao na linha y (5 pixels seguidos)."""
    if not 0 <= y < rgb.shape[0]:
        return None
    row = rgb[y, b.left:b.right].astype(np.int16)
    mask = (np.abs(row - np.array(b.color, np.int16)).max(axis=1) <= 8).astype(np.int8)
    runs = np.convolve(mask, np.ones(5, np.int8), mode="valid") == 5
    xs = np.flatnonzero(runs)
    if len(xs) == 0 or xs[-1] + 5 - xs[0] < b.width * 0.5:
        return None
    return int(xs[0]), int(xs[-1]) + 5


def _square_corners(rgb: np.ndarray, b: BubbleBox, y: int) -> bool:
    """A ponta do balao na altura y e reta (corte), nao arredondada.

    No canto arredondado a borda do balao recua alguns pixels perto da ponta;
    no corte reto, nao. Compara a borda perto da ponta com a borda um pouco
    para dentro, usando a borda real de cada linha (o "rabinho" do balao e
    tracos do papel de parede alargam o retangulo).

    Em cima o rabinho deixa um dos lados reto, por isso os dois precisam
    estar retos. Embaixo nao ha rabinho, mas a barra de digitacao esfumaca
    a borda de um dos lados; basta um lado reto.
    """
    top_side = y < b.top + b.height // 2
    inward = 1 if top_side else -1
    ref = _row_edges(rgb, b, y + inward * max(14, b.width // 30))
    if ref is None:
        return False
    for tip_y in (y, y + inward):
        tip = _row_edges(rgb, b, tip_y)
        if tip is None:
            return False
        left, right = abs(tip[0] - ref[0]) <= 2, abs(tip[1] - ref[1]) <= 2
        if not ((left and right) if top_side else (left or right)):
            return False
    return True


def _own_color(rgb: np.ndarray, b: BubbleBox) -> tuple[int, int, int]:
    """Cor do balao, medida nas faixas sem texto: respiro de cima e de baixo, no meio.

    A borda esquerda nao serve: o "rabinho" do balao e o canto arredondado
    misturam o papel de parede.
    """
    x0, x1 = b.left + b.width // 4, b.right - b.width // 4
    bands = []
    if not b.cut_top:
        bands.append(rgb[b.top + 3:b.top + 8, x0:x1])
    if not b.cut_bottom:
        bands.append(rgb[b.bottom - 8:b.bottom - 3, b.left + b.width // 8:b.left + b.width // 2])
    pixels = np.concatenate([x.reshape(-1, 3) for x in bands]) if bands else np.empty((0, 3))
    if len(pixels) == 0:
        return b.color
    key, _ = Counter(map(tuple, (pixels // 3).tolist())).most_common(1)[0]
    near = pixels[(pixels // 3 == np.array(key)).all(axis=1)]
    return tuple(int(c) for c in near.mean(axis=0))  # type: ignore[return-value]


def _cards(rgb: np.ndarray, b: BubbleBox) -> list[tuple[int, int, int, int]]:
    """Faixas do balao que nao sao texto sobre o fundo do balao.

    Previa de link e mensagem citada tem um tom proximo do balao (quase igual
    para o detector); miniatura e foto nao tem a cor do balao. Numa linha de
    texto a maior parte dos pixels continua com a cor do balao; numa faixa de
    cartao, nao.
    """
    pad = max(6, b.width // 40)
    crop = rgb[b.top:b.bottom, b.left + pad:b.right - pad].astype(np.int16)
    if crop.size == 0:
        return []
    own = (np.abs(crop - np.array(b.color, np.int16)).max(axis=2) <= 5).mean(axis=1)
    min_rows = max(20, int(rgb.shape[0] * 0.012))
    cards: list[tuple[int, int, int, int]] = []
    start = None
    for y, frac in enumerate(np.append(own, 1.0)):
        if frac < 0.2 and start is None:
            start = y
        elif frac >= 0.2 and start is not None:
            if y - start >= min_rows:
                cards.append((b.left + pad, b.top + start, b.right - pad, b.top + y))
            start = None
    return cards


def _side(b: BubbleBox, w: int) -> str:
    center = (b.left + b.right) / 2
    if abs(center - w / 2) < w * _CENTER_TOL and b.left > w * 0.06 and b.right < w * 0.94:
        return "center"
    return "left" if b.left < w - b.right else "right"


def _merge_split(boxes: list[BubbleBox], rgb: np.ndarray, bg: tuple[int, int, int]) -> list[BubbleBox]:
    """Junta pedacos do mesmo balao.

    Dois casos: (1) a previa de um link ou a mensagem citada ocupa quase toda a
    largura do balao, a borda fina que sobra some na limpeza e o balao vira dois
    pedacos da mesma cor; (2) a miniatura de um documento ou foto tem outra cor
    e fica colada ao balao. Entre dois baloes diferentes ha papel de parede;
    dentro do mesmo balao, nao. Pedacos com outro balao no meio nunca se juntam.
    """
    boxes = sorted(boxes, key=lambda b: b.top)
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                if _belongs_together(a, b, boxes, rgb, bg):
                    _absorb(a, b)
                    boxes.remove(b)
                    changed = True
                    break
            if changed:
                break
    return boxes


def _contains_x(outer: BubbleBox, inner: BubbleBox, slack: int = 10) -> bool:
    return outer.left - slack <= inner.left and inner.right <= outer.right + slack


def _belongs_together(a: BubbleBox, b: BubbleBox, boxes: list[BubbleBox], rgb: np.ndarray,
                      bg: tuple[int, int, int]) -> bool:
    upper, lower = (a, b) if a.top <= b.top else (b, a)
    gap = lower.top - upper.bottom
    if gap < -4:
        return False
    same = _dist(a.color, b.color) <= 8
    if same:
        if abs(a.left - b.left) > 10 or abs(a.right - b.right) > 10 or gap > rgb.shape[0] * 0.25:
            return False
    elif gap > 12 or not (_contains_x(a, b) or _contains_x(b, a)):
        return False
    span = BubbleBox(min(a.left, b.left), upper.bottom, max(a.right, b.right), lower.top, a.color, "")
    for c in boxes:
        if c is a or c is b:
            continue
        between = c.top < lower.top and c.bottom > upper.bottom
        overlaps_x = c.right > span.left and c.left < span.right
        if between and overlaps_x and not _contains_x(span, c):
            return False  # outro balao no meio
    return _background_fraction(rgb, span.left, span.top, span.right, span.bottom, bg) < 0.3


def _absorb(host: BubbleBox, piece: BubbleBox) -> None:
    """Une piece a host; a parte mais estreita de outra cor vira cartao interno."""
    if _dist(host.color, piece.color) > 8:
        card, main = (piece, host) if piece.width <= host.width else (host, piece)
        host.inner.append((card.left, card.top, card.right, card.bottom))
        host.color = main.color
    host.inner.extend(piece.inner)
    host.left, host.right = min(host.left, piece.left), max(host.right, piece.right)
    host.top, host.bottom = min(host.top, piece.top), max(host.bottom, piece.bottom)


def _background_fraction(rgb: np.ndarray, left: int, top: int, right: int, bottom: int,
                         bg: tuple[int, int, int]) -> float:
    if bottom <= top:
        return 0.0
    band = rgb[top:bottom, left + 4:right - 4].astype(np.int16)
    if band.size == 0:
        return 0.0
    near = np.abs(band - np.array(bg, np.int16)).max(axis=2) <= 10
    return float(near.mean())


def _overlap(a: BubbleBox, b: BubbleBox) -> float:
    """Fracao do menor retangulo coberta pela intersecao."""
    iw = min(a.right, b.right) - max(a.left, b.left)
    ih = min(a.bottom, b.bottom) - max(a.top, b.top)
    if iw <= 0 or ih <= 0:
        return 0.0
    return iw * ih / min(a.width * a.height, b.width * b.height)


def _dedupe(boxes: list[BubbleBox]) -> list[BubbleBox]:
    """Tons vizinhos da mesma cor acham o mesmo balao; fica um so."""
    kept: list[BubbleBox] = []
    for b in sorted(boxes, key=lambda b: -(b.width * b.height)):
        if any(_overlap(b, k) > 0.85 and abs(b.width - k.width) <= 12 for k in kept):
            continue
        kept.append(b)
    return kept


def _nest(boxes: list[BubbleBox]) -> list[BubbleBox]:
    """Retangulos dentro de um balao nao sao baloes.

    De outra cor, sao cartoes internos (previa de link, citacao, miniatura); de
    tom parecido, sao o mesmo balao achado de novo e saem.
    """
    outer: list[BubbleBox] = []
    for b in sorted(boxes, key=lambda b: -(b.width * b.height)):
        host = next((o for o in outer if o.left - 4 <= b.left and b.right <= o.right + 4
                     and o.top - 4 <= b.top and b.bottom <= o.bottom + 4), None)
        if host is None:
            outer.append(b)
        elif _dist(host.color, b.color) > 12:
            host.inner.append((b.left, b.top, b.right, b.bottom))
    return outer
