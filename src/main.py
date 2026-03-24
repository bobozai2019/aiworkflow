"""
应用主入口

启动PyQt GUI界面或命令行界面。
"""

from __future__ import annotations

import sys


def main():
    """主入口"""
    if len(sys.argv) > 1:
        from src.cli import main as cli_main
        cli_main()
    else:
        from src.ui import run_gui
        run_gui()


if __name__ == "__main__":
    main()
