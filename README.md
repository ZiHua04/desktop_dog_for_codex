# Pygame 桌面小狗

一个用 Pygame 做的 Windows 桌宠示例。小狗会在桌面上自行待机、走路、坐下、
睡觉，也可以通过鼠标和本地 HTTP 接口控制动作，并在头顶显示对话气泡。

## 功能

- 无边框透明桌宠窗口，除小狗和菜单外不影响背后应用点击。
- 基于雪碧图和 `animations.json` 的动画资源管理。
- 状态机驱动动作切换，支持待机、走路、跑步、叫、舔、挠、坐下、趴下、睡觉等。
- 轻量自动行为层，小狗可以自己行动，也可以关闭自动行为或自动叫声。
- 鼠标交互：左键点击触发叫声，左键拖拽移动小狗，右键打开设置菜单。
- 右键菜单可切换品种、声音、音量、置顶、长文本滚动等设置。
- 本地 HTTP 后端接口，可由其他程序发送命令控制小狗。
- 支持对话气泡，文本过长时可省略或滚动显示。

## 环境

- Windows 10/11
- Python 3.11+，当前项目在 Python 3.13 下测试
- Pygame 2.x

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

## 运行

```powershell
python main.py
```

启动后会创建一个透明桌宠窗口，并同时启动本地控制服务：

```text
http://127.0.0.1:8989
```

按 `Esc` 可以退出程序。

## 鼠标操作

- 左键点击小狗：叫一声。
- 左键按住并拖动小狗：移动位置。
- 右键点击小狗：打开设置菜单，可在菜单里选择“关闭程序”退出。

## HTTP 控制

健康检查：

```powershell
curl http://127.0.0.1:8989/health
```

发送动作：

```powershell
curl -X POST http://127.0.0.1:8989/dog `
  -H "Content-Type: application/json; charset=utf-8" `
  -d "{\"command\":\"bark\"}"
```

显示文字并让小狗叫：

```powershell
curl -X POST http://127.0.0.1:8989/say `
  -H "Content-Type: application/json; charset=utf-8" `
  -d "{\"text\":\"你好，我是桌面小狗！\",\"text_duration\":5,\"command\":\"bark\"}"
```

Python 请求示例：

```python
import json
import urllib.request

payload = {
    "text": "你好，我是桌面小狗！",
    "text_duration": 5,
    "command": "bark",
}

request = urllib.request.Request(
    "http://127.0.0.1:8989/say",
    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    headers={"Content-Type": "application/json; charset=utf-8"},
    method="POST",
)

urllib.request.urlopen(request, timeout=2)
```

常用命令：

| 命令 | 说明 |
|---|---|
| `bark` | 叫一声 |
| `sit` / `sitting` | 坐下 |
| `sleep` / `sleeping` | 睡觉 |
| `lie` / `lying_down` | 趴下 |
| `itch` / `itching` | 挠痒 |
| `lick` / `licking1` | 舔 |
| `licking2` | 另一种舔动作 |
| `stretch` / `stretching` | 伸懒腰 |
| `walk_left` / `walk_right` | 向左/向右走 |
| `run_left` / `run_right` | 向左/向右跑 |

走路和跑步可以加 `duration` 控制持续时间：

```json
{"command": "walk_right", "duration": 2}
```

## 资源结构

```text
desktop_dog/                  # 桌宠源码包
examples/send_message.py      # HTTP 控制示例
assets/
  dogs/Pet Dogs Pack/
    Dog-2-Akita/
      animations.json
      Akita-Idle.png
      Akita-walk.png
      ...
  sounds/dog2a.wav
  ui/speech_bubble.png
```

每个狗狗品种目录都有自己的 `animations.json`。动画配置只描述文件名、帧率、
是否循环和帧尺寸，实际图片加载和切图由 `animation.py` 完成。

默认品种在 `settings.py` 中配置：

```python
ASSET_DIR = ASSET_ROOT / "Dog-2-Akita"
```

## 打包

项目提供了 PyInstaller 配置文件 `desktop_dog.spec`。安装依赖后执行：

```powershell
python -m PyInstaller desktop_dog.spec --clean --noconfirm
```

构建成功后，可执行文件会生成在：

```text
dist/desktop_dog/desktop_dog.exe
```

如果想生成单文件 exe：

```powershell
python -m PyInstaller desktop_dog_onefile.spec --clean --noconfirm
```

生成位置：

```text
dist/desktop_dog_onefile.exe
```

单文件版更方便分发，但首次启动会先解包资源，速度会比文件夹版慢一点。

如果只想快速打包，也可以使用：

```powershell
python -m PyInstaller main.py `
  --name desktop_dog `
  --windowed `
  --add-data "assets;assets"
```

## 常见问题

### 气泡颜色看起来发紫

当前透明窗口使用 Windows 颜色键透明方案，半透明像素会先和洋红色透明底混合。
因此气泡图片在代码里被处理成透明/不透明两档，以保证颜色更接近原图。

### 发送中文变成乱码

发送端需要用 UTF-8 读取和发送 JSON，并建议设置请求头：

```text
Content-Type: application/json; charset=utf-8
```

如果是在 Codex hook 或其他脚本里读取标准输入，优先用二进制读取后按 UTF-8 解码：

```python
raw = sys.stdin.buffer.read()
event = json.loads(raw.decode("utf-8", errors="replace"))
```

### 打包后找不到资源

项目通过 `desktop_dog/resources.py` 兼容源码运行和 PyInstaller 运行。新增资源后，需要同步加入
`desktop_dog.spec` 的 `datas` 列表。

## 许可证

狗狗素材来自 `Pet Dogs Pack`，请查看 `assets/dogs/Pet Dogs Pack/License.txt`。
