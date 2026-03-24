#!/usr/bin/env python
"""
Multi-Agent System 启动器
直接启动PyQt GUI界面
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui import run_gui

if __name__ == "__main__":
    run_gui()
