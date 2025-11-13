from __future__ import annotations

import pygame

from config import WIDTH, HEIGHT, BIG_BLIND
from utils import clamp
from ui import Button

class KeypadMixin:
    # --- keypad modal ---
    def open_keypad(self) -> None:
        p = self.players[self.current_player] if self.players else None
        if (
            not p
            or (self.state not in ("BETTING", "BOT_PAUSE"))
            or p.folded
            or p.all_in
            or p.stack <= 0
            or self.current_player not in self.pending_to_act
        ):
            return
        self.keypad_visible = True
        self.keypad_value = max(
            self.current_bet + self.min_raise_amount(), self.current_bet + 1
        )
        self.make_keypad_buttons()

    def can_allin_now(self) -> bool:
        return (
            self.round_index == 2
            and self.state in ("BETTING", "BOT_PAUSE")
            and len(self.board) == 5
        )

    def pre_river_cap_target(self, idx: int, proposed_target: int) -> int:
        if self.can_allin_now():
            return proposed_target
        p = self.players[idx]
        to_call = self.to_call_amount(idx)

        cap_by_rule = p.bet + to_call + min(self.pot, 4 * BIG_BLIND)
        cap_by_floor = p.bet + max(0, p.stack - BIG_BLIND)
        legal_max = max(self.current_bet, min(cap_by_rule, cap_by_floor))
        legal_min = self.current_bet + 1
        return int(clamp(proposed_target, legal_min, legal_max))

    def make_keypad_buttons(self) -> None:
        self.buttons = []

        panel_w, panel_h = 480, 240
        self.keypad_rect = pygame.Rect(
            WIDTH // 2 - panel_w // 2,
            HEIGHT // 2 - panel_h // 2,
            panel_w,
            panel_h,
        )

        def legal_min_target() -> int:
            return max(self.current_bet + self.min_raise_amount(), self.current_bet + 1)

        def set_target(val: int) -> None:
            try:
                self.keypad_value = int(clamp(int(val), 0, 999_999_999))
            except Exception:
                self.keypad_value = max(0, self.current_bet + self.min_raise_amount())

        def capped_max_target() -> int:
            p = self.players[self.current_player]
            if self.can_allin_now():
                return p.bet + p.stack
            return self.pre_river_cap_target(
                self.current_player,
                p.bet + p.stack - 1,
            )

        to_call = (
            self.to_call_amount(self.current_player)
            if self.state in ("BETTING", "BOT_PAUSE")
            else 0
        )
        p = self.players[self.current_player]
        pot = max(0, self.pot)
        min_target = legal_min_target()
        pot_sized = p.bet + to_call + pot
        allin_total = p.bet + p.stack

        def do_equal() -> None:
            self.close_keypad()
            self.player_action_call()

        def less_bb() -> None:
            set_target(max(min_target, self.keypad_value - self.min_raise_amount()))

        def more_bb() -> None:
            set_target(min(capped_max_target(), self.keypad_value + self.min_raise_amount()))

        def set_pot() -> None:
            set_target(min(capped_max_target(), pot_sized))

        def set_allin() -> None:
            set_target(allin_total)

        def ok() -> None:
            target = max(self.keypad_value, min_target)
            if not self.can_allin_now():
                target = self.pre_river_cap_target(self.current_player, target)
            target = min(target, capped_max_target())

            self.close_keypad()
            if to_call > 0 and target <= self.current_bet:
                self.player_action_call()
            else:
                self.player_action_raise_to(target)

        def cancel() -> None:
            self.close_keypad()

        r = self.keypad_rect
        y1 = r.y + 86
        y2 = y1 + 56
        x = r.x + 16
        w = 96
        gap = 12

        if to_call > 0:
            self.buttons.append(
                Button((x, y1, w, 44), "Igualar", do_equal, small=True)
            )
            x += w + gap

        self.buttons.append(Button((x, y1, w, 44), "−BB", less_bb, small=True))
        x += w + gap
        self.buttons.append(Button((x, y1, w, 44), "+BB", more_bb, small=True))
        x += w + gap
        self.buttons.append(Button((x, y1, w, 44), "Pote", set_pot, small=True))
        x += w + gap
        self.buttons.append(
            Button(
                (x, y1, w, 44),
                "All-in" if self.can_allin_now() else "All-in (cap)",
                set_allin,
                small=True,
            )
        )
        self.buttons.append(
            Button((r.centerx - 54, y2, 108, 48), "OK", ok, small=True)
        )
        self.buttons.append(
            Button((r.right - 116, y2, 100, 48), "Cerrar", cancel, small=True)
        )

    def close_keypad(self) -> None:
        self.keypad_visible = False
        self.make_action_buttons()
