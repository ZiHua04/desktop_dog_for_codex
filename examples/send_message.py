#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request


def send_message(text: str, command: str = "bark", text_duration: float = 5.0) -> None:
    payload = {
        "text": text,
        "text_duration": text_duration,
        "command": command,
    }

    request = urllib.request.Request(
        "http://127.0.0.1:8989/say",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    urllib.request.urlopen(request, timeout=2).close()


if __name__ == "__main__":
    import time
    # time.sleep(5)
    send_message("你好，我是桌面小狗！")
