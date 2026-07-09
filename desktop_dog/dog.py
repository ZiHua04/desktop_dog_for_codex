from __future__ import annotations

import pygame

from .animation import AnimationClip, Animator
from .audio import SoundEffects
from .dog_states import create_dog_state_machine
from .intent import DogIntent


class Dog(pygame.sprite.Sprite):
    """狗狗实体。

    这个类负责位置、朝向、像素级命中检测和绘制所需的 image/rect。
    它不决定“下一步做什么”，那是 Brain 或鼠标交互层的职责。
    """

    def __init__(
        self,
        clips: dict[str, AnimationClip],
        pos: tuple[int, int],
        sounds: SoundEffects | None = None,
    ) -> None:
        super().__init__()
        self.sounds = sounds
        self.last_dt = 0.0
        self.animator = Animator(clips, "idle")
        self.state_machine = create_dog_state_machine()
        self.facing = 1
        self.state_machine.start(self)
        self.image = self.animator.image
        self.rect = self.image.get_rect(midbottom=pos)

    @property
    def state(self) -> str:
        return self.state_machine.current_name

    @property
    def visual_rect(self) -> pygame.Rect:
        """返回当前帧里真正有像素的区域。

        狗狗的雪碧图单帧通常有大量透明留白，如果用整张帧的 rect 给对话框定位，
        气泡会看起来离狗很远。这里按 alpha 像素计算实际可见范围，让 UI 更贴近狗狗本体。
        """

        bounds = self.image.get_bounding_rect(min_alpha=1)
        return bounds.move(self.rect.topleft)

    def change_state(self, state: str) -> None:
        self.state_machine.change(state, self)
        self._sync_image()

    def set_clips(self, clips: dict[str, AnimationClip]) -> None:
        midbottom = self.rect.midbottom
        self.animator = Animator(clips, "idle")
        self.state_machine = create_dog_state_machine()
        self.state_machine.start(self)
        self.image = self.animator.image
        self.rect = self.image.get_rect(midbottom=midbottom)

    def play_sound(self, name: str) -> None:
        if self.sounds is not None:
            self.sounds.play(name)

    def update(self, dt: float, intent: DogIntent, bounds: pygame.Rect) -> None:
        self.last_dt = dt
        self.state_machine.update(self, intent, dt, bounds)
        self._sync_image()

    def move_horizontal(self, direction: int, speed: float, dt: float, bounds: pygame.Rect) -> None:
        self.facing = direction
        self.rect.x += round(direction * speed * dt)
        self._keep_grabbable(bounds)

    def place_at(self, topleft: tuple[int, int], bounds: pygame.Rect) -> None:
        """把狗放到指定左上角，并限制在 bounds 里。

        鼠标拖拽时使用这个方法。因为保存的是左上角，所以 X/Y 都能跟随鼠标。
        """

        self.rect = self.image.get_rect(topleft=(round(topleft[0]), round(topleft[1])))
        self._keep_grabbable(bounds)

    def _keep_grabbable(self, bounds: pygame.Rect) -> None:
        visible_margin = min(48, self.rect.width // 2, self.rect.height // 2)
        if self.rect.right < bounds.left + visible_margin:
            self.rect.right = bounds.left + visible_margin
        if self.rect.left > bounds.right - visible_margin:
            self.rect.left = bounds.right - visible_margin
        if self.rect.bottom < bounds.top + visible_margin:
            self.rect.bottom = bounds.top + visible_margin
        if self.rect.top > bounds.bottom - visible_margin:
            self.rect.top = bounds.bottom - visible_margin

    def hit_test(self, pos: tuple[int, int]) -> bool:
        """像素级命中检测。

        先用 rect 粗略判断，再看点到的像素 alpha。
        为了让桌宠更容易抓住，鼠标点附近几像素内有不透明像素也算命中。
        """

        if not self.rect.collidepoint(pos):
            return False

        local_pos = (pos[0] - self.rect.x, pos[1] - self.rect.y)
        if self.image.get_at(local_pos).a > 0:
            return True

        grab_radius = 4
        width, height = self.image.get_size()
        for y in range(max(0, local_pos[1] - grab_radius), min(height, local_pos[1] + grab_radius + 1)):
            for x in range(max(0, local_pos[0] - grab_radius), min(width, local_pos[0] + grab_radius + 1)):
                if self.image.get_at((x, y)).a > 0:
                    return True

        return False

    def _sync_image(self) -> None:
        # 切换动画帧后 Surface 可能变化，用 midbottom 保持脚底位置稳定。
        midbottom = self.rect.midbottom
        image = self.animator.image
        if self.facing < 0:
            image = pygame.transform.flip(image, True, False)

        self.image = image
        self.rect = self.image.get_rect(midbottom=midbottom)
