from __future__ import annotations

import os

import pygame

from desktop_dog.animation import AssetStore, load_animation_specs
from desktop_dog.audio import SoundEffects
from desktop_dog.backend import ControlCommand, DogControlServer
from desktop_dog.desktop_geometry import get_virtual_desktop_rect
from desktop_dog.desktop_window import DesktopPetWindow
from desktop_dog.dog import Dog
from desktop_dog.dog_brain import AutonomousDogBrain
from desktop_dog.intent import DogIntent
from desktop_dog.mouse_interaction import DogMouseInteractor
from desktop_dog.settings_menu import MenuAction, PetSettings, SettingsMenu, discover_breeds
from desktop_dog.speech_bubble import SpeechBubble
from desktop_dog.settings import (
    ASSET_DIR,
    BARK_SOUND,
    CONTROL_HOST,
    CONTROL_PORT,
    START_BOTTOM_MARGIN,
    TRANSPARENT_COLOR,
)


def main() -> None:
    # 让无边框桌宠窗口从屏幕左上角开始铺满整个桌面。
    # 必须在 display.set_mode 之前设置，SDL 才会读取这个位置。
    virtual_desktop = get_virtual_desktop_rect()
    os.environ.setdefault("SDL_VIDEO_WINDOW_POS", f"{virtual_desktop.x},{virtual_desktop.y}")

    pygame.init()

    desktop_size = virtual_desktop.size

    # 用一个覆盖桌面的无边框窗口承载桌宠。
    # 背景区域会被 Windows 颜色键变成透明，并且鼠标会透传给背后的应用。
    screen = pygame.display.set_mode(desktop_size, pygame.NOFRAME)
    pygame.display.set_caption("Akita sprite animation")
    clock = pygame.time.Clock()
    desktop_window = DesktopPetWindow(screen, TRANSPARENT_COLOR)

    sounds = SoundEffects()
    sounds.load("bark", BARK_SOUND, volume=0.9)

    breeds = discover_breeds(ASSET_DIR.parent)
    settings = PetSettings()
    for index, breed in enumerate(breeds):
        if breed.asset_dir == ASSET_DIR:
            settings.dog_index = index
            break

    menu = SettingsMenu(breeds, settings)
    speech_bubble = SpeechBubble()
    speech_bubble.scroll_enabled = settings.speech_scroll
    sounds.set_enabled(settings.sound_enabled)
    sounds.set_master_volume(settings.volume)

    def load_breed_clips(asset_dir):
        assets = AssetStore(asset_dir, scale=3)
        animation_specs = load_animation_specs(asset_dir / "animations.json")
        return assets.load_all(animation_specs)

    dog = Dog(
        load_breed_clips(menu.current_breed.asset_dir),
        pos=(desktop_size[0] // 2, desktop_size[1] - START_BOTTOM_MARGIN),
        sounds=sounds,
    )
    desktop_window.set_hit_test(lambda pos: dog.hit_test(pos) or menu.hit_test(pos))

    brain = AutonomousDogBrain()
    brain.auto_behavior_enabled = settings.auto_behavior
    brain.auto_bark_enabled = settings.auto_bark
    mouse = DogMouseInteractor()
    control_server = DogControlServer(CONTROL_HOST, CONTROL_PORT)
    control_server.start()
    print(f"Dog control server: {control_server.url}/intent")
    sprites = pygame.sprite.Group(dog)

    # 桌宠可以在整个桌面范围内拖动。
    world_bounds = screen.get_rect()

    running = True
    remote_command: ControlCommand | None = None
    remote_time_left = 0.0

    def apply_menu_action(action: MenuAction) -> None:
        nonlocal remote_command, remote_time_left, running

        if action.kind == "next_breed":
            settings.dog_index = (settings.dog_index + 1) % len(breeds)
            dog.set_clips(load_breed_clips(menu.current_breed.asset_dir))
        elif action.kind == "toggle_auto_behavior":
            settings.auto_behavior = not settings.auto_behavior
            brain.auto_behavior_enabled = settings.auto_behavior
            brain.hold(0.5)
        elif action.kind == "toggle_auto_bark":
            settings.auto_bark = not settings.auto_bark
            brain.auto_bark_enabled = settings.auto_bark
        elif action.kind == "toggle_sound":
            settings.sound_enabled = not settings.sound_enabled
            sounds.set_enabled(settings.sound_enabled)
        elif action.kind == "volume":
            levels = [0.0, 0.25, 0.5, 0.75, 1.0]
            current = min(range(len(levels)), key=lambda index: abs(levels[index] - settings.volume))
            settings.volume = levels[(current + 1) % len(levels)]
            sounds.set_master_volume(settings.volume)
        elif action.kind == "toggle_topmost":
            settings.always_on_top = not settings.always_on_top
            desktop_window.set_topmost(settings.always_on_top)
        elif action.kind == "toggle_speech_scroll":
            settings.speech_scroll = not settings.speech_scroll
            speech_bubble.scroll_enabled = settings.speech_scroll
        elif action.kind == "bark":
            remote_command = ControlCommand(DogIntent(action="bark"), duration=0.0)
            remote_time_left = 0.0
        elif action.kind == "sit":
            remote_command = ControlCommand(DogIntent(pose="sitting"), duration=6.0)
            remote_time_left = 6.0
        elif action.kind == "sleep":
            remote_command = ControlCommand(DogIntent(pose="sleeping"), duration=10.0)
            remote_time_left = 10.0
        elif action.kind == "quit":
            running = False

    try:
        while running:
            dt = clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                elif menu.visible:
                    action = menu.handle_event(event)
                    if action is not None:
                        apply_menu_action(action)
                else:
                    mouse.handle_event(event, dog, world_bounds)

            mouse.update(dog, world_bounds)

            menu_pos = mouse.consume_context_menu_pos()
            if menu_pos is not None:
                menu.open(menu_pos, world_bounds)
                brain.hold(0.5)

            # 鼠标交互优先级高于自动行为：
            # 1. 拖拽中：狗不执行新动作，只更新当前动画帧；
            # 2. 鼠标点击：把点击翻译成 DogIntent；
            # 3. 没有鼠标交互：交给自动行为层自己决定。
            server_command = control_server.poll_command()
            if server_command is not None:
                if server_command.text is not None:
                    speech_bubble.show(server_command.text, server_command.text_duration)
                remote_command = server_command
                remote_time_left = server_command.duration

            mouse_intent = mouse.consume_intent()
            if mouse.active:
                brain.hold(0.5)
                intent = DogIntent()
            elif remote_command is not None:
                brain.hold(1.0)
                intent = remote_command.intent
                if remote_time_left > 0:
                    remote_time_left -= dt
                    if remote_time_left <= 0:
                        remote_command = None
                else:
                    remote_command = None
            elif mouse_intent is not None:
                brain.hold(1.0)
                intent = mouse_intent
            else:
                intent = brain.update(dog, dt, world_bounds)

            dog.update(dt, intent, world_bounds)
            speech_bubble.update(dt)

            desktop_window.clear()
            sprites.draw(screen)
            speech_bubble.draw(screen, dog.visual_rect, dog.facing)
            menu.draw(screen)
            pygame.display.flip()
    finally:
        control_server.stop()
        desktop_window.close()

    pygame.quit()


if __name__ == "__main__":
    main()
