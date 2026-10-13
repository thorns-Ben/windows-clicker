"""
坐标查找工具 (通用)
==================
用途: 在屏幕上测量鼠标位置,把坐标填进 auto_clicker.py

使用方法:
1. 运行: python coord_finder.py
2. 鼠标移到目标元素中心,看控制台实时坐标
3. 按 R 键 -> 记录当前坐标到列表
4. 按 Ctrl+C 退出,退出时会打印所有记录的坐标

特点:
- 实时刷新,坐标不变时不重复打印
- 按 R 记录,方便多点采集
- 退出时自动汇总坐标,直接复制粘贴到脚本里
"""

import sys
import time
from datetime import datetime

import pyautogui
import ctypes

VK_R = 0x52
VK_LBUTTON = 0x01  # 左鼠标键


def is_pressed(vk_code):
    """检测某个虚拟键码是否被按下"""
    return ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000


def main():
    screen_w, screen_h = pyautogui.size()
    print("=" * 56)
    print("  坐标查找工具")
    print("=" * 56)
    print(f"  屏幕尺寸:    {screen_w} x {screen_h}")
    print(f"  坐标系原点:  屏幕左上角 (0, 0)")
    print(f"  当前时间:    {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 56)
    print("  操作:")
    print("    移动鼠标 -> 实时显示坐标")
    print("    按 R 键   -> 记录当前坐标")
    print("    Ctrl+C   -> 退出并打印汇总")
    print("=" * 56 + "\n")

    recorded = []
    last_x, last_y = -1, -1
    r_was_pressed = False  # 防抖: 避免长按 R 连续记录

    try:
        while True:
            x, y = pyautogui.position()

            # 只在坐标变化时刷新显示
            if (x, y) != (last_x, last_y):
                print(f"\r  当前坐标: x={x:>5}, y={y:>5}    ", end="")
                last_x, last_y = x, y

            # 检测 R 键按下(防抖)
            r_now = is_pressed(VK_R)
            if r_now and not r_was_pressed:
                recorded.append((x, y))
                print(f"\n  [已记录 #{len(recorded)}] x={x}, y={y}")
                print(f"\r  当前坐标: x={x:>5}, y={y:>5}    ", end="")
            r_was_pressed = r_now

            time.sleep(0.03)

    except KeyboardInterrupt:
        print("\n")
        print("=" * 56)
        print("  退出 - 记录的坐标汇总")
        print("=" * 56)
        if not recorded:
            print("  (未记录任何坐标)")
        else:
            for i, (rx, ry) in enumerate(recorded, 1):
                print(f"    坐标 {i}: x={rx}, y={ry}")
                print(f'        {{"x": {rx}, "y": {ry}, "button": "left"}},')
        print("=" * 56)
        print("\n  提示: 把坐标复制到 auto_clicker.py 的 steps 列表里")
        print("=" * 56)


if __name__ == "__main__":
    main()
