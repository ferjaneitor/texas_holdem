from __future__ import annotations
import random
from typing import Tuple, List

from .player import Player
from .cards import Card
from .config import BIG_BLIND, EASY, MED
from .eval_hand import quick_strength

"""
ai.py
-----
Lógica de decisión de los bots (fold/call/raise/allin).
"""


def bot_decision(
    player: Player,
    to_call: int,
    min_raise: int,
    pot: int,
    board: List[Card],
    round_index: int
) -> Tuple[str, int]:
    """
    Devuelve (acción, cantidad) donde acción ∈ {'fold','call','raise_to','allin'}.
    Ver comentarios en game.Game.bot_take_turn_if_needed() para cómo se usa.
    """

    strength = quick_strength(player.hole, board)

    # Tabla de agresividad por dificultad
    if player.difficulty == EASY:
        fold_t_base = 0.30
        raise_t_base = 0.60
        bluff_chance = 0.02
        raise_factor = 0.8
        call_bias = 0.55
    elif player.difficulty == MED:
        fold_t_base = 0.22
        raise_t_base = 0.50
        bluff_chance = 0.07
        raise_factor = 1.2
        call_bias = 0.45
    else:
        # HARD
        fold_t_base = 0.14
        raise_t_base = 0.38
        bluff_chance = 0.14
        raise_factor = 1.7
        call_bias = 0.30

    pot_pressure = min(1.0, pot / 400.0)
    fold_t = max(0.05, fold_t_base - 0.10 * pot_pressure)
    raise_t = min(0.95, raise_t_base - 0.05 * pot_pressure)

    # posible farol agresivo
    if random.random() < bluff_chance and to_call <= pot * 0.4:
        target_total = to_call + max(
            min_raise,
            int((pot * 0.4) + (strength * 80 * raise_factor))
        )
        return ('raise_to', target_total)

    # mano floja y pagar caro -> fold
    if strength < fold_t and to_call > 0:
        return ('fold', 0)

    want_raise = (
        strength > raise_t or
        (to_call == 0 and random.random() > call_bias)
    )

    if want_raise:
        base_raise = (pot * 0.3) + (strength * 100 * raise_factor)
        target_total = to_call + max(min_raise, int(base_raise))

        short_stack = (player.stack < max(80, pot * 0.6))
        endgame_push = (round_index >= 2)  # river
        if (short_stack or endgame_push) and random.random() < 0.15 * raise_factor:
            return ('allin', player.stack)

        return ('raise_to', target_total)

    return ('call', to_call)
