from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pygame


@dataclass(frozen=True)
class AnimationSpec:
    """从 JSON 里读出来的动画描述。

    它只描述“资源长什么样”，不保存 pygame.Surface。
    真正的图像加载和切帧交给 AssetStore 完成。
    """

    filename: str
    fps: float = 10.0
    loop: bool = True
    frame_size: tuple[int, int] | None = None


@dataclass(frozen=True)
class AnimationClip:
    """已经加载好的动画片段。

    frames 是切好的每一帧 Surface，Animator 播放时只需要按时间取帧。
    """

    frames: list[pygame.Surface]
    fps: float
    loop: bool

    @property
    def frame_time(self) -> float:
        return 1.0 / self.fps


class AssetStore:
    """资源仓库：负责加载图片、切雪碧图、缓存 AnimationClip。

    同一个动画只加载一次，之后重复使用缓存，避免每次切换状态都读磁盘。
    """

    def __init__(self, root: Path, scale: int = 3) -> None:
        self.root = root
        self.scale = scale
        self._clips: dict[str, AnimationClip] = {}

    def load_animation(self, name: str, spec: AnimationSpec) -> AnimationClip:
        if name in self._clips:
            return self._clips[name]

        sheet = pygame.image.load(self.root / spec.filename).convert_alpha()

        # 这个资源包每一帧是 100x100，横向排列。
        # 如果 JSON 不写 frame_size，就默认按“高度 = 帧宽 = 帧高”的规则切。
        frame_width, frame_height = spec.frame_size or (sheet.get_height(), sheet.get_height())
        frame_count = sheet.get_width() // frame_width

        frames: list[pygame.Surface] = []
        for index in range(frame_count):
            rect = pygame.Rect(index * frame_width, 0, frame_width, frame_height)
            frame = pygame.Surface(rect.size, pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), rect)

            if self.scale != 1:
                scaled_size = (frame_width * self.scale, frame_height * self.scale)
                frame = pygame.transform.scale(frame, scaled_size)

            frames.append(frame)

        clip = AnimationClip(frames=frames, fps=spec.fps, loop=spec.loop)
        self._clips[name] = clip
        return clip

    def load_all(self, specs: dict[str, AnimationSpec]) -> dict[str, AnimationClip]:
        return {name: self.load_animation(name, spec) for name, spec in specs.items()}


def load_animation_specs(path: Path) -> dict[str, AnimationSpec]:
    """读取 animations.json，把纯数据转成 AnimationSpec。"""

    with path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    default_frame_size = manifest.get("default_frame_size")
    if default_frame_size is not None:
        default_frame_size = tuple(default_frame_size)

    specs: dict[str, AnimationSpec] = {}
    for name, config in manifest["animations"].items():
        frame_size = config.get("frame_size", default_frame_size)
        specs[name] = AnimationSpec(
            filename=config["file"],
            fps=config.get("fps", 10),
            loop=config.get("loop", True),
            frame_size=tuple(frame_size) if frame_size is not None else None,
        )

    return specs


class Animator:
    """动画播放器：只负责“当前动画第几帧”。不关心状态、不关心输入。"""

    def __init__(self, clips: dict[str, AnimationClip], initial: str) -> None:
        self.clips = clips
        self.current_name = initial
        self.current = clips[initial]
        self.frame_index = 0
        self.elapsed = 0.0
        self.finished = False

    @property
    def image(self) -> pygame.Surface:
        return self.current.frames[self.frame_index]

    def play(self, name: str, restart: bool = False) -> None:
        # 相同动画默认不重播，这样 walk 每帧保持连贯。
        # one-shot 动作可以传 restart=True，让它从第一帧重新开始。
        if name == self.current_name and not restart:
            return

        self.current_name = name
        self.current = self.clips[name]
        self.frame_index = 0
        self.elapsed = 0.0
        self.finished = False

    def update(self, dt: float) -> None:
        if self.finished and not self.current.loop:
            return

        self.elapsed += dt
        steps = int(self.elapsed / self.current.frame_time)
        if steps == 0:
            return

        self.elapsed %= self.current.frame_time
        self.frame_index += steps

        if self.frame_index < len(self.current.frames):
            return

        if self.current.loop:
            self.frame_index %= len(self.current.frames)
        else:
            self.frame_index = len(self.current.frames) - 1
            self.finished = True
