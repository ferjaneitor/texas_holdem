from __future__ import annotations
from typing import List, Optional

from cards import Card
from config import STARTING_STACK

"""
player.py
---------
Modelo de un asiento en la mesa (humano o bot).
"""


class Player:
    """
    Representa tanto al jugador humano como a los bots.
    """

    def __init__(self, name: str, is_human: bool = False, difficulty: Optional[str] = None) -> None:
        self.name: str = name
        self.is_human: bool = is_human
        self.difficulty: Optional[str] = difficulty  # "Fácil","Media","Difícil" o None
        self.reset_all()

    def reset_all(self) -> None:
        """
        Reinicia stack y ganancias acumuladas. Llama a new_hand_reset().
        """
        self.stack: int = STARTING_STACK
        self.total_won: int = 0
        self.new_hand_reset()

    def new_hand_reset(self) -> None:
        """
        Limpia estado volátil de la mano actual.
        """
        self.hole: List[Card] = []
        self.folded: bool = False
        self.all_in: bool = False
        self.bet: int = 0
