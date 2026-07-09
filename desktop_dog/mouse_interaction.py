from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from .intent import DogIntent

if TYPE_CHECKING:
    from .dog import Dog


class DogMouseInteractor:
    """把鼠标事件翻译成狗狗交互。

    左键短点：触发 bark。
    左键拖拽：直接移动狗的位置，并暂停自动行为。
    右键点击：触发 licking1。
    """

    def __init__(self, drag_threshold: int = 8) -> None:
        self.drag_threshold_squared = drag_threshold * drag_threshold
        self.active = False
        self.dragging = False
        self.down_pos = (0, 0)
        self.drag_offset = (0, 0)
        self.pending_intent: DogIntent | None = None
        self.context_menu_pos: tuple[int, int] | None = None

    def handle_event(self, event: pygame.event.Event, dog: Dog, bounds: pygame.Rect) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN:
            return self._handle_button_down(event, dog)

        if event.type == pygame.MOUSEMOTION and self.active:
            self._handle_motion(event, dog, bounds)
            return True

        if event.type == pygame.MOUSEBUTTONUP and self.active and event.button == 1:
            self._handle_button_up(event, dog, bounds)
            return True

        return False

    def update(self, dog: Dog, bounds: pygame.Rect) -> None:
        """拖拽兜底更新。

        有些窗口透传/焦点切换场景里，pygame 可能漏掉 MOUSEBUTTONUP。
        每帧检查左键状态，能避免 active 永远卡住。
        """

        if not self.active:
            return

        if pygame.mouse.get_pressed(num_buttons=3)[0]:
            pos = pygame.mouse.get_pos()
            if self.dragging:
                dog.place_at(self._event_to_dog_topleft(pos), bounds)
        else:
            self.active = False
            self.dragging = False

    def consume_intent(self) -> DogIntent | None:
        """取走待处理的鼠标意图。

        这里用 consume 模式，是为了保证一次点击只触发一次动作。
        """

        intent = self.pending_intent
        self.pending_intent = None
        return intent

    def _handle_button_down(self, event: pygame.event.Event, dog: Dog) -> bool:
        if not dog.hit_test(event.pos):
            return False

        if event.button == 1:
            self.active = True
            self.dragging = False
            self.down_pos = event.pos

            # 记录鼠标按下点相对狗左上角的位置。
            # 后续拖拽时用这个偏移量还原位置，狗不会突然跳到鼠标中心。
            self.drag_offset = (event.pos[0] - dog.rect.x, event.pos[1] - dog.rect.y)
            return True

        if event.button == 3:
            self.context_menu_pos = event.pos
            return True

        return False

    def _handle_motion(self, event: pygame.event.Event, dog: Dog, bounds: pygame.Rect) -> None:
        if not self.dragging and self._moved_past_threshold(event.pos):
            self.dragging = True
            dog.change_state("idle")

        if self.dragging:
            dog.place_at(self._event_to_dog_topleft(event.pos), bounds)

    def _handle_button_up(self, event: pygame.event.Event, dog: Dog, bounds: pygame.Rect) -> None:
        if self.dragging:
            dog.place_at(self._event_to_dog_topleft(event.pos), bounds)
        else:
            self.pending_intent = DogIntent(action="bark")

        self.active = False
        self.dragging = False

    def consume_context_menu_pos(self) -> tuple[int, int] | None:
        pos = self.context_menu_pos
        self.context_menu_pos = None
        return pos

    def _event_to_dog_topleft(self, pos: tuple[int, int]) -> tuple[int, int]:
        return pos[0] - self.drag_offset[0], pos[1] - self.drag_offset[1]

    def _moved_past_threshold(self, pos: tuple[int, int]) -> bool:
        dx = pos[0] - self.down_pos[0]
        dy = pos[1] - self.down_pos[1]
        return dx * dx + dy * dy >= self.drag_threshold_squared
