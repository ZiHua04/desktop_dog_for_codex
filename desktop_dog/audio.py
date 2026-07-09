from __future__ import annotations

from pathlib import Path

import pygame


class SoundEffects:
    """集中管理音效。

    动画和状态机只关心“播放哪个音效”，不关心 mp3 文件在哪里、
    pygame.mixer 是否初始化成功。这样音频细节不会散落在状态类里。
    """

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._volumes: dict[str, float] = {}
        self.enabled = True
        self.master_volume = 1.0
        self._enabled = self._init_mixer()

    def load(self, name: str, path: Path, volume: float = 1.0) -> None:
        """加载一个音效，并给它起一个逻辑名字。"""

        if not self._enabled:
            return

        try:
            sound = pygame.mixer.Sound(str(path))
        except pygame.error as exc:
            print(f"音效加载失败: {path} ({exc})")
            return

        sound.set_volume(volume * self.master_volume)
        self._sounds[name] = sound
        self._volumes[name] = volume

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def set_master_volume(self, volume: float) -> None:
        self.master_volume = max(0.0, min(1.0, volume))
        for name, sound in self._sounds.items():
            sound.set_volume(self._volumes.get(name, 1.0) * self.master_volume)

    def play(self, name: str) -> None:
        """播放指定名字的音效。未加载时静默忽略。"""

        if not self.enabled:
            return

        sound = self._sounds.get(name)
        if sound is not None:
            sound.play()

    def _init_mixer(self) -> bool:
        if pygame.mixer.get_init() is not None:
            return True

        try:
            pygame.mixer.init()
        except pygame.error as exc:
            print(f"音频系统初始化失败，程序会继续运行但没有声音: {exc}")
            return False

        return True
