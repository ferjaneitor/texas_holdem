# game/state.py
from __future__ import annotations

from config import (
    STARTING_STACK,
    SMALL_BLIND,
    BIG_BLIND,
    ARCADE_REBUY,
    AUTO_REBUY_BOTS,
)
from cards import Deck
from player import Player


class StateMixin:
    # --- setup jugadores / start hand ---
    def setup_players(self) -> None:
        self.players = [Player("Tú", is_human=True)]
        for i in range(self.num_bots):
            self.players.append(
                Player(f"Bot {i + 1}", difficulty=self.bot_difficulty)
            )
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

        self.state = "BETTING"
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

    def continue_after_pause(self) -> None:
        if self.state == "ROUND_PAUSE":
            self.state = "BETTING"
            self.make_action_buttons()
            self.dump_state("continue_betting")

        elif self.state in ("ENDHAND", "SHOWDOWN"):
            self.dealer_index = (self.dealer_index + 1) % len(self.players)

            if ARCADE_REBUY and self.players[self.hero_index].stack <= 0:
                self.players[self.hero_index].stack = STARTING_STACK
                self.players[self.hero_index].total_won = 0
                self.push_log("Recompra automática para el jugador.")

            self.start_hand()
