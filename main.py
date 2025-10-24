from __future__ import annotations
import random
from .utils import setup_logging
from .game import Game

def main() -> None:
    setup_logging()
    random.seed()
    Game().run()

if __name__ == "__main__":
    main()
