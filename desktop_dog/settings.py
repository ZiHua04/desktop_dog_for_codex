from pathlib import Path

from .resources import resource_path


# 透明色键。窗口背景会填这个颜色，Windows API 会把这个颜色变成透明。
# 这个颜色最好选资源里不会出现的纯色。
TRANSPARENT_COLOR = (255, 0, 255)

# 狗狗初始位置离屏幕底部的距离。桌宠一般从桌面下方附近出现。
START_BOTTOM_MARGIN = 0

# Bark sound effect. It is played when the dog enters the bark state.
BARK_SOUND = resource_path("assets/sounds/dog2a.wav")

# Local HTTP control server. Keep it bound to localhost by default.
CONTROL_HOST = "127.0.0.1"
CONTROL_PORT = 8989

# 资源路径只在这里定义。其他模块只关心传进来的路径，不写死具体狗狗品种。
ASSET_ROOT = resource_path("assets/dogs/Pet Dogs Pack")
ASSET_DIR = ASSET_ROOT / "Dog-2-Akita"
ANIMATION_MANIFEST = ASSET_DIR / "animations.json"
