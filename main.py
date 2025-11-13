from __future__ import annotations
import random

from utils import setup_logging        # utils está al lado de main.py
from game_logic import Game            # Game viene del paquete game_logic


def main() -> None:
    setup_logging()
    random.seed()
    Game().run()


if __name__ == "__main__":
    main()
