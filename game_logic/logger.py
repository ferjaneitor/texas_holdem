# game/logger.py
from __future__ import annotations
import logging

from config import BANNER_MS   # estaba como .config, pásalo así


class LoggerMixin:
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
                if 0 <= self.current_player < len(self.players)
                else "?"
            )
            logging.info(
                f"[STATE {tag}] round={self.round_index}({self.round_label()}) "
                f"pot={self.pot} current_bet={self.current_bet} current_player={who} "
                f"stacks={stacks} bets={bets} folded={folds} allin={allins} "
                f"pending={sorted(list(self.pending_to_act))}"
            )
        except Exception:
            pass
