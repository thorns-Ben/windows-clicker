"""
交互式自动连点器 (带后台运行功能)
==================================
双击 run.bat 即可启动。

交互流程:
1. 输入循环次数
2. 输入间隔秒数
3. 输入要点击几个位置
4. 鼠标移到每个位置,按 R 键自动记录坐标
5. 预览任务,确认后开始执行
6. 倒计时 5 秒后自动最小化并点击

后台运行:
- 倒计时开始后自动最小化窗口
- 按 F9 切换最小化/还原(随时查看进度)
- 进度写入日志文件 clicker_log.txt

停止方式(全部保留):
- 按 Esc: 立即停止
- 鼠标甩到屏幕左上角: 紧急终止(触发 pyautogui FAILSAFE)
- Ctrl+C: 强制退出
"""

import ctypes
import os
import sys
import time
import threading
from datetime import datetime

import pyautogui

# ==================== 安全上限(别改) ====================
MAX_LOOPS = 500
MAX_INTERVAL = 60
MAX_STEPS = 20
MAX_RUNTIME = 3600
MAX_CLICKS = 5000
COUNTDOWN = 5

# ==================== 键码常量 ====================
VK_ESCAPE = 0x1B
VK_R = 0x52
VK_F9 = 0x78

# ==================== Windows API 常量 ====================
SW_MINIMIZE = 6
SW_RESTORE = 9
WM_SYSCOMMAND = 0x0112
SC_MINIMIZE = 0xF020
SC_RESTORE = 0xF120

# ==================== 日志文件 ====================
_APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(_APP_DIR, "clicker_log.txt")

# ==================== 全局状态 ====================
_stop_flag = threading.Event()
_minimized = False  # 当前窗口是否最小化
_window_hwnd = 0    # 缓存窗口句柄


def get_async_key(vk):
    """检测虚拟键码是否被按下"""
    return ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000


def get_console_hwnd():
    """获取控制台窗口句柄,并缓存"""
    global _window_hwnd
    if _window_hwnd:
        return _window_hwnd
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        _window_hwnd = hwnd
        return hwnd
    # 回退: 尝试获取前台窗口
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if hwnd:
        _window_hwnd = hwnd
        return hwnd
    return 0


def toggle_window():
    """切换窗口最小化/还原状态"""
    global _minimized
    hwnd = get_console_hwnd()
    if not hwnd:
        print("  [警告] 无法获取控制台窗口句柄,请手动最小化")
        return

    if _minimized:
        # 还原: 用 SendMessage 发送 SC_RESTORE
        ctypes.windll.user32.SendMessageW(hwnd, WM_SYSCOMMAND, SC_RESTORE, 0)
        _minimized = False
        print("[窗口] 已还原")
    else:
        # 最小化: 用 SendMessage 发送 SC_MINIMIZE
        ctypes.windll.user32.SendMessageW(hwnd, WM_SYSCOMMAND, SC_MINIMIZE, 0)
        _minimized = True
        print("[窗口] 已最小化")


