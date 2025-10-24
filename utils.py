from __future__ import annotations
import sys
import logging

"""
utils.py
--------
Utilidades genéricas compartidas: clamp y logging global.
"""


def clamp(x: float, a: float, b: float) -> float:
    """
    Restringe x al rango [a, b].

    Args:
        x: valor original.
        a: límite inferior.
        b: límite superior.

    Returns:
        x limitado entre a y b.
    """
    return max(a, min(b, x))


def setup_logging(logfile: str = "hand_history.log") -> None:
    """
    Configura logging a stdout y a archivo.

    Debe llamarse una sola vez al inicio del programa
    (por ejemplo en main.py).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(logfile, encoding="utf-8")
        ]
    )
