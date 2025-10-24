from __future__ import annotations
from typing import Tuple

"""
config.py
---------
Constantes de configuración del juego: tamaños de ventana, colores,
ciegas, tiempos, etiquetas de dificultad, etc.
"""

# Window / render
WIDTH: int = 1280
HEIGHT: int = 720
FPS: int = 60

TABLE_COLOR: Tuple[int, int, int] = (18, 80, 56)
CARD_W: int = 76
CARD_H: int = 104
FOOTER_H: int = 110
PLAYER_Y: int = HEIGHT - FOOTER_H - CARD_H - 28
BOT_MAX_Y: int = PLAYER_Y - CARD_H - 60

# Economía
STARTING_STACK: int = 500
SMALL_BLIND: int = 10
BIG_BLIND: int = 20
MAX_BOTS: int = 7

ARCADE_REBUY: bool = True       # recompra del humano si bustea
AUTO_REBUY_BOTS: bool = True    # bots < BB se recargan al inicio de mano

# Tiempos (ms)
BOT_THINK_MS: int = 900         # "pensando..."
BOT_POST_ACT_PAUSE: int = 800   # pausa breve tras acción bot
BANNER_MS: int = 1800           # banner de acción en pantalla

# Dificultad bots
EASY: str = "Fácil"
MED: str = "Media"
HARD: str = "Difícil"
