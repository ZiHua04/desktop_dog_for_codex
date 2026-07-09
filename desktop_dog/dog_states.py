from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from .intent import DogIntent

if TYPE_CHECKING:
    from .dog import Dog


def choose_interruptible_state(intent: DogIntent) -> str:
    """把 Intent 翻译成状态名。

    优先级是：一次性动作 > 移动 > 姿态 > idle。
    这个函数只给“可打断状态”使用；one-shot 动作播放期间不会被这里打断。
    """

    if intent.action is not None:
        return intent.action

    if intent.direction:
        return "run" if intent.running else "walk"

    if intent.pose is not None:
        return intent.pose

    return "idle"


class DogState:
    """单个动作状态的基类。

    状态对象负责描述：
    1. 进入状态时播放哪个动画；
    2. 每帧是否要切到别的状态；
    3. 动画播完后要不要自动跳转。
    """

    restart_on_enter = False

    def __init__(self, name: str, animation: str | None = None, sound: str | None = None) -> None:
        self.name = name
        self.animation = animation or name
        self.sound = sound

    def enter(self, dog: Dog) -> None:
        dog.animator.play(self.animation, restart=self.restart_on_enter)
        if self.sound is not None:
            dog.play_sound(self.sound)

    def exit(self, dog: Dog) -> None:
        pass

    def update(self, dog: Dog, intent: DogIntent, dt: float, bounds: pygame.Rect) -> str | None:
        return None

    def after_animation(self, dog: Dog) -> str | None:
        return None


class InterruptibleState(DogState):
    """可以随时响应新 Intent 的状态，例如 idle、sitting、sleeping。"""

    def update(self, dog: Dog, intent: DogIntent, dt: float, bounds: pygame.Rect) -> str | None:
        next_state = choose_interruptible_state(intent)
        if next_state == self.name:
            return None
        return next_state


class MoveState(DogState):
    """移动状态。状态本身知道移动速度，具体位移交给 Dog 实体处理。"""

    def __init__(self, name: str, speed: float) -> None:
        super().__init__(name)
        self.speed = speed

    def update(self, dog: Dog, intent: DogIntent, dt: float, bounds: pygame.Rect) -> str | None:
        next_state = choose_interruptible_state(intent)
        if next_state != self.name:
            return next_state

        dog.move_horizontal(intent.direction, self.speed, dt, bounds)
        return None


class OneShotState(DogState):
    """一次性动作，例如叫、挠痒、伸懒腰。

    进入时强制从第一帧播放，播放完自动回到 idle。
    """

    restart_on_enter = True

    def after_animation(self, dog: Dog) -> str | None:
        if dog.animator.finished:
            return "idle"
        return None


class TimedOneShotState(OneShotState):
    """一次性动画播放完后，在最后一帧多停留一段时间。"""

    def __init__(
        self,
        name: str,
        hold_seconds: float,
        animation: str | None = None,
        sound: str | None = None,
    ) -> None:
        super().__init__(name, animation=animation, sound=sound)
        self.hold_seconds = hold_seconds
        self.elapsed_after_finish = 0.0

    def enter(self, dog: Dog) -> None:
        self.elapsed_after_finish = 0.0
        super().enter(dog)

    def after_animation(self, dog: Dog) -> str | None:
        if not dog.animator.finished:
            return None

        self.elapsed_after_finish += dog.last_dt
        if self.elapsed_after_finish >= self.hold_seconds:
            return "idle"

        return None


class StateMachine:
    """轻量状态机。

    它不负责选择“应该做什么”，只负责安全地执行状态切换。
    自动行为、鼠标交互、键盘控制都应该先生成 DogIntent。
    """

    def __init__(self, states: dict[str, DogState], initial: str) -> None:
        self.states = states
        self.current_name = initial
        self.current = states[initial]

    def start(self, dog: Dog) -> None:
        self.current.enter(dog)

    def change(self, name: str, dog: Dog) -> None:
        if name == self.current_name:
            return
        if name not in self.states:
            raise KeyError(f"Unknown dog state: {name}")

        self.current.exit(dog)
        self.current_name = name
        self.current = self.states[name]
        self.current.enter(dog)

    def update(self, dog: Dog, intent: DogIntent, dt: float, bounds: pygame.Rect) -> None:
        next_state = self.current.update(dog, intent, dt, bounds)
        if next_state is not None:
            self.change(next_state, dog)

        dog.animator.update(dt)

        next_state = self.current.after_animation(dog)
        if next_state is not None:
            self.change(next_state, dog)


def create_dog_state_machine() -> StateMachine:
    """组装狗狗可用的全部状态。后面加动作时主要改这里。"""

    return StateMachine(
        {
            "idle": InterruptibleState("idle"),
            "walk": MoveState("walk", speed=130),
            "run": MoveState("run", speed=260),
            "sitting": InterruptibleState("sitting"),
            "sleeping": InterruptibleState("sleeping"),
            "bark": OneShotState("bark", sound="bark"),
            "itching": OneShotState("itching"),
            "licking1": OneShotState("licking1"),
            "licking2": OneShotState("licking2"),
            "lying_down": TimedOneShotState("lying_down", hold_seconds=4.0),
            "stretching": OneShotState("stretching"),
        },
        initial="idle",
    )
