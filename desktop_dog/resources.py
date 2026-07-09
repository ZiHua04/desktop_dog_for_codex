from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative_path: str | Path) -> Path:
    """返回资源文件的真实路径。

    源码运行时，资源在项目目录下；PyInstaller 打包成 exe 后，资源会被解包到
    sys._MEIPASS。所有图片、音效、动画清单都通过这个函数定位，就不需要在业务
    代码里关心当前到底是哪种运行方式。
    """

    source_root = Path(__file__).resolve().parents[1]
    base_dir = Path(getattr(sys, "_MEIPASS", source_root))
    return base_dir / relative_path
