from __future__ import annotations

import pygame
import math

from config import WIDTH, HEIGHT, FOOTER_H, CARD_W, MAX_BOTS, EASY, MED, HARD
from utils import clamp
from ui import Button



class LobbyMixin:
    # --- lobby buttons ---
    def make_lobby_buttons(self) -> None:
        self.buttons = []

        def minus_bots() -> None:
            self.num_bots = int(clamp(self.num_bots - 1, 1, MAX_BOTS))

        def plus_bots() -> None:
            self.num_bots = int(clamp(self.num_bots + 1, 1, MAX_BOTS))

        def diff_prev() -> None:
            order = [EASY, MED, HARD]
            self.bot_difficulty = order[
                (order.index(self.bot_difficulty) - 1) % len(order)
            ]

        def diff_next() -> None:
            order = [EASY, MED, HARD]
            self.bot_difficulty = order[
                (order.index(self.bot_difficulty) + 1) % len(order)
            ]

        def start() -> None:
            self.setup_players()
            self.start_hand()

        self.buttons.append(Button((WIDTH // 2 - 240, 340, 56, 56), "-", minus_bots))
        self.buttons.append(Button((WIDTH // 2 + 184, 340, 56, 56), "+", plus_bots))
        self.buttons.append(Button((WIDTH // 2 - 240, 420, 56, 56), "<", diff_prev))
        self.buttons.append(Button((WIDTH // 2 + 184, 420, 56, 56), ">", diff_next))
        self.buttons.append(Button((WIDTH // 2 - 140, 520, 280, 64), "Empezar", start))

    def make_continue_button(self, label: str = "Continuar") -> None:
        def cb_continue() -> None:
            self.continue_after_pause()

        def cb_menu() -> None:
            self.return_to_lobby()

        self.buttons = [
            Button(
                (WIDTH // 2 - 100, HEIGHT - FOOTER_H + 18, 200, 48),
                label,
                cb_continue,
            ),
            Button(
                (WIDTH // 2 + 320, HEIGHT - FOOTER_H + 18, 150, 48),
                "Menu",
                cb_menu,
            ),
        ]

    def return_to_lobby(self) -> None:
        self.state = "LOBBY"
        self.keypad_visible = False
        self.banner_text = ""
        self.banner_timer = 0.0
        self.log = []
        self.last_winner_text = ""
        self.make_lobby_buttons()

    # --- dibujo de la pantalla de lobby ---
    def draw_lobby(self) -> None:
        self.draw_gradient_bg()

        title = self.titlefont.render("Texas Hold’em", True, (240, 240, 240))
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 120)))

        cx, cy = WIDTH // 2, 220
        gap = CARD_W + 18
        for i in range(5):
            dx = math.sin(pygame.time.get_ticks() * 0.0012 + i * 0.6) * 6
            dy = math.cos(pygame.time.get_ticks() * 0.0014 + i * 0.4) * 3
            self.draw_card((cx - 2 * gap + i * gap + int(dx), cy + int(dy)))

        lbl1 = self.midfont.render("Bots en mesa", True, (220, 220, 220))
        self.screen.blit(lbl1, lbl1.get_rect(center=(WIDTH // 2, 350)))
        val1 = self.bigfont.render(str(self.num_bots), True, (255, 255, 255))
        self.screen.blit(val1, val1.get_rect(center=(WIDTH // 2, 380)))

        lbl2 = self.midfont.render("Dificultad", True, (220, 220, 220))
        self.screen.blit(lbl2, lbl2.get_rect(center=(WIDTH // 2, 430)))
        val2 = self.bigfont.render(self.bot_difficulty, True, (255, 255, 255))
        self.screen.blit(val2, val2.get_rect(center=(WIDTH // 2, 460)))

        for b in self.buttons:
            b.draw(self.screen, self.font, self.midfont)
