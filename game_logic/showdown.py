from __future__ import annotations

from eval_hand import evaluate7

class ShowdownMixin:
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
            self.state = "ENDHAND"
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
        self.state = "ENDHAND"
        self.make_continue_button("Siguiente mano")
