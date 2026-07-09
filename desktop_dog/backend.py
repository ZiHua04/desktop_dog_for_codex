from __future__ import annotations

import json
import queue
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .intent import DogIntent
from .text_utils import sanitize_text


@dataclass(frozen=True)
class ControlCommand:
    """后端传给 pygame 主循环的控制命令。

    intent 表示狗要做什么；duration 表示这个意图要持续多久。
    bark 这类 one-shot 动作通常不需要持续时间，走路/跑步则适合传 duration。
    """

    intent: DogIntent
    duration: float = 0.0
    text: str | None = None
    text_duration: float = 5.0


ACTION_COMMANDS = {
    "bark": DogIntent(action="bark"),
    "itch": DogIntent(action="itching"),
    "itching": DogIntent(action="itching"),
    "lick": DogIntent(action="licking1"),
    "licking1": DogIntent(action="licking1"),
    "licking2": DogIntent(action="licking2"),
    "lie": DogIntent(action="lying_down"),
    "lying_down": DogIntent(action="lying_down"),
    "stretch": DogIntent(action="stretching"),
    "stretching": DogIntent(action="stretching"),
}

POSE_COMMANDS = {
    "idle": DogIntent(),
    "sit": DogIntent(pose="sitting"),
    "sitting": DogIntent(pose="sitting"),
    "sleep": DogIntent(pose="sleeping"),
    "sleeping": DogIntent(pose="sleeping"),
}

MOVE_COMMANDS = {
    "walk_left": DogIntent(direction=-1),
    "walk_right": DogIntent(direction=1),
    "run_left": DogIntent(direction=-1, running=True),
    "run_right": DogIntent(direction=1, running=True),
}


class DogControlServer:
    """本地 HTTP 控制服务。

    服务运行在后台线程里。请求线程只负责把命令放入 Queue，
    pygame 主线程每帧从 Queue 取命令并更新狗，避免跨线程直接操作游戏对象。
    """

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._queue: queue.Queue[ControlCommand] = queue.Queue()
        self._server = ThreadingHTTPServer((host, port), self._make_handler())
        self.port = self._server.server_port
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=1.0)

    def poll_command(self) -> ControlCommand | None:
        """从队列里取一条命令；没有命令时返回 None。"""

        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        command_queue = self._queue

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/health":
                    self._send_json(200, {"ok": True})
                else:
                    self._send_json(404, {"ok": False, "error": "unknown endpoint"})

            def do_POST(self) -> None:
                if self.path not in {"/intent", "/dog", "/say"}:
                    self._send_json(404, {"ok": False, "error": "unknown endpoint"})
                    return

                try:
                    payload = self._read_json()
                    command = payload_to_command(payload)
                except ValueError as exc:
                    self._send_json(400, {"ok": False, "error": str(exc)})
                    return

                command_queue.put(command)
                self._send_json(200, {"ok": True})

            def log_message(self, format: str, *args: Any) -> None:
                # 桌宠程序不需要每个请求都刷控制台日志。
                pass

            def _read_json(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                if not raw:
                    return {}

                try:
                    payload = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    raise ValueError("body must be valid JSON") from exc

                if not isinstance(payload, dict):
                    raise ValueError("body must be a JSON object")

                return payload

            def _send_json(self, status: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return Handler


def payload_to_command(payload: dict[str, Any]) -> ControlCommand:
    """把 HTTP 请求体转成 ControlCommand。

    支持两种写法：
    1. {"command": "bark"}
    2. {"action": "bark"} / {"pose": "sitting"} / {"direction": 1, "duration": 2}
    """

    duration = _read_duration(payload)
    duration_was_provided = "duration" in payload
    text = _read_text(payload)
    text_duration = _read_text_duration(payload)
    command = payload.get("command")

    if isinstance(command, str):
        intent = _intent_from_command(command)
        if not duration_was_provided:
            duration = _default_duration_for_intent(intent)
        return ControlCommand(intent=intent, duration=duration, text=text, text_duration=text_duration)

    action = payload.get("action")
    if action is not None:
        if not isinstance(action, str):
            raise ValueError("action must be a string")
        normalized = action.strip().lower()
        if normalized not in ACTION_COMMANDS:
            raise ValueError(f"unknown action: {action}")
        intent = ACTION_COMMANDS[normalized]
        if not duration_was_provided:
            duration = _default_duration_for_intent(intent)
        return ControlCommand(intent=intent, duration=duration, text=text, text_duration=text_duration)

    pose = payload.get("pose")
    if pose is not None:
        if not isinstance(pose, str):
            raise ValueError("pose must be a string")
        normalized = pose.strip().lower()
        if normalized not in POSE_COMMANDS:
            raise ValueError(f"unknown pose: {pose}")
        intent = POSE_COMMANDS[normalized]
        if not duration_was_provided:
            duration = _default_duration_for_intent(intent)
        return ControlCommand(intent=intent, duration=duration, text=text, text_duration=text_duration)

    direction = payload.get("direction", 0)
    running = bool(payload.get("running", False))
    if direction not in {-1, 0, 1}:
        raise ValueError("direction must be -1, 0, or 1")

    intent = DogIntent(direction=direction, running=running)
    if not duration_was_provided:
        duration = _default_duration_for_intent(intent)
    return ControlCommand(intent=intent, duration=duration, text=text, text_duration=text_duration)


def _intent_from_command(command: str) -> DogIntent:
    normalized = command.strip().lower()
    if normalized in ACTION_COMMANDS:
        return ACTION_COMMANDS[normalized]
    if normalized in POSE_COMMANDS:
        return POSE_COMMANDS[normalized]
    if normalized in MOVE_COMMANDS:
        return MOVE_COMMANDS[normalized]
    raise ValueError(f"unknown command: {command}")


def _read_duration(payload: dict[str, Any]) -> float:
    raw = payload.get("duration", 0.0)
    if raw is None:
        return 0.0

    try:
        duration = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("duration must be a number") from exc

    if duration < 0:
        raise ValueError("duration must be >= 0")

    return duration


def _read_text(payload: dict[str, Any]) -> str | None:
    raw = payload.get("text")
    if raw is None:
        raw = payload.get("message")
    if raw is None:
        raw = payload.get("say")

    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError("text must be a string")

    text = sanitize_text(raw)
    return text or None


def _read_text_duration(payload: dict[str, Any]) -> float:
    raw = payload.get("text_duration", payload.get("say_duration", 5.0))
    try:
        duration = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("text_duration must be a number") from exc

    if duration < 1:
        raise ValueError("text_duration must be >= 1")

    return duration


def _default_duration_for_intent(intent: DogIntent) -> float:
    if intent.pose == "sitting":
        return 6.0
    if intent.pose == "sleeping":
        return 10.0
    if intent.direction:
        return 2.0
    return 0.0
