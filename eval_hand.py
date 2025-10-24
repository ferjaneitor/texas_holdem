from __future__ import annotations
from typing import List, Tuple, Optional
from collections import Counter

from .cards import Card, RANK_TO_INT
from .utils import clamp

"""
eval_hand.py
------------
Lógica de:
- detectar escalera
- evaluar la mejor mano de 5 cartas entre 7+ cartas
- heurística rápida quick_strength() para la IA
"""


def is_straight(vals_desc: List[int]) -> Optional[int]:
    """
    Devuelve la carta alta de una escalera encontrada en 'vals_desc',
    o None si no hay escalera. Considera la rueda A-5.

    vals_desc debería ser una lista de valores de rango tipo [14,13,12,...]
    (puede tener repetidos; aquí se limpia).
    """
    if not vals_desc:
        return None
    v = sorted(set(vals_desc), reverse=True)

    # rueda A-5 (A=14 contado como bajo)
    if {14, 5, 4, 3, 2}.issubset(v):
        return 5

    run = 1
    for i in range(len(v) - 1):
        if v[i] - 1 == v[i + 1]:
            run += 1
            if run >= 5:
                return v[i + 1] + 4
        else:
            run = 1
    return None


def evaluate7(cards: List[Card]) -> Tuple[int, ...]:
    """
    Evalúa la mejor mano de póker de 5 cartas contenida en 7 cartas dadas.
    Retorna una tupla comparable lexicográficamente (más grande = mejor).

    Categorías (primer elemento de la tupla):
        0 = Carta alta
        1 = Pareja
        2 = Doble pareja
        3 = Trío
        4 = Escalera
        5 = Color
        6 = Full House
        7 = Poker
        8 = Escalera de color
    """
    ranks = [RANK_TO_INT[c.rank] for c in cards]
    suits = [c.suit for c in cards]
    rc = Counter(ranks)
    sc = Counter(suits)

    # flush?
    flush_suit: Optional[str] = None
    for s, cnt in sc.items():
        if cnt >= 5:
            flush_suit = s
            break

    uniq = sorted(set(ranks), reverse=True)
    st_high = is_straight(uniq)

    # Escalera de color
    if flush_suit:
        fr = sorted({r for r, s in zip(ranks, suits) if s == flush_suit}, reverse=True)
        sf = is_straight(fr)
        if sf is not None:
            return (8, sf)

    # Poker
    groups = sorted(((cnt, r) for r, cnt in rc.items()), reverse=True)
    if groups[0][0] == 4:
        four = groups[0][1]
        kickers = sorted([r for r in ranks if r != four], reverse=True)
        return (7, four, kickers[0])

    # Full
    trips = [r for c, r in groups if c == 3]
    pairs = [r for c, r in groups if c == 2]
    if trips:
        if len(trips) >= 2:
            return (6, trips[0], trips[1])
        if pairs:
            return (6, trips[0], pairs[0])

    # Color
    if flush_suit:
        franks = sorted(
            [r for r, s in zip(ranks, suits) if s == flush_suit],
            reverse=True
        )[:5]
        return (5, *franks)

    # Escalera
    if st_high is not None:
        return (4, st_high)

    # Trío
    if trips:
        t = trips[0]
        kickers = sorted([r for r in ranks if r != t], reverse=True)[:2]
        return (3, t, *kickers)

    # Doble pareja
    if len(pairs) >= 2:
        p1, p2 = sorted(pairs, reverse=True)[:2]
        kicker = max([r for r in ranks if r != p1 and r != p2])
        return (2, p1, p2, kicker)

    # Pareja
    if len(pairs) == 1:
        p = pairs[0]
        kickers = sorted([r for r in ranks if r != p], reverse=True)[:3]
        return (1, p, *kickers)

    # Carta alta
    highs = sorted(ranks, reverse=True)[:5]
    return (0, *highs)


def quick_strength(hole: List[Card], board: List[Card]) -> float:
    """
    Heurística aproximada de fuerza de mano para la IA.
    Devuelve algo ~[0..1]. Usa evaluate7() si hay suficientes cartas,
    o aproximación preflop si no.
    """
    cards = hole + board
    if len(cards) >= 5:
        score = evaluate7(cards)[0]
        return (score + 0.1) / 9.0

    # Preflop-ish
    a, b = hole
    ar, br = RANK_TO_INT[a.rank], RANK_TO_INT[b.rank]
    hi, lo = max(ar, br), min(ar, br)
    if ar == br:
        s = 0.55 + hi / 20.0
    else:
        s = hi / 20.0 + lo / 40.0

    if a.suit == b.suit:
        s += 0.05

    gap = abs(ar - br)
    if gap == 1:
        s += 0.05
    elif gap == 2:
        s += 0.02

    if board:
        s += 0.05 * len(board)

    return float(clamp(s, 0.0, 0.95))
