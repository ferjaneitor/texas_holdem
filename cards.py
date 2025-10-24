from __future__ import annotations
import random
from typing import List, Dict, Tuple

"""
cards.py
--------
Representación de cartas y baraja.
También definimos rankings y colores de palos.
"""

SUITS: List[str] = ['♠', '♥', '♦', '♣']

SUIT_COLORS: Dict[str, Tuple[int, int, int]] = {
    '♠': (230, 230, 230),
    '♣': (230, 230, 230),
    '♥': (230, 80, 90),
    '♦': (230, 80, 90),
}

RANKS: List[str] = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']

# Mapeo a fuerza numérica de cada rango (A alto = 14)
# Nota: está hecho como en tu código original para evaluación de manos
RANK_TO_INT: Dict[str, int] = {r: i for i, r in enumerate('..23456789TJQKA')}


class Card:
    """
    Carta estándar de póker.

    Attributes:
        rank: '2'..'9','T','J','Q','K','A'
        suit: '♠','♥','♦','♣'
    """
    __slots__ = ("rank", "suit")

    def __init__(self, rank: str, suit: str) -> None:
        self.rank: str = rank
        self.suit: str = suit

    def __repr__(self) -> str:
        return f"{self.rank}{self.suit}"


class Deck:
    """
    Baraja de 52 cartas. Se baraja automáticamente al crearla.
    """

    def __init__(self) -> None:
        self.cards: List[Card] = [Card(r, s) for s in SUITS for r in RANKS]
        random.shuffle(self.cards)

    def deal(self, n: int = 1) -> List[Card]:
        """
        Roba n cartas de la parte superior de la baraja.

        Args:
            n: cuántas cartas robar.

        Returns:
            Lista de n Card.
        """
        out = self.cards[:n]
        self.cards = self.cards[n:]
        return out
