# game_logic/game.py
from __future__ import annotations

from typing import List, Optional, Set
import sys
import pygame

from config import WIDTH, HEIGHT, FPS, MED, BIG_BLIND  # ⬅ sin punto
from cards import Deck, Card                           # ⬅ sin punto
from player import Player                              # ⬅ sin punto
from ui import Button                                  # ⬅ sin punto

from .logger import LoggerMixin
from .lobby import LobbyMixin
from .keypad import KeypadMixin
from .betting import BettingMixin
from .showdown import ShowdownMixin
from .renderer import RendererMixin
from .state import StateMixin


class Game(
    LoggerMixin,
    LobbyMixin,
    KeypadMixin,
    BettingMixin,
    ShowdownMixin,
    RendererMixin,
    StateMixin,
):
    """
    Controlador principal del juego:
    - loop pygame
    - flujo de rondas
    - apuestas humano/bots
    - HUD/render
    """

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Texas Hold’em")

        # Pygame core
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(pygame.font.get_default_font(), 18)
        self.midfont = pygame.font.SysFont(
            pygame.font.get_default_font(), 20, bold=True
        )
        self.bigfont = pygame.font.SysFont(
            pygame.font.get_default_font(), 28, bold=True
        )
        self.titlefont = pygame.font.SysFont(
            pygame.font.get_default_font(), 44, bold=True
        )

        # Estado general
        self.state: str = "LOBBY"
        self.num_bots: int = 4
        self.bot_difficulty: str = MED

        self.players: List[Player] = []
        self.hero_index: int = 0
        self.dealer_index: int = 0

        self.buttons: List[Button] = []

        # keypad modal
        self.keypad_visible: bool = False
        self.keypad_value: int = 0
        self.keypad_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)

        # ronda / board
        self.round_index: int = 0
        self.deck: Optional[Deck] = None
        self.board_all: List[Card] = []
        self.board_visible_count: int = 0
        self.board: List[Card] = []

        # apuestas
        self.pot: int = 0
        self.current_bet: int = 0
        self.current_player: int = 0
        self.last_raiser: Optional[int] = None
        self.last_raise_size: int = BIG_BLIND

        # calle actual
        self.first_to_act: int = 0
        self.acted_set: Set[int] = set()
        self.had_aggression: bool = False
        self.pending_to_act: Set[int] = set()

        # feedback visual / timers
        self.bot_think_timer: float = 0.0
        self.bot_pause_timer: float = 0.0
        self.banner_text: str = ""
        self.banner_timer: float = 0.0
        self.log: List[str] = []
        self.last_winner_text: str = ""
        self._advancing: bool = False  # para proteger proceed_round

        self.make_lobby_buttons()

    # --- main loop ---
    def run(self) -> None:
        while True:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                for b in list(self.buttons):
                    b.handle(event)

            self.update()
            self.draw()
