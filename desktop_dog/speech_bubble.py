from __future__ import annotations

import math

import pygame

from .resources import resource_path
from .text_utils import sanitize_text


class SpeechBubble:
    """桌宠对话气泡。

    气泡本身不接收鼠标事件，只负责显示文字。
    位置由狗狗的朝向决定：面朝右时显示在右上方，面朝左时显示在左上方。
    """

    WIDTH = 190
    HEIGHT = 66
    PADDING_X = 19
    PADDING_Y = 17
    IMAGE_PATH = resource_path("assets/ui/speech_bubble.png")
    ALPHA_THRESHOLD = 12

    BG = (236, 207, 91)
    TEXT = (82, 61, 34)
    ALPHA = 255

    def __init__(self) -> None:
        if not pygame.font.get_init():
            pygame.font.init()

        self.font = pygame.font.SysFont("Microsoft YaHei UI", 15)
        self.background = self._load_background()
        self.text = ""
        self.time_left = 0.0
        self.elapsed = 0.0
        self.scroll_enabled = False

    @property
    def visible(self) -> bool:
        return self.time_left > 0 and bool(self.text)

    def show(self, text: str, duration: float = 5.0) -> None:
        self.text = sanitize_text(text)
        self.time_left = max(1.0, duration)
        self.elapsed = 0.0

    def update(self, dt: float) -> None:
        if not self.visible:
            return

        self.time_left = max(0.0, self.time_left - dt)
        self.elapsed += dt

    def draw(self, surface: pygame.Surface, dog_rect: pygame.Rect, facing: int) -> None:
        if not self.visible:
            return

        bubble = self._bubble_rect(surface.get_rect(), dog_rect, facing)
        self._draw_background(surface, bubble)
        self._draw_text(surface, bubble)

    def _bubble_rect(self, bounds: pygame.Rect, dog_rect: pygame.Rect, facing: int) -> pygame.Rect:
        if facing >= 0:
            x = dog_rect.centerx + 20
        else:
            x = dog_rect.centerx - self.WIDTH - 20

        y = dog_rect.top - 50
        rect = pygame.Rect(x, y, self.WIDTH, self.HEIGHT)
        rect.clamp_ip(bounds)
        return rect

    def _load_background(self) -> pygame.Surface | None:
        """加载用户提供的对话框图片。

        图片只在初始化时加载一次；如果文件不存在或加载失败，绘制时会回退到手绘背景。
        """

        try:
            image = pygame.image.load(self.IMAGE_PATH).convert_alpha()
        except (FileNotFoundError, pygame.error):
            return None

        image = pygame.transform.smoothscale(image, (self.WIDTH, self.HEIGHT))
        return self._make_colorkey_friendly(image)

    def _make_colorkey_friendly(self, image: pygame.Surface) -> pygame.Surface:
        """把气泡图片处理成适合颜色键透明窗口的格式。

        当前桌宠窗口用洋红色颜色键做透明，不支持真正的半透明叠加。
        如果气泡带半透明像素，pygame 会先把它和洋红背景混色，导致黄色发紫、发灰。
        所以这里保留图片原本的 RGB 颜色，只把 alpha 压成 0 或 255。
        """

        image = image.copy()
        width, height = image.get_size()

        image.lock()
        try:
            for y in range(height):
                for x in range(width):
                    r, g, b, a = image.get_at((x, y))
                    if a <= self.ALPHA_THRESHOLD:
                        image.set_at((x, y), (r, g, b, 0))
                    else:
                        image.set_at((x, y), (r, g, b, self.ALPHA))
        finally:
            image.unlock()

        return image

    def _draw_background(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if self.background is not None:
            surface.blit(self.background, rect.topleft)
            return

        bubble_surface = pygame.Surface(rect.size, pygame.SRCALPHA)

        # 找不到素材时的兜底背景，保证程序仍然能正常显示文字。
        layers = [
            pygame.Rect(8, 8, rect.width - 16, rect.height - 16),
            pygame.Rect(2, 18, rect.width - 4, rect.height - 30),
            pygame.Rect(20, 2, rect.width - 40, rect.height - 4),
            pygame.Rect(0, 24, rect.width, rect.height - 42),
            pygame.Rect(34, 0, rect.width - 68, rect.height - 2),
        ]
        for layer in layers:
            pygame.draw.rect(bubble_surface, (*self.BG, self.ALPHA), layer, border_radius=26)

        surface.blit(bubble_surface, rect.topleft)

    def _draw_text(self, surface: pygame.Surface, bubble: pygame.Rect) -> None:
        text_surface = self.font.render(self.text, True, self.TEXT)
        text_area = pygame.Rect(
            bubble.x + self.PADDING_X,
            bubble.y + self.PADDING_Y,
            bubble.width - self.PADDING_X * 2,
            bubble.height - self.PADDING_Y * 2,
        )

        if text_surface.get_width() <= text_area.width:
            x = text_area.x + (text_area.width - text_surface.get_width()) // 2
            y = text_area.y + (text_area.height - text_surface.get_height()) // 2
            surface.blit(text_surface, (x, y))
            return

        if self.scroll_enabled:
            self._draw_scrolling_text(surface, text_surface, text_area)
        else:
            clipped = self._ellipsis_text(text_area.width)
            clipped_surface = self.font.render(clipped, True, self.TEXT)
            y = text_area.y + (text_area.height - clipped_surface.get_height()) // 2
            surface.blit(clipped_surface, (text_area.x, y))

    def _draw_scrolling_text(self, surface: pygame.Surface, text_surface: pygame.Surface, text_area: pygame.Rect) -> None:
        gap = 48
        cycle_width = text_surface.get_width() + gap
        speed = 48
        offset = int(math.floor(self.elapsed * speed)) % cycle_width
        y = text_area.y + (text_area.height - text_surface.get_height()) // 2

        previous_clip = surface.get_clip()
        surface.set_clip(text_area)
        surface.blit(text_surface, (text_area.x - offset, y))
        surface.blit(text_surface, (text_area.x - offset + cycle_width, y))
        surface.set_clip(previous_clip)

    def _ellipsis_text(self, max_width: int) -> str:
        ellipsis = "..."
        if self.font.size(self.text)[0] <= max_width:
            return self.text

        result = ""
        for char in self.text:
            candidate = result + char + ellipsis
            if self.font.size(candidate)[0] > max_width:
                break
            result += char

        return result + ellipsis if result else ellipsis
