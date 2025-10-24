"""
texas_holdem
============
Paquete del minijuego Texas Hold'em con pygame.

Este paquete expone las piezas principales para que puedan
importarse desde fuera si quieres reutilizar lógica sin abrir la UI.
"""

from .config import (
    WIDTH, HEIGHT, FPS,
    TABLE_COLOR, CARD_W, CARD_H, FOOTER_H, PLAYER_Y, BOT_MAX_Y,
    STARTING_STACK, SMALL_BLIND, BIG_BLIND, MAX_BOTS,
    ARCADE_REBUY, AUTO_REBUY_BOTS,
    BOT_THINK_MS, BOT_POST_ACT_PAUSE, BANNER_MS,
    EASY, MED, HARD,
)

from .utils import clamp, setup_logging
from .cards import Card, Deck, SUITS, RANKS, RANK_TO_INT
from .eval_hand import evaluate7, quick_strength
from .player import Player
from .ai import bot_decision
from .game import Game
__all__ = [
    "WIDTH", "HEIGHT", "FPS",
    "TABLE_COLOR", "CARD_W", "CARD_H", "FOOTER_H", "PLAYER_Y", "BOT_MAX_Y",
    "STARTING_STACK", "SMALL_BLIND", "BIG_BLIND", "MAX_BOTS",
    "ARCADE_REBUY", "AUTO_REBUY_BOTS",
    "BOT_THINK_MS", "BOT_POST_ACT_PAUSE", "BANNER_MS",
    "EASY", "MED", "HARD",
    "clamp", "setup_logging",
    "Card", "Deck", "SUITS", "RANKS", "RANK_TO_INT",
    "evaluate7", "quick_strength",
    "Player",
    "bot_decision",
    "Game",
]