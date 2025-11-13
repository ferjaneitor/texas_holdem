from __future__ import annotations

from typing import List
import random

from config import BIG_BLIND, BOT_THINK_MS, BOT_POST_ACT_PAUSE, FPS
from ai import bot_decision

class BettingMixin:
    # --- betting engine core ---
    def eligible_players_for_street(self) -> List[int]:
        return [
            i
            for i, p in enumerate(self.players)
            if not p.folded and not p.all_in and p.stack > 0
        ]

    def next_in_pending_from(self, start_idx: int) -> int:
        if not self.pending_to_act:
            return start_idx
        n = len(self.players)
        for step in range(1, n + 1):
            j = (start_idx + step) % n
            if j in self.pending_to_act:
                return j
        return start_idx

    def start_street(self, first_player: int, preflop: bool = False) -> None:
        self.first_to_act = first_player
        self.acted_set = set()

        if not preflop:
            for p in self.players:
                if not p.all_in:
                    p.bet = 0
            self.current_bet = 0
            self.last_raiser = None
            self.had_aggression = False
            self.pending_to_act = set(self.eligible_players_for_street())
        else:
            self.had_aggression = True
            elig = set(self.eligible_players_for_street())
            if self.last_raiser is not None and self.last_raiser in elig:
                elig.discard(self.last_raiser)
            self.pending_to_act = elig

        self.current_player = self.next_in_pending_from(
            (first_player - 1) % len(self.players)
        )

    def to_call_amount(self, idx: int) -> int:
        p = self.players[idx]
        return max(0, self.current_bet - p.bet)

    def min_raise_amount(self) -> int:
        if self.current_bet == 0:
            return BIG_BLIND
        return max(self.last_raise_size, BIG_BLIND)

    def only_one_left(self) -> bool:
        return sum(1 for p in self.players if not p.folded) == 1

    def mark_action(self, idx: int, kind: str) -> None:
        if kind in ("check", "call", "fold"):
            if idx in self.pending_to_act:
                self.pending_to_act.discard(idx)
            return

        if kind in ("bet", "raise", "allin"):
            self.had_aggression = True
            self.last_raiser = idx
            elig = [
                i for i, p in enumerate(self.players) if not p.folded and not p.all_in
            ]
            self.pending_to_act = {
                i for i in elig
                if i != idx and self.players[i].bet < self.current_bet
            }

    def street_should_end(self) -> bool:
        if len(self.pending_to_act) == 0:
            return True
        vivos = [p for p in self.players if not p.folded]
        if vivos and all(p.all_in for p in vivos):
            return True
        return False

    def proceed_round(self) -> None:
        if getattr(self, "_advancing", False):
            return
        self._advancing = True
        try:
            if self.round_index == 0:
                # Turn
                if self.board_visible_count < 4:
                    self.board_visible_count = 4
                self.board = self.board_all[:self.board_visible_count]
                self.round_index = 1
                first = (self.dealer_index + 1) % len(self.players)
                self.start_street(first, preflop=False)
                self.state = "ROUND_PAUSE"
                self.make_continue_button()
                self.dump_state("after_turn_reveal")
                return

            if self.round_index == 1:
                # River
                if self.board_visible_count < 5:
                    self.board_visible_count = 5
                self.board = self.board_all[:self.board_visible_count]
                self.round_index = 2
                first = (self.dealer_index + 1) % len(self.players)
                self.start_street(first, preflop=False)
                self.state = "ROUND_PAUSE"
                self.make_continue_button()
                self.dump_state("after_river_reveal")
                return

            if self.round_index == 2:
                # Showdown
                self.round_index = 3
                self.state = "SHOWDOWN"
                self.showdown()
                self.make_continue_button("Siguiente mano")
                self.dump_state("after_showdown")
                return

            # fallback
            self.state = "SHOWDOWN"
            self.showdown()
            self.make_continue_button("Siguiente mano")
            self.dump_state("fallback_showdown")
        finally:
            self._advancing = False

    # --- acciones humano ---
    def _human_can_act_now(self) -> bool:
        return self.state in ("BETTING", "BOT_PAUSE")

    def human_action(self, label: str) -> None:
        p = self.players[self.current_player]
        self.banner(label, who=p.name)
        self.push_log(f"{p.name}: {label}")

    def player_action_fold(self) -> None:
        if not self._human_can_act_now():
            return
        p = self.players[self.current_player]
        if (not p.is_human) or p.folded or p.all_in:
            return
        if self.current_player not in self.pending_to_act:
            return
        p.folded = True
        self.human_action("Se retira")
        self.mark_action(self.current_player, "fold")
        self.advance_after_action()

    def player_action_call(self) -> None:
        if not self._human_can_act_now():
            return
        p = self.players[self.current_player]
        if (not p.is_human) or p.folded or p.all_in:
            return

        to_call = self.to_call_amount(self.current_player)
        if to_call > 0 and self.current_player not in self.pending_to_act:
            return

        if not self.can_allin_now():
            if p.stack - min(to_call, p.stack) < BIG_BLIND and to_call > 0:
                self.banner(f"No puedes bajar de {BIG_BLIND} antes del river.")
                return

        need = to_call
        put = min(need, p.stack)
        if put > 0:
            p.stack -= put
            p.bet += put
            self.pot += put
        if p.stack == 0 and need > 0:
            p.all_in = True

        self.human_action("Iguala" if need > 0 else "Pasa")
        self.mark_action(self.current_player, "call" if need > 0 else "check")
        self.advance_after_action()

    def player_action_allin(self) -> None:
        if not self._human_can_act_now():
            return
        if not self.can_allin_now():
            self.banner("El all-in solo está permitido en la última ronda.")
            return
        p = self.players[self.current_player]
        if (not p.is_human) or p.folded or p.all_in or p.stack == 0:
            return
        if self.current_player not in self.pending_to_act:
            return

        total = p.stack
        p.stack = 0
        p.bet += total
        self.pot += total
        p.all_in = True

        prev_cb = self.current_bet
        if p.bet > self.current_bet:
            self.current_bet = p.bet
            self.last_raiser = self.current_player
            self.last_raise_size = max(
                self.last_raise_size, self.current_bet - prev_cb
            )
            self.mark_action(self.current_player, "allin")
        else:
            self.mark_action(self.current_player, "call")

        self.human_action("All-in")
        self.advance_after_action()

    def player_action_raise_to(self, target_total: int) -> None:
        if not self._human_can_act_now():
            return
        p = self.players[self.current_player]
        if (not p.is_human) or p.folded or p.all_in or p.stack == 0:
            return
        if self.current_player not in self.pending_to_act:
            return

        if target_total <= self.current_bet:
            return self.player_action_call()

        if not self.can_allin_now():
            target_total = self.pre_river_cap_target(self.current_player, target_total)
            to_call = self.to_call_amount(self.current_player)
            if (
                p.stack - max(0, min(to_call, p.stack)) < BIG_BLIND
                and target_total <= self.current_bet
            ):
                self.banner(f"No puedes bajar de {BIG_BLIND} antes del river.")
                return

        raise_diff = target_total - self.current_bet
        if raise_diff < self.min_raise_amount():
            target_total = self.current_bet + self.min_raise_amount()

        need = max(0, target_total - p.bet)
        if need <= 0:
            return self.player_action_call()

        need = min(need, p.stack)
        if need <= 0:
            return

        prev_cb = self.current_bet
        p.stack -= need
        p.bet += need
        self.pot += need

        if p.bet > self.current_bet:
            self.current_bet = p.bet
            self.last_raiser = self.current_player
            if (self.current_bet - prev_cb) >= self.min_raise_amount():
                self.last_raise_size = self.current_bet - prev_cb
            if p.stack == 0:
                p.all_in = True
            self.human_action(f"Sube a {p.bet}")
            self.mark_action(self.current_player, "raise")
            self.advance_after_action()
        else:
            self.human_action("Iguala")
            self.mark_action(self.current_player, "call")
            self.advance_after_action()

    def advance_after_action(self) -> None:
        if self.only_one_left():
            self.round_index = 3
            self.state = "SHOWDOWN"
            self.showdown()
            return

        if self.street_should_end():
            self.proceed_round()
            return

        self.current_player = self.next_player(self.current_player)
        self.dump_state("after_action")

    def next_player(self, i: int) -> int:
        if not self.pending_to_act:
            return i
        n = len(self.players)
        for step in range(1, n + 1):
            j = (i + step) % n
            if j in self.pending_to_act:
                return j
        return i

    # --- turno de bots ---
    def bot_take_turn_if_needed(self) -> None:
        if self.state not in ("BETTING", "BOT_PAUSE"):
            return

        if self.street_should_end():
            self.proceed_round()
            return

        if self.current_player not in self.pending_to_act:
            self.current_player = self.next_player(self.current_player)
            if self.street_should_end():
                self.proceed_round()
            return

        p = self.players[self.current_player]

        if p.is_human:
            return

        if p.folded or p.all_in:
            if self.current_player in self.pending_to_act:
                self.pending_to_act.discard(self.current_player)
            if self.street_should_end():
                self.proceed_round()
            else:
                self.current_player = self.next_player(self.current_player)
            return

        # "pensando..."
        if self.bot_think_timer <= 0:
            self.bot_think_timer = BOT_THINK_MS * (0.8 + random.random() * 0.6)
            self.banner("pensando...", who=p.name)
            return
        else:
            self.bot_think_timer -= 1000 / FPS
            if self.bot_think_timer > 0:
                return

        to_call = self.to_call_amount(self.current_player)
        act, amount = bot_decision(
            p,
            to_call,
            self.min_raise_amount(),
            self.pot,
            self.board,
            self.round_index,
        )

        allin_allowed = self.can_allin_now()
        label = ""

        if act == "fold":
            p.folded = True
            label = "se retira"
            self.mark_action(self.current_player, "fold")

        elif act == "call":
            if (
                not allin_allowed
                and p.stack - min(to_call, p.stack) < BIG_BLIND
                and to_call > 0
            ):
                p.folded = True
                label = "se retira"
                self.mark_action(self.current_player, "fold")
            else:
                put = min(to_call, p.stack)
                p.stack -= put
                p.bet += put
                self.pot += put
                if p.stack == 0 and to_call > 0:
                    p.all_in = True
                label = "iguala" if to_call > 0 else "pasa"
                self.mark_action(
                    self.current_player, "call" if to_call > 0 else "check"
                )

        elif act == "allin":
            if not allin_allowed:
                amount = self.pre_river_cap_target(
                    self.current_player,
                    p.bet + p.stack - 1,
                )
                act = "raise_to" if amount > max(self.current_bet, p.bet) else "call"

            if allin_allowed:
                total = p.stack
                p.stack = 0
                p.bet += total
                self.pot += total
                p.all_in = True
                label = "va all-in"
                prev_cb = self.current_bet
                if p.bet > self.current_bet:
                    self.current_bet = p.bet
                    self.last_raiser = self.current_player
                    self.last_raise_size = max(
                        self.last_raise_size, self.current_bet - prev_cb
                    )
                    self.mark_action(self.current_player, "allin")
                else:
                    self.mark_action(self.current_player, "call")

        if act == "raise_to":
            if not allin_allowed:
                amount = self.pre_river_cap_target(self.current_player, amount)
            need = max(0, amount - p.bet)
            need = min(need, p.stack)
            if need <= 0:
                label = "pasa" if to_call == 0 else "iguala"
                self.mark_action(
                    self.current_player, "check" if to_call == 0 else "call"
                )
            else:
                prev_cb = self.current_bet
                p.stack -= need
                p.bet += need
                self.pot += need
                label = f"sube a {p.bet}"
                if p.bet > self.current_bet:
                    self.current_bet = p.bet
                    self.last_raiser = self.current_player
                    if (self.current_bet - prev_cb) >= self.min_raise_amount():
                        self.last_raise_size = self.current_bet - prev_cb
                    if p.stack == 0:
                        p.all_in = True
                    self.mark_action(self.current_player, "raise")
                else:
                    self.mark_action(self.current_player, "call")

        self.banner(label, who=p.name)
        self.push_log(f"{p.name}: {label}.")

        self.bot_think_timer = 0.0

        self.advance_after_action()

        if self.state in ("BETTING", "BOT_PAUSE"):
            self.state = "BOT_PAUSE"
            self.bot_pause_timer = float(BOT_POST_ACT_PAUSE)