def write_log(msg):
    """写入日志文件"""
    ts = datetime.now().strftime("%H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def _hotkey_watcher():
    """后台线程: 监听 Esc(停止) 和 F9(切换窗口)"""
    esc_was_pressed = False
    f9_was_pressed = False

    while not _stop_flag.is_set():
        # Esc: 停止
        esc_now = get_async_key(VK_ESCAPE)
        if esc_now and not esc_was_pressed:
            _stop_flag.set()
            print("\n[停止信号] Esc 被按下,正在停止...")
            write_log("[停止] Esc 被按下")
            break
        esc_was_pressed = esc_now

        # F9: 切换窗口(只按下瞬间触发,防抖)
        f9_now = get_async_key(VK_F9)
        if f9_now and not f9_was_pressed:
            toggle_window()
        f9_was_pressed = f9_now

        time.sleep(0.05)


def ask_int(prompt, min_val=1, max_val=9999):
    """问一个整数,带范围校验"""
    while True:
        try:
            s = input(prompt).strip()
            if not s:
                continue
            v = int(s)
            if v < min_val:
                print(f"  不能小于 {min_val},请重新输入")
                continue
            if v > max_val:
                print(f"  不能大于 {max_val},请重新输入")
                continue
            return v
        except ValueError:
            print("  请输入数字")


def ask_float(prompt, min_val=0.0, max_val=9999.0):
    """问一个小数,带范围校验"""
    while True:
        try:
            s = input(prompt).strip()
            if not s:
                continue
            v = float(s)
            if v < min_val:
                print(f"  不能小于 {min_val},请重新输入")
                continue
            if v > max_val:
                print(f"  不能大于 {max_val},请重新输入")
                continue
            return v
        except ValueError:
            print("  请输入数字")


def collect_coords(count):
    """采集坐标: 鼠标移到位置,按 R 记录"""
    print("\n" + "=" * 56)
    print("  坐标采集模式")
    print("=" * 56)
    print("  操作: 鼠标移到目标位置 -> 按 R 键记录")
    print("  提示: 按 Esc 可取消采集并退出")
    print("=" * 56 + "\n")

    coords = []
    for i in range(1, count + 1):
        print(f"[{i}/{count}] 请把鼠标移到第 {i} 个点击位置,然后按 R 键记录...")
        recorded = False
        while not recorded:
            if _stop_flag.is_set():
                return None

            if get_async_key(VK_R):
                x, y = pyautogui.position()
                coords.append((x, y))
                print(f"  [已记录] x={x}, y={y}\n")
                write_log(f"[采集] 第 {i} 个坐标: ({x}, {y})")
                recorded = True
                time.sleep(0.3)  # 防抖
            time.sleep(0.03)
    return coords


def countdown(seconds):
    """倒计时"""
    for i in range(seconds, 0, -1):
        print(f"  {i} 秒后开始... (按 Esc 取消)")
        time.sleep(1)
        if _stop_flag.is_set():
            return False
    return True


def run_clicker(loops, interval, coords):
    """执行点击任务"""
    steps = len(coords)
    total_clicks = steps * loops
    est_time = total_clicks * interval + total_clicks * 0.3

    print("\n" + "=" * 56)
    print("  任务预览")
    print("=" * 56)
    print(f"  循环次数:  {loops} 轮")
    print(f"  间隔时间:  {interval} 秒")
    print(f"  点击位置:  {steps} 个")
    print(f"  总点击数:  {total_clicks} 次")
    print(f"  预计耗时:  ~{est_time:.1f} 秒")
    print("-" * 56)
    for i, (x, y) in enumerate(coords, 1):
        print(f"    位置 {i}: ({x}, {y})")
    print("=" * 56)
    print("  提示: 按 F9 切换最小化/还原,查看进度")
    print(f"  日志文件: {LOG_FILE}")
    print("=" * 56 + "\n")

    ans = input("是否开始? (y/N): ").strip().lower()
    if ans not in ("y", "yes"):
        print("[取消] 用户取消")
        write_log("[取消] 用户取消任务")
        return False, 0, "用户取消"

    # 启动热键监听
    watcher = threading.Thread(target=_hotkey_watcher, daemon=True)
    watcher.start()

    write_log("=" * 40)
    write_log(f"[开始] 循环 {loops} 轮, 间隔 {interval}s, {steps} 个位置")
    write_log(f"[位置] {coords}")

    print("\n[开始] 倒计时...")
    if not countdown(COUNTDOWN):
        write_log("[停止] 倒计时阶段取消")
        return False, 0, "倒计时阶段取消"

    # 倒计时结束,自动最小化
    print("\n[自动最小化] 5 秒后开始点击,窗口将最小化到任务栏")
    print("  按 F9 可随时还原窗口查看进度")
    write_log("[最小化] 自动最小化窗口")
    time.sleep(1)
    toggle_window()

    print(f"\n[执行] 共 {loops} 轮\n")
    start_time = time.time()
    click_count = 0

    for loop_idx in range(loops):
        elapsed = time.time() - start_time
        if elapsed > MAX_RUNTIME:
            write_log(f"[停止] 超过运行时间上限")
            return False, click_count, f"超过运行时间上限 {MAX_RUNTIME}s"
        if click_count >= MAX_CLICKS:
            write_log(f"[停止] 超过点击数上限")
            return False, click_count, f"超过点击数上限 {MAX_CLICKS}"
        if _stop_flag.is_set():
            write_log(f"[停止] 用户按 Esc 停止")
            return False, click_count, "用户按 Esc 停止"

        print(f"[轮次 {loop_idx+1}/{loops}]  (已运行 {elapsed:.1f}s)")
        write_log(f"[轮次] {loop_idx+1}/{loops}")

        for step_idx, (x, y) in enumerate(coords):
            if _stop_flag.is_set():
                write_log(f"[停止] 用户按 Esc 停止")
                return False, click_count, "用户按 Esc 停止"

            click_count += 1
            print(f"    点击位置 {step_idx+1}/{steps}: ({x}, {y})  累计 {click_count}")
            write_log(f"[点击] {step_idx+1}/{steps} 坐标({x},{y}) 累计{click_count}")
            pyautogui.moveTo(x, y, duration=0.3, _pause=False)
            pyautogui.click(_pause=False)
            time.sleep(interval)

    elapsed = time.time() - start_time
    write_log(f"[完成] 全部完成,耗时 {elapsed:.1f}s, 共 {click_count} 次点击")
    return True, click_count, f"全部完成,耗时 {elapsed:.1f}s"


def main():
    print("\n" + "=" * 56)
    print("  交互式自动连点器")
    print("=" * 56)
    print(f"  启动时间: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 56)
    print("  操作提示:")
    print("    R 键: 采集坐标时记录")
    print("    F9 键: 切换窗口最小化/还原")
    print("    Esc 键: 立即停止")
    print("    鼠标到左上角: 紧急终止")
    print("=" * 56 + "\n")

    # 清空日志文件
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 日志开始\n")

    # 步骤 1: 循环次数
    loops = ask_int(f"[1/3] 请输入循环次数 (1-{MAX_LOOPS}): ", 1, MAX_LOOPS)

    # 步骤 2: 间隔秒数
    interval = ask_float(f"[2/3] 请输入间隔秒数 (0.1-{MAX_INTERVAL}): ", 0.1, MAX_INTERVAL)

    # 步骤 3: 坐标数量
    step_count = ask_int(f"[3/3] 请输入要点击的位置数量 (1-{MAX_STEPS}): ", 1, MAX_STEPS)

    # 步骤 4: 采集坐标
    coords = collect_coords(step_count)
    if coords is None:
        print("\n[退出] 采集阶段取消")
        write_log("[退出] 采集阶段取消")
        return

    # 步骤 5: 执行
    try:
        completed, clicks, reason = run_clicker(loops, interval, coords)
    except pyautogui.FailSafeException:
        print("\n[紧急停止] 鼠标移到左上角触发 FAILSAFE")
        write_log("[紧急停止] FAILSAFE 触发")
        completed, clicks, reason = False, 0, "FAILSAFE"
    except Exception as e:
        print(f"\n[异常] {type(e).__name__}: {e}")
        write_log(f"[异常] {type(e).__name__}: {e}")
        completed, clicks, reason = False, 0, f"异常: {e}"
    finally:
        _stop_flag.set()
        # 结束时还原窗口
        if _minimized:
            toggle_window()

    # 结束报告
    print("\n" + "=" * 56)
    print(f"  状态: {'成功完成' if completed else '提前停止'}")
    print(f"  原因: {reason}")
    print(f"  点击: {clicks} 次")
    print(f"  结束: {datetime.now().strftime('%H:%M:%S')}")
    print(f"  日志: {LOG_FILE}")
    print("=" * 56)
    print("\n按 Enter 键退出...")
    try:
        input()
    except EOFError:
        pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[中断] Ctrl+C 退出")
        sys.exit(130)
