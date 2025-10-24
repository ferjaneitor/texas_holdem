from __future__ import annotations
import pygame
from typing import Callable

"""
ui.py
-----
Elementos UI reutilizables, como el botón clickeable.
"""


class Button:
    """
    Botón rectangular clickeable.

    Args:
        rect: (x,y,w,h)
        label: texto
        on_click: callback sin args
        small: usa fuente más chica si True
    """

    def __init__(self, rect, label: str, on_click: Callable[[], None], small: bool = False) -> None:
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.small = small

    def draw(self, surf: pygame.Surface, font: pygame.font.Font, midfont: pygame.font.Font) -> None:
        hover = self.rect.collidepoint(*pygame.mouse.get_pos())
        base = (56, 86, 110) if hover else (40, 66, 88)
        pygame.draw.rect(surf, base, self.rect, border_radius=12)
        pygame.draw.rect(surf, (12, 12, 12), self.rect, 2, border_radius=12)
        f = midfont if not self.small else font
        txt = f.render(self.label, True, (240, 240, 240))
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def handle(self, event: pygame.event.Event) -> None:
        if (
            event.type == pygame.MOUSEBUTTONDOWN and
            event.button == 1 and
            self.rect.collidepoint(*event.pos)
        ):
            self.on_click()
