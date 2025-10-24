from __future__ import annotations
from typing import List, Tuple, Set, Optional
import math
import random
import sys
import pygame
import logging

from .config import (
    WIDTH, HEIGHT, FPS,
    TABLE_COLOR, CARD_W, CARD_H, FOOTER_H, PLAYER_Y, BOT_MAX_Y,
    STARTING_STACK, SMALL_BLIND, BIG_BLIND, MAX_BOTS,
    ARCADE_REBUY, AUTO_REBUY_BOTS,
    BOT_THINK_MS, BOT_POST_ACT_PAUSE, BANNER_MS,
    EASY, MED, HARD,
)
from .utils import clamp
from .cards import Deck, Card
from .player import Player
from .ai import bot_decision
from .eval_hand import evaluate7
from .ui import Button



class Game:
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
        self.midfont = pygame.font.SysFont(pygame.font.get_default_font(), 20, bold=True)
        self.bigfont = pygame.font.SysFont(pygame.font.get_default_font(), 28, bold=True)
        self.titlefont = pygame.font.SysFont(pygame.font.get_default_font(), 44, bold=True)

        # Estado general
        self.state: str = 'LOBBY'
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

        # feedback visual
        self.bot_think_timer: float = 0.0
        self.bot_pause_timer: float = 0.0
        self.banner_text: str = ""
        self.banner_timer: float = 0.0
        self.log: List[str] = []
        self.last_winner_text: str = ""

        self.make_lobby_buttons()

    # --- logging helpers / UI status ---
    def round_label(self) -> str:
        names = ["Flop", "Turn", "River", "Showdown"]
        if 0 <= self.round_index < len(names):
            return names[self.round_index]
        return f"Ronda {self.round_index}"

    def banner(self, text: str, who: str = "") -> None:
        self.banner_text = (who + ": " + text) if who else text
        self.banner_timer = float(BANNER_MS)

    def push_log(self, msg: str) -> None:
        self.log.append(msg)
        try:
            logging.info(f"[{self.round_label()}] {msg}")
        except Exception:
            pass

    def dump_state(self, tag: str = "") -> None:
        try:
            stacks = [p.stack for p in self.players]
            bets = [p.bet for p in self.players]
            folds = [p.folded for p in self.players]
            allins = [p.all_in for p in self.players]
            who = (
                self.players[self.current_player].name
                if 0 <= self.current_player < len(self.players) else "?"
            )
            logging.info(
                f"[STATE {tag}] round={self.round_index}({self.round_label()}) "
                f"pot={self.pot} current_bet={self.current_bet} current_player={who} "
                f"stacks={stacks} bets={bets} folded={folds} allin={allins} "
                f"pending={sorted(list(self.pending_to_act))}"
            )
        except Exception:
            pass

    # --- lobby buttons ---
    def make_lobby_buttons(self) -> None:
        self.buttons = []

        def minus_bots() -> None:
            self.num_bots = int(clamp(self.num_bots - 1, 1, MAX_BOTS))

        def plus_bots() -> None:
            self.num_bots = int(clamp(self.num_bots + 1, 1, MAX_BOTS))

        def diff_prev() -> None:
            order = [EASY, MED, HARD]
            self.bot_difficulty = order[(order.index(self.bot_difficulty) - 1) % len(order)]

        def diff_next() -> None:
            order = [EASY, MED, HARD]
            self.bot_difficulty = order[(order.index(self.bot_difficulty) + 1) % len(order)]

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
            Button((WIDTH // 2 - 100, HEIGHT - FOOTER_H + 18, 200, 48), label, cb_continue),
            Button((WIDTH // 2 + 320, HEIGHT - FOOTER_H + 18, 150, 48), "Menu", cb_menu),
        ]

    def return_to_lobby(self) -> None:
        self.state = 'LOBBY'
        self.keypad_visible = False
        self.banner_text = ""
        self.banner_timer = 0.0
        self.log = []
        self.last_winner_text = ""
        self.make_lobby_buttons()

    # --- keypad modal ---
    def open_keypad(self) -> None:
        p = self.players[self.current_player] if self.players else None
        if (
            not p or
            (self.state not in ('BETTING', 'BOT_PAUSE')) or
            p.folded or p.all_in or p.stack <= 0 or
            self.current_player not in self.pending_to_act
        ):
            return
        self.keypad_visible = True
        self.keypad_value = max(self.current_bet + self.min_raise_amount(), self.current_bet + 1)
        self.make_keypad_buttons()

    def can_allin_now(self) -> bool:
        return (
            self.round_index == 2 and
            self.state in ('BETTING', 'BOT_PAUSE') and
            len(self.board) == 5
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
            panel_h
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
                p.bet + p.stack - 1
            )

        to_call = self.to_call_amount(self.current_player) if self.state in ('BETTING', 'BOT_PAUSE') else 0
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
            self.buttons.append(Button((x, y1, w, 44), "Igualar", do_equal, small=True))
            x += w + gap

        self.buttons.append(Button((x, y1, w, 44), "−BB", less_bb, small=True)); x += w + gap
        self.buttons.append(Button((x, y1, w, 44), "+BB", more_bb, small=True));  x += w + gap
        self.buttons.append(Button((x, y1, w, 44), "Pote", set_pot, small=True)); x += w + gap
        self.buttons.append(Button(
            (x, y1, w, 44),
            "All-in" if self.can_allin_now() else "All-in (cap)",
            set_allin,
            small=True
        ))
        self.buttons.append(Button((r.centerx - 54, y2, 108, 48), "OK", ok, small=True))
        self.buttons.append(Button((r.right - 116, y2, 100, 48), "Cerrar", cancel, small=True))

    def close_keypad(self) -> None:
        self.keypad_visible = False
        self.make_action_buttons()

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

    # --- setup jugadores / start hand ---
    def setup_players(self) -> None:
        self.players = [Player("Tú", is_human=True)]
        for i in range(self.num_bots):
            self.players.append(Player(f"Bot {i+1}", difficulty=self.bot_difficulty))
        self.hero_index = 0
        self.dealer_index = 0

    def start_hand(self) -> None:
        if AUTO_REBUY_BOTS:
            for pl in self.players:
                if not pl.is_human and pl.stack < BIG_BLIND:
                    pl.stack = STARTING_STACK
                    pl.total_won = 0

        for p in self.players:
            p.new_hand_reset()

        self.round_index = 0
        self.pot = 0
        self.current_bet = 0
        self.last_raiser = None
        self.last_raise_size = BIG_BLIND
        self.deck = Deck()

        # limpiar feedback
        self.bot_think_timer = 0.0
        self.bot_pause_timer = 0.0
        self.banner_text = ""
        self.banner_timer = 0.0
        self.pending_to_act = set()
        self.last_winner_text = ""
        self.keypad_visible = False
        self.log = []

        # hole cards
        if self.deck:
            for _ in range(2):
                for pl in self.players:
                    if pl.stack > 0:
                        pl.hole += self.deck.deal(1)

        # board pre-robado
        self.board_all = self.deck.deal(5) if self.deck else []
        self.board_visible_count = 3
        self.board = self.board_all[:self.board_visible_count]

        self.post_blinds()

        self.current_player = (self.dealer_index + 3) % len(self.players)
        self.start_street(self.current_player, preflop=True)

        self.state = 'BETTING'
        self.make_action_buttons()
        self.push_log("Nueva mano. Ciegas 10/20.")
        self.dump_state("start_hand")

    def post_blinds(self) -> None:
        n = len(self.players)
        sb_i = (self.dealer_index + 1) % n
        bb_i = (self.dealer_index + 2) % n
        sb = min(SMALL_BLIND, self.players[sb_i].stack)
        bb = min(BIG_BLIND, self.players[bb_i].stack)
        self.players[sb_i].stack -= sb
        self.players[sb_i].bet += sb
        self.players[bb_i].stack -= bb
        self.players[bb_i].bet += bb
        self.pot += sb + bb
        self.current_bet = bb
        self.last_raiser = bb_i
        self.last_raise_size = BIG_BLIND
        self.push_log(f"{self.players[sb_i].name} pone ciega chica ({sb}).")
        self.push_log(f"{self.players[bb_i].name} pone ciega grande ({bb}).")

    # --- betting engine core ---
    def eligible_players_for_street(self) -> List[int]:
        return [
            i for i, p in enumerate(self.players)
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
        if kind in ('check', 'call', 'fold'):
            if idx in self.pending_to_act:
                self.pending_to_act.discard(idx)
            return

        if kind in ('bet', 'raise', 'allin'):
            self.had_aggression = True
            self.last_raiser = idx
            elig = [
                i for i, p in enumerate(self.players)
                if not p.folded and not p.all_in
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
                self.state = 'ROUND_PAUSE'
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
                self.state = 'ROUND_PAUSE'
                self.make_continue_button()
                self.dump_state("after_river_reveal")
                return

            if self.round_index == 2:
                # Showdown
                self.round_index = 3
                self.state = 'SHOWDOWN'
                self.showdown()
                self.make_continue_button("Siguiente mano")
                self.dump_state("after_showdown")
                return

            # fallback
            self.state = 'SHOWDOWN'
            self.showdown()
            self.make_continue_button("Siguiente mano")
            self.dump_state("fallback_showdown")
        finally:
            self._advancing = False

    def continue_after_pause(self) -> None:
        if self.state == 'ROUND_PAUSE':
            self.state = 'BETTING'
            self.make_action_buttons()
            self.dump_state("continue_betting")

        elif self.state in ('ENDHAND', 'SHOWDOWN'):
            self.dealer_index = (self.dealer_index + 1) % len(self.players)

            if ARCADE_REBUY and self.players[self.hero_index].stack <= 0:
                self.players[self.hero_index].stack = STARTING_STACK
                self.players[self.hero_index].total_won = 0
                self.push_log("Recompra automática para el jugador.")

            self.start_hand()

    # --- acciones humano ---
    def _human_can_act_now(self) -> bool:
        return self.state in ('BETTING', 'BOT_PAUSE')

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
                self.last_raise_size,
                self.current_bet - prev_cb
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
            if p.stack - max(0, min(to_call, p.stack)) < BIG_BLIND and target_total <= self.current_bet:
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
            self.state = 'SHOWDOWN'
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
        if self.state not in ('BETTING', 'BOT_PAUSE'):
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
            p, to_call, self.min_raise_amount(),
            self.pot, self.board, self.round_index
        )

        allin_allowed = self.can_allin_now()
        label = ""

        if act == 'fold':
            p.folded = True
            label = "se retira"
            self.mark_action(self.current_player, "fold")

        elif act == 'call':
            if (
                not allin_allowed and
                p.stack - min(to_call, p.stack) < BIG_BLIND and
                to_call > 0
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
                label = ("iguala" if to_call > 0 else "pasa")
                self.mark_action(self.current_player, "call" if to_call > 0 else "check")

        elif act == 'allin':
            if not allin_allowed:
                amount = self.pre_river_cap_target(
                    self.current_player,
                    p.bet + p.stack - 1
                )
                act = 'raise_to' if amount > max(self.current_bet, p.bet) else 'call'

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
                        self.last_raise_size,
                        self.current_bet - prev_cb
                    )
                    self.mark_action(self.current_player, "allin")
                else:
                    self.mark_action(self.current_player, "call")

        if act == 'raise_to':
            if not allin_allowed:
                amount = self.pre_river_cap_target(self.current_player, amount)
            need = max(0, amount - p.bet)
            need = min(need, p.stack)
            if need <= 0:
                label = "pasa" if to_call == 0 else "iguala"
                self.mark_action(self.current_player, "check" if to_call == 0 else "call")
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

        if self.state in ('BETTING', 'BOT_PAUSE'):
            self.state = 'BOT_PAUSE'
            self.bot_pause_timer = float(BOT_POST_ACT_PAUSE)

    # --- showdown ---
    def showdown(self) -> None:
        contenders = [p for p in self.players if not p.folded]
        diff_label = self.bot_difficulty

        # Sólo uno
        if len(contenders) == 1:
            w = contenders[0]
            total_bote = self.pot
            w.stack += total_bote
            w.total_won += total_bote

            msg = f"{w.name} gana el bote sin mostrar (${total_bote}).  [{diff_label}]"

            self.push_log(msg)
            self.banner(msg)
            self.last_winner_text = msg

            self.pot = 0
            self.state = 'ENDHAND'
            self.make_continue_button("Siguiente mano")
            return

        # Showdown múltiple
        for p in contenders:
            self.push_log(f"{p.name} muestra {p.hole[0]} {p.hole[1]}.")

        scored = [(evaluate7(p.hole + self.board), p) for p in contenders]
        scored.sort(key=lambda x: x[0], reverse=True)

        best = scored[0][0]
        winners = [pl for sc, pl in scored if sc == best]

        total_bote = self.pot
        split = total_bote // len(winners)
        resto = total_bote - split * len(winners)

        names = ", ".join(w.name for w in winners)

        for w in winners:
            w.stack += split
            w.total_won += split
        if resto > 0:
            winners[0].stack += resto
            winners[0].total_won += resto

        if len(winners) == 1:
            msg = f"Gana {names} y se lleva ${total_bote}.  [{diff_label}]"
        else:
            msg = f"Empate entre {names}. Bote ${total_bote} dividido.  [{diff_label}]"

        self.push_log(msg)
        self.banner(msg)
        self.last_winner_text = msg

        self.pot = 0
        self.state = 'ENDHAND'
        self.make_continue_button("Siguiente mano")

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
        pygame.draw.ellipse(self.screen, TABLE_COLOR, (160, 46, WIDTH - 320, HEIGHT - 150))
        pygame.draw.ellipse(self.screen, (10, 40, 28), (150, 36, WIDTH - 300, HEIGHT - 130), 8)

    def draw_card(self, topleft: Tuple[int, int], card: Optional[Card] = None) -> None:
        x, y = topleft
        rect = pygame.Rect(x, y, CARD_W, CARD_H)
        pygame.draw.rect(self.screen, (240, 240, 240) if card else (32, 46, 58), rect, border_radius=10)
        pygame.draw.rect(self.screen, (200, 200, 200), rect, 2, border_radius=10)
        if card:
            rtxt = self.midfont.render(card.rank, True, (20, 20, 20))
            self.screen.blit(rtxt, (x + 8, y + 6))
            stxt = self.midfont.render(card.suit, True, (230, 80, 90) if card.suit in ('♥','♦') else (230,230,230))
            self.screen.blit(stxt, (x + CARD_W - 28, y + CARD_H - 34))

    def draw_hand_cards(self, center: Tuple[int, int], cards: List[Card], face_up: bool) -> None:
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

            if self.state in ('BETTING', 'BOT_PAUSE') and i == self.current_player:
                pygame.draw.circle(self.screen, (255, 204, 0), (sx, sy), 44, 4)

            name = self.midfont.render(p.name, True, (12, 12, 12))
            self.screen.blit(name, name.get_rect(center=(sx, sy - 56)))

            if not p.is_human:
                stack = self.font.render(f"Stack: $ {p.stack}", True, (12, 12, 12))
                self.screen.blit(stack, stack.get_rect(center=(sx, sy + 44)))

            bet = self.font.render(f"Apuesta: {p.bet}", True, (12, 12, 12))
            self.screen.blit(bet, bet.get_rect(center=(sx, sy + 62)))
            won = self.font.render(f"Ganado: {p.total_won}", True, (12, 12, 12))
            self.screen.blit(won, won.get_rect(center=(sx, sy + 80)))

            face_up = p.is_human or (self.state in ('SHOWDOWN', 'ENDHAND'))
            if len(p.hole) == 2:
                self.draw_hand_cards((sx, sy - 6), p.hole, face_up)

    def draw_hud(self) -> None:
        pot_txt = self.bigfont.render(f"Pote: {self.pot}", True, (240, 240, 240))
        self.screen.blit(pot_txt, (24, 20))

        names = ["Flop", "Turn", "River", "Showdown"]
        rlabel = names[self.round_index] if self.round_index < len(names) else str(self.round_index)
        r_txt = self.bigfont.render(f"Fase: {rlabel}", True, (240, 240, 240))
        self.screen.blit(r_txt, (24, 56))

        diff_txt = self.font.render(f"Dificultad: {self.bot_difficulty}", True, (200, 200, 200))
        self.screen.blit(diff_txt, (24, 80))

        pygame.draw.rect(
            self.screen,
            (24, 30, 38),
            pygame.Rect(0, HEIGHT - FOOTER_H, WIDTH, FOOTER_H)
        )

        if self.state in ('BETTING', 'ROUND_PAUSE', 'ENDHAND', 'SHOWDOWN', 'BOT_PAUSE'):
            if self.state in ('BETTING', 'BOT_PAUSE'):
                to_call = self.to_call_amount(self.current_player)
                info = self.midfont.render(f"A igualar: {to_call}", True, (230, 230, 230))
                self.screen.blit(info, (20, HEIGHT - FOOTER_H + 10))

                minraise = self.min_raise_amount()
                maxinfo = (
                    "All-in"
                    if self.can_allin_now()
                    else f"Máx pre-river: call + min(pote, {4 * BIG_BLIND})"
                )
                mi = self.font.render(f"Min-raise: +{minraise}", True, (210, 210, 210))
                ma = self.font.render(maxinfo, True, (210, 210, 210))
                self.screen.blit(mi, (20, HEIGHT - FOOTER_H + 34))
                self.screen.blit(ma, (20, HEIGHT - FOOTER_H + 54))
            else:
                info = self.midfont.render("A igualar: 0", True, (230, 230, 230))
                self.screen.blit(info, (20, HEIGHT - FOOTER_H + 10))

        if self.players and len(self.players) > self.hero_index:
            hero = self.players[self.hero_index]
            stack_txt = self.midfont.render(f"Tu stack: $ {hero.stack}", True, (230, 230, 230))
            self.screen.blit(
                stack_txt,
                stack_txt.get_rect(bottomright=(WIDTH - 24, HEIGHT - FOOTER_H + 60))
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

        if self.state in ('ENDHAND', 'SHOWDOWN') and self.last_winner_text:
            winner_surface = self.bigfont.render(self.last_winner_text, True, (255, 215, 0))
            self.screen.blit(
                winner_surface,
                winner_surface.get_rect(center=(WIDTH // 2, HEIGHT - FOOTER_H - 40))
            )

    def make_action_buttons(self) -> None:
        self.buttons = []
        y = HEIGHT - FOOTER_H + 18

        spacing = 170
        x = 210

        p = self.players[self.current_player] if 0 <= self.current_player < len(self.players) else None
        to_call = self.to_call_amount(self.current_player) if (self.state in ('BETTING', 'BOT_PAUSE') and p) else 0

        can_act = (
            self.state in ('BETTING', 'BOT_PAUSE') and
            p and p.is_human and
            (not p.folded) and
            (not p.all_in) and
            p.stack > 0 and
            self.current_player in self.pending_to_act
        )

        call_label = "Pasar" if to_call == 0 else "Igualar"

        self.buttons.append(
            Button(
                (x, y, 150, 48), "Retirarse",
                self.player_action_fold if (p and p.is_human and not p.folded and not p.all_in and self.state in ('BETTING', 'BOT_PAUSE')) else (lambda: None)
            )
        )
        x += spacing

        self.buttons.append(
            Button(
                (x, y, 150, 48), call_label,
                self.player_action_call if (
                    (can_act or (to_call == 0 and self.state in ('BETTING', 'BOT_PAUSE') and p and not p.folded and not p.all_in and p.is_human))
                ) else (lambda: None)
            )
        )
        x += spacing

        self.buttons.append(
            Button(
                (x, y, 150, 48), "Aumentar",
                self.open_keypad if can_act else (lambda: None)
            )
        )
        x += spacing

        self.buttons.append(
            Button(
                (x, y, 150, 48), "All-in",
                self.player_action_allin if can_act else (lambda: None)
            )
        )
        x += spacing

        def cb_menu() -> None:
            self.return_to_lobby()

        self.buttons.append(
            Button(
                (x, y, 150, 48), "Menu",
                cb_menu
            )
        )

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

    def draw(self) -> None:
        if self.state == 'LOBBY':
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

            to_call = self.to_call_amount(self.current_player) if self.state in ('BETTING', 'BOT_PAUSE') else 0
            minraise = self.min_raise_amount()
            title = self.bigfont.render(f"Subir a: {self.keypad_value}", True, (240, 240, 240))
            self.screen.blit(title, (r.x + 16, r.y + 16))

            info_l = self.midfont.render(f"A igualar: {to_call}", True, (220, 220, 220))
            info_r = self.midfont.render(f"Min-raise: +{minraise}", True, (220, 220, 220))
            cap_txt = (
                "Máx: All-in" if self.can_allin_now()
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

        if self.state == 'BOT_PAUSE':
            if self.bot_pause_timer > 0:
                self.bot_pause_timer -= 1000 / FPS
            if self.bot_pause_timer <= 0:
                self.state = 'BETTING'
                self.make_action_buttons()
            return

        if self.state == 'BETTING':
            self.bot_take_turn_if_needed()
