from __future__ import annotations

from typing import List, Tuple, Optional
import math
import pygame

from config import (
    WIDTH, HEIGHT, FPS,
    TABLE_COLOR, CARD_W, CARD_H,
    FOOTER_H, PLAYER_Y, BOT_MAX_Y, BIG_BLIND,
)
from cards import Card
from ui import Button

class RendererMixin:
    # --- dibujo / render ---
    def seat_positions(self) -> List[Tuple[int, int]]:
        pos = [(WIDTH // 2, PLAYER_Y)]
        nb = len(self.players) - 1 if self.players else self.num_bots
        cx, cy = WIDTH // 2, HEIGHT // 2 - 20
        rx, ry = 420, 210
        if nb > 0:
            a0 = math.radians(190)
            a1 = math.radians(350)
            for k in range(nb):
                t = (k + 1) / (nb + 1)
                ang = a0 + (a1 - a0) * t
                x = int(cx + rx * math.cos(ang))
                y = int(cy + ry * math.sin(ang))
                y = min(y, BOT_MAX_Y)
                pos.append((x, y))
        return pos

    def draw_gradient_bg(self) -> None:
        for i in range(0, HEIGHT, 4):
            t = i / HEIGHT
            c = (int(14 + 20 * t), int(18 + 24 * t), int(22 + 30 * t))
            pygame.draw.rect(self.screen, c, (0, i, WIDTH, 4))

    def draw_table(self) -> None:
        self.draw_gradient_bg()
        pygame.draw.ellipse(
            self.screen, TABLE_COLOR, (160, 46, WIDTH - 320, HEIGHT - 150)
        )
        pygame.draw.ellipse(
            self.screen,
            (10, 40, 28),
            (150, 36, WIDTH - 300, HEIGHT - 130),
            8,
        )

    def draw_card(self, topleft: Tuple[int, int], card: Optional[Card] = None) -> None:
        x, y = topleft
        rect = pygame.Rect(x, y, CARD_W, CARD_H)
        pygame.draw.rect(
            self.screen,
            (240, 240, 240) if card else (32, 46, 58),
            rect,
            border_radius=10,
        )
        pygame.draw.rect(self.screen, (200, 200, 200), rect, 2, border_radius=10)
        if card:
            rtxt = self.midfont.render(card.rank, True, (20, 20, 20))
            self.screen.blit(rtxt, (x + 8, y + 6))
            stxt = self.midfont.render(
                card.suit,
                True,
                (230, 80, 90) if card.suit in ("♥", "♦") else (230, 230, 230),
            )
            self.screen.blit(stxt, (x + CARD_W - 28, y + CARD_H - 34))

    def draw_hand_cards(
        self, center: Tuple[int, int], cards: List[Card], face_up: bool
    ) -> None:
        cx, cy = center
        left = (cx - CARD_W - 10, cy - CARD_H // 2)
        right = (cx + 10, cy - CARD_H // 2)
        self.draw_card(left, cards[0] if face_up else None)
        self.draw_card(right, cards[1] if face_up else None)

    def draw_board(self) -> None:
        cx, cy = WIDTH // 2, HEIGHT // 2 - 28
        gap = CARD_W + 18
        start_x = cx - 2 * gap
        y = cy - CARD_H // 2
        for i in range(5):
            if i < self.board_visible_count:
                self.draw_card((start_x + i * gap, y), self.board_all[i])
            else:
                self.draw_card((start_x + i * gap, y), None)

    def draw_players(self) -> None:
        seats = self.seat_positions()
        for i, p in enumerate(self.players):
            sx, sy = seats[i]
            col = (250, 250, 250) if p.is_human else (210, 210, 210)
            if p.folded:
                col = (120, 120, 120)

            pygame.draw.circle(self.screen, col, (sx, sy), 38)
            pygame.draw.circle(self.screen, (60, 60, 60), (sx, sy), 38, 2)

            if self.state in ("BETTING", "BOT_PAUSE") and i == self.current_player:
                pygame.draw.circle(
                    self.screen, (255, 204, 0), (sx, sy), 44, 4
                )

            name = self.midfont.render(p.name, True, (12, 12, 12))
            self.screen.blit(name, name.get_rect(center=(sx, sy - 56)))

            if not p.is_human:
                stack = self.font.render(
                    f"Stack: $ {p.stack}", True, (12, 12, 12)
                )
                self.screen.blit(stack, stack.get_rect(center=(sx, sy + 44)))

            bet = self.font.render(f"Apuesta: {p.bet}", True, (12, 12, 12))
            self.screen.blit(bet, bet.get_rect(center=(sx, sy + 62)))
            won = self.font.render(f"Ganado: {p.total_won}", True, (12, 12, 12))
            self.screen.blit(won, won.get_rect(center=(sx, sy + 80)))

            face_up = p.is_human or (self.state in ("SHOWDOWN", "ENDHAND"))
            if len(p.hole) == 2:
                self.draw_hand_cards((sx, sy - 6), p.hole, face_up)

    def draw_hud(self) -> None:
        pot_txt = self.bigfont.render(f"Pote: {self.pot}", True, (240, 240, 240))
        self.screen.blit(pot_txt, (24, 20))

        names = ["Flop", "Turn", "River", "Showdown"]
        rlabel = (
            names[self.round_index] if self.round_index < len(names) else str(self.round_index)
        )
        r_txt = self.bigfont.render(f"Fase: {rlabel}", True, (240, 240, 240))
        self.screen.blit(r_txt, (24, 56))

        diff_txt = self.font.render(
            f"Dificultad: {self.bot_difficulty}", True, (200, 200, 200)
        )
        self.screen.blit(diff_txt, (24, 80))

        pygame.draw.rect(
            self.screen,
            (24, 30, 38),
            pygame.Rect(0, HEIGHT - FOOTER_H, WIDTH, FOOTER_H),
        )

        if self.state in ("BETTING", "ROUND_PAUSE", "ENDHAND", "SHOWDOWN", "BOT_PAUSE"):
            if self.state in ("BETTING", "BOT_PAUSE"):
                to_call = self.to_call_amount(self.current_player)
                info = self.midfont.render(
                    f"A igualar: {to_call}", True, (230, 230, 230)
                )
                self.screen.blit(info, (20, HEIGHT - FOOTER_H + 10))

                minraise = self.min_raise_amount()
                maxinfo = (
                    "All-in"
                    if self.can_allin_now()
                    else f"Máx pre-river: call + min(pote, {4 * BIG_BLIND})"
                )
                mi = self.font.render(
                    f"Min-raise: +{minraise}", True, (210, 210, 210)
                )
                ma = self.font.render(maxinfo, True, (210, 210, 210))
                self.screen.blit(mi, (20, HEIGHT - FOOTER_H + 34))
                self.screen.blit(ma, (20, HEIGHT - FOOTER_H + 54))
            else:
                info = self.midfont.render(
                    "A igualar: 0", True, (230, 230, 230)
                )
                self.screen.blit(info, (20, HEIGHT - FOOTER_H + 10))

        if self.players and len(self.players) > self.hero_index:
            hero = self.players[self.hero_index]
            stack_txt = self.midfont.render(
                f"Tu stack: $ {hero.stack}", True, (230, 230, 230)
            )
            self.screen.blit(
                stack_txt,
                stack_txt.get_rect(
                    bottomright=(WIDTH - 24, HEIGHT - FOOTER_H + 60)
                ),
            )

        log_y = 110
        for msg in self.log[-6:]:
            t = self.font.render("• " + msg, True, (230, 230, 230))
            self.screen.blit(t, (24, log_y))
            log_y += 20

        if self.banner_timer > 0 and self.banner_text:
            w = 640
            h = 52
            r = pygame.Rect(WIDTH // 2 - w // 2, 88, w, h)
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            s.fill((16, 16, 16, 180))
            self.screen.blit(s, r.topleft)
            pygame.draw.rect(self.screen, (220, 220, 220), r, 2, border_radius=10)
            btxt = self.midfont.render(self.banner_text, True, (240, 240, 240))
            self.screen.blit(btxt, btxt.get_rect(center=r.center))

        if self.state in ("ENDHAND", "SHOWDOWN") and self.last_winner_text:
            winner_surface = self.bigfont.render(
                self.last_winner_text, True, (255, 215, 0)
            )
            self.screen.blit(
                winner_surface,
                winner_surface.get_rect(
                    center=(WIDTH // 2, HEIGHT - FOOTER_H - 40)
                ),
            )

    def make_action_buttons(self) -> None:
        self.buttons = []
        y = HEIGHT - FOOTER_H + 18

        spacing = 170
        x = 210

        p = (
            self.players[self.current_player]
            if 0 <= self.current_player < len(self.players)
            else None
        )
        to_call = (
            self.to_call_amount(self.current_player)
            if (self.state in ("BETTING", "BOT_PAUSE") and p)
            else 0
        )

        can_act = (
            self.state in ("BETTING", "BOT_PAUSE")
            and p
            and p.is_human
            and (not p.folded)
            and (not p.all_in)
            and p.stack > 0
            and self.current_player in self.pending_to_act
        )

        call_label = "Pasar" if to_call == 0 else "Igualar"

        self.buttons.append(
            Button(
                (x, y, 150, 48),
                "Retirarse",
                self.player_action_fold
                if (
                    p
                    and p.is_human
                    and not p.folded
                    and not p.all_in
                    and self.state in ("BETTING", "BOT_PAUSE")
                )
                else (lambda: None),
            )
        )
        x += spacing

        self.buttons.append(
            Button(
                (x, y, 150, 48),
                call_label,
                self.player_action_call
                if (
                    can_act
                    or (
                        to_call == 0
                        and self.state in ("BETTING", "BOT_PAUSE")
                        and p
                        and not p.folded
                        and not p.all_in
                        and p.is_human
                    )
                )
                else (lambda: None),
            )
        )
        x += spacing

        self.buttons.append(
            Button(
                (x, y, 150, 48),
                "Aumentar",
                self.open_keypad if can_act else (lambda: None),
            )
        )
        x += spacing

        self.buttons.append(
            Button(
                (x, y, 150, 48),
                "All-in",
                self.player_action_allin if can_act else (lambda: None),
            )
        )
        x += spacing

        def cb_menu() -> None:
            self.return_to_lobby()

        self.buttons.append(Button((x, y, 150, 48), "Menu", cb_menu))

    def draw(self) -> None:
        if self.state == "LOBBY":
            self.draw_lobby()
            pygame.display.flip()
            return

        self.draw_table()
        self.draw_board()
        self.draw_players()
        self.draw_hud()

        for b in self.buttons:
            b.draw(self.screen, self.font, self.midfont)

        if self.keypad_visible:
            r = self.keypad_rect
            pygame.draw.rect(self.screen, (24, 30, 38), r, border_radius=12)
            pygame.draw.rect(self.screen, (120, 120, 120), r, 2, border_radius=12)

            to_call = (
                self.to_call_amount(self.current_player)
                if self.state in ("BETTING", "BOT_PAUSE")
                else 0
            )
            minraise = self.min_raise_amount()
            title = self.bigfont.render(
                f"Subir a: {self.keypad_value}", True, (240, 240, 240)
            )
            self.screen.blit(title, (r.x + 16, r.y + 16))

            info_l = self.midfont.render(
                f"A igualar: {to_call}", True, (220, 220, 220)
            )
            info_r = self.midfont.render(
                f"Min-raise: +{minraise}", True, (220, 220, 220)
            )
            cap_txt = (
                "Máx: All-in"
                if self.can_allin_now()
                else f"Máx pre-river: call + min(pote, {4 * BIG_BLIND})"
            )
            info_c = self.font.render(cap_txt, True, (210, 210, 210))

            self.screen.blit(info_l, (r.x + 16, r.y + 44))
            self.screen.blit(info_r, (r.right - 16 - info_r.get_width(), r.y + 44))
            self.screen.blit(info_c, (r.x + 16, r.y + 64))

            for b in self.buttons:
                b.draw(self.screen, self.font, self.midfont)

        pygame.display.flip()

    # --- update loop tick ---
    def update(self) -> None:
        if self.banner_timer > 0:
            self.banner_timer -= 1000 / FPS
            if self.banner_timer < 0:
                self.banner_timer = 0

        if self.state == "BOT_PAUSE":
            if self.bot_pause_timer > 0:
                self.bot_pause_timer -= 1000 / FPS
            if self.bot_pause_timer <= 0:
                self.state = "BETTING"
                self.make_action_buttons()
            return

        if self.state == "BETTING":
            self.bot_take_turn_if_needed()
