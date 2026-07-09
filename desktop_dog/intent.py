from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DogIntent:
    """狗狗“想做什么”的抽象表达。

    鼠标、键盘、AI、行为树都不应该直接操作状态机，而是先转成 Intent。
    状态机再根据当前状态决定这个意图能不能执行。
    """

    # 一次性动作，例如 bark、itching。通常只触发一帧，然后交给状态机播完。
    action: str | None = None

    # 持续姿态，例如 sitting、sleeping。只要 intent 持续存在，就保持这个状态。
    pose: str | None = None

    # 水平移动方向：-1 向左，0 不移动，1 向右。
    direction: int = 0

    # 是否奔跑。只有 direction 非 0 时才有意义。
    running: bool = False
