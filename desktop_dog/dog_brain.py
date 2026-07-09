from __future__ import annotations

import random
from typing import TYPE_CHECKING

import pygame

from .intent import DogIntent

if TYPE_CHECKING:
    from .dog import Dog


class AutonomousDogBrain:
    """狗狗的自动行为层。

    这里不是完整行为树，而是一个轻量的随机行为选择器。
    它只产出 DogIntent，不直接改动画、不直接改状态。
    """

    AUTO_ONE_SHOT_ACTIONS = ("itching", "licking1", "licking2", "lying_down", "stretching")
    BLOCKING_STATES = {"bark", *AUTO_ONE_SHOT_ACTIONS}

    def __init__(self) -> None:
        self.rng = random.Random()
        self.intent = DogIntent()
        self.time_left = 0.0
        self.auto_behavior_enabled = True
        self.auto_bark_enabled = False

    def hold(self, duration: float) -> None:
        """暂停自动行为一小段时间。

        鼠标点击或拖拽后调用它，避免狗刚被用户操作完就立刻自己跑走。
        """

        self.intent = DogIntent()
        self.time_left = max(self.time_left, duration)

    def update(self, dog: Dog, dt: float, bounds: pygame.Rect) -> DogIntent:
        if not self.auto_behavior_enabled:
            self.intent = DogIntent()
            return DogIntent()

        # one-shot 动作播放期间，AI 不再发新意图，等状态机自动回 idle。
        if dog.state in self.BLOCKING_STATES:
            self.intent = DogIntent()
            return DogIntent()

        self.time_left -= dt
        if self.time_left <= 0 or self._walking_into_edge(dog, bounds):
            self.intent, self.time_left = self._choose_next_intent(dog, bounds)

        # 一次性动作必须像“脉冲”一样只发出一帧。
        # 否则动画播完回 idle 后，会立刻再次进入同一个动作。
        if self.intent.action is not None:
            action_intent = self.intent
            self.intent = DogIntent()
            self.time_left = self.rng.uniform(0.8, 2.0)
            return action_intent

        return self.intent

    def _walking_into_edge(self, dog: Dog, bounds: pygame.Rect) -> bool:
        margin = 24
        if self.intent.direction < 0:
            return dog.rect.left <= bounds.left + margin
        if self.intent.direction > 0:
            return dog.rect.right >= bounds.right - margin
        return False

    def _choose_next_intent(self, dog: Dog, bounds: pygame.Rect) -> tuple[DogIntent, float]:
        # 每个选项包含：意图、持续时间范围、权重。
        options: list[tuple[DogIntent, tuple[float, float], float]] = [
            (DogIntent(), (0.8, 2.4), 4),
            (DogIntent(pose="sitting"), (4.0, 8.0), 2),
            (DogIntent(pose="sleeping"), (6.0, 12.0), 1),
        ]

        # 靠近左右边缘时，只把“往回走”的方向加入候选，避免一直撞边。
        directions = []
        if dog.rect.centerx > bounds.left + bounds.width * 0.2:
            directions.append(-1)
        if dog.rect.centerx < bounds.right - bounds.width * 0.2:
            directions.append(1)

        for direction in directions:
            options.append((DogIntent(direction=direction), (1.0, 3.0), 4))
            options.append((DogIntent(direction=direction, running=True), (0.5, 1.2), 1))

        one_shot_actions = list(self.AUTO_ONE_SHOT_ACTIONS)
        if self.auto_bark_enabled:
            one_shot_actions.append("bark")

        for action in one_shot_actions:
            delay = (3.0, 6.0) if action == "lying_down" else (0.0, 0.0)
            options.append((DogIntent(action=action), delay, 1))

        duration_ranges = [option[1] for option in options]
        weights = [option[2] for option in options]
        index = self.rng.choices(range(len(options)), weights=weights, k=1)[0]
        duration = self.rng.uniform(*duration_ranges[index])
        return options[index][0], duration
