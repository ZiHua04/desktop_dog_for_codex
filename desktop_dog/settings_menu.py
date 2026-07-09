from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pygame


@dataclass
class PetSettings:
    dog_index: int = 1
    auto_behavior: bool = True
    auto_bark: bool = False
    sound_enabled: bool = True
    volume: float = 0.9
    always_on_top: bool = True
    speech_scroll: bool = False


@dataclass(frozen=True)
class DogBreed:
    label: str
    asset_dir: Path


@dataclass(frozen=True)
class MenuAction:
    kind: str
    value: object | None = None


@dataclass
class MenuItem:
    text: str
    action: MenuAction
    rect: pygame.Rect


class SettingsMenu:
    WIDTH = 260
    PADDING = 12
    HEADER_HEIGHT = 34
    ITEM_HEIGHT = 30
    RADIUS = 8

    BG = (255, 248, 236)
    BORDER = (190, 160, 124)
    TEXT = (73, 57, 44)
    MUTED = (127, 103, 79)
    HOVER = (246, 229, 204)

    def __init__(self, breeds: list[DogBreed], settings: PetSettings) -> None:
        if not pygame.font.get_init():
            pygame.font.init()

        self.breeds = breeds
        self.settings = settings
        self.visible = False
        self.rect = pygame.Rect(0, 0, self.WIDTH, 10)
        self.items: list[MenuItem] = []
        self.hover_index: int | None = None
        self.font = pygame.font.SysFont("Microsoft YaHei UI", 15)
        self.title_font = pygame.font.SysFont("Microsoft YaHei UI", 16, bold=True)

    @property
    def current_breed(self) -> DogBreed:
        return self.breeds[self.settings.dog_index]

    def open(self, pos: tuple[int, int], bounds: pygame.Rect) -> None:
        self.visible = True
        self._rebuild_items()
        self.rect.topleft = pos
        self.rect.clamp_ip(bounds)

    def close(self) -> None:
        self.visible = False
        self.hover_index = None

    def handle_event(self, event: pygame.event.Event) -> MenuAction | None:
        if not self.visible:
            return None

        if event.type == pygame.MOUSEMOTION:
            self.hover_index = self._item_at(event.pos)
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = self._item_at(event.pos)
            if index is None:
                self.close()
                return None

            action = self.items[index].action
            self.close()
            return action

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if not self.rect.collidepoint(event.pos):
                self.close()
            return None

        return None

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        self._rebuild_items()
        pygame.draw.rect(surface, self.BG, self.rect, border_radius=self.RADIUS)
        pygame.draw.rect(surface, self.BORDER, self.rect, width=1, border_radius=self.RADIUS)

        title = self.title_font.render("桌宠设置", True, self.TEXT)
        surface.blit(title, (self.rect.x + self.PADDING, self.rect.y + 9))

        for index, item in enumerate(self.items):
            rect = item.rect.move(self.rect.topleft)
            if index == self.hover_index:
                pygame.draw.rect(surface, self.HOVER, rect, border_radius=6)

            label = self.font.render(item.text, True, self.TEXT if item.action.kind != "label" else self.MUTED)
            surface.blit(label, (rect.x + 8, rect.y + 7))

    def hit_test(self, pos: tuple[int, int]) -> bool:
        return self.visible and self.rect.collidepoint(pos)

    def _rebuild_items(self) -> None:
        rows = [
            ("品种: " + self.current_breed.label, MenuAction("next_breed")),
            ("自动行动: " + _on_off(self.settings.auto_behavior), MenuAction("toggle_auto_behavior")),
            ("自己会叫: " + _on_off(self.settings.auto_bark), MenuAction("toggle_auto_bark")),
            ("声音: " + _on_off(self.settings.sound_enabled), MenuAction("toggle_sound")),
            (f"音量: {int(self.settings.volume * 100)}%", MenuAction("volume")),
            ("窗口置顶: " + _on_off(self.settings.always_on_top), MenuAction("toggle_topmost")),
            ("长文本滚动: " + _on_off(self.settings.speech_scroll), MenuAction("toggle_speech_scroll")),
            ("让狗狗叫一声", MenuAction("bark")),
            ("坐下", MenuAction("sit")),
            ("睡觉", MenuAction("sleep")),
            ("关闭程序", MenuAction("quit")),
        ]

        self.items = []
        y = self.HEADER_HEIGHT
        for text, action in rows:
            rect = pygame.Rect(self.PADDING, y, self.WIDTH - self.PADDING * 2, self.ITEM_HEIGHT)
            self.items.append(MenuItem(text, action, rect))
            y += self.ITEM_HEIGHT

        self.rect.size = (self.WIDTH, y + self.PADDING)

    def _item_at(self, pos: tuple[int, int]) -> int | None:
        if not self.rect.collidepoint(pos):
            return None

        local = (pos[0] - self.rect.x, pos[1] - self.rect.y)
        for index, item in enumerate(self.items):
            if item.rect.collidepoint(local):
                return index
        return None


def discover_breeds(root: Path) -> list[DogBreed]:
    labels = {
        "Dog-1-Golden-Retriever": "Golden Retriever",
        "Dog-2-Akita": "Akita",
        "Dog-3-Great-Dane": "Great Dane",
        "Dog-4-Schnauzer": "Schnauzer",
        "Dog-5-Saint-Bernard": "Saint Bernard",
        "Dog-6-Siberian-Husky": "Siberian Husky",
    }

    breeds = []
    for path in sorted(root.iterdir()):
        if path.is_dir() and (path / "animations.json").exists():
            breeds.append(DogBreed(labels.get(path.name, path.name), path))
    return breeds


def _on_off(value: bool) -> str:
    return "开" if value else "关"
