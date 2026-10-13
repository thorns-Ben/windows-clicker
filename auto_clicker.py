"""
自动连点器 (Python + PyAutoGUI)
================================
功能:
- 按配置的坐标序列循环点击指定次数
- 每个动作之间固定间隔(无随机抖动)
- Esc 全局停止(任意时刻,后台线程监听)
- 启动前 5 秒倒计时,可取消
- 多种安全上限,防死循环

安全防线(你担心的"无限循环"问题):
1. MAX_LOOPS_ABSOLUTE: 循环轮次硬上限,改配置文件也没用
2. MAX_RUNTIME_ABSOLUTE: 总运行时间硬上限
3. MAX_TOTAL_CLICKS: 总点击数硬上限
4. Esc 全局热键: 后台线程监听,无需焦点
5. 启动前 5 秒倒计时,方便切窗口
6. pyautogui 自带 FAILSAFE: 鼠标移到屏幕左上角(0,0)会抛异常强制终止
7. dry_run 模式: 只打印不真点击,先验证流程
"""

import ctypes
import sys
import time
import threading
from datetime import datetime

import pyautogui

# ==================== 安全配置(改这里前先想清楚) ====================
MAX_LOOPS_ABSOLUTE = 500      # 最多 500 轮,即使配置写错也不会超
MAX_RUNTIME_ABSOLUTE = 3600   # 最多跑 1 小时
MAX_TOTAL_CLICKS = 5000       # 最多点 5000 次
COUNTDOWN_SECONDS = 5         # 启动倒计时秒数

# ==================== 任务配置(改这里) ====================
# 你只需要改下面 TASK = {} 里的数字,改完保存再运行脚本即可
TASK = {
    "loops": 10,              # 循环次数: 想点几轮就写几,比如 5/10/20/90
    "interval": 1.0,         # 间隔秒数: 每个动作之间等多久,比如 1.0(1秒)/2.0(2秒)/0.5(半秒)
    "move_duration": 0.1,    # 鼠标缓动秒数: 鼠标从当前位置飞到目标位置花的时间
                             #   0.0 = 瞬间闪现(最快); 0.3 = 较快(默认); 1.0 = 慢慢飘过去
    "dry_run": False,        # 测试开关: True = 只打印不动鼠标(先验证坐标对不对); False = 真实点击
    "steps": [
        {"x": 1105, "y": 270, "button": "left"},   # 步骤1: A 选项(改成你的坐标)
        {"x": 1050, "y": 645, "button": "left"},   # 步骤2: 确认按钮
    ],
}

# ==================== 全局停止标志 ====================
_stop_flag = threading.Event()
VK_ESCAPE = 0x1B


def _esc_watcher():
    """后台线程: 轮询 Esc 键状态,按下则置位停止标志"""
    while not _stop_flag.is_set():
        # GetAsyncKeyState 返回的高位(bit 15)表示按下
        if ctypes.windll.user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000:
            _stop_flag.set()
            print("\n[停止信号] Esc 被按下,将在当前动作后停止...")
            break
        time.sleep(0.05)


def _validate_config(task):
    """校验配置,返回 (是否合法, 错误列表, 实际循环数)"""
    errors = []
    loops = int(task.get("loops", 0))
    interval = float(task.get("interval", 0))
    steps = task.get("steps", [])

    if loops <= 0:
        errors.append("loops 必须大于 0")
    if loops > MAX_LOOPS_ABSOLUTE:
        errors.append(f"loops={loops} 超过硬上限 {MAX_LOOPS_ABSOLUTE}")
    if interval < 0:
        errors.append("interval 不能为负")
    if not steps:
        errors.append("steps 不能为空")

    total = len(steps) * loops
    if total > MAX_TOTAL_CLICKS:
        errors.append(f"总点击数 {total} 超过硬上限 {MAX_TOTAL_CLICKS}")

    for i, s in enumerate(steps):
        if not isinstance(s.get("x"), (int, float)):
            errors.append(f"steps[{i}] 缺少 x 坐标")
        if not isinstance(s.get("y"), (int, float)):
            errors.append(f"steps[{i}] 缺少 y 坐标")
        btn = s.get("button", "left")
        if btn not in ("left", "right", "middle"):
            errors.append(f"steps[{i}] button='{btn}' 无效,应为 left/right/middle")

    return (len(errors) == 0, errors, loops)


def _print_task_summary(task, loops):
    total = len(task["steps"]) * loops
    est_seconds = total * task["interval"] + total * task.get("move_duration", 0.3)
    print("\n" + "=" * 56)
    print("  自动连点器 - 任务信息")
    print("=" * 56)
    print(f"  循环次数:      {loops} 轮")
    print(f"  动作间隔:      {task['interval']} 秒")
    print(f"  鼠标缓动:      {task.get('move_duration', 0.3)} 秒")
    print(f"  每轮步骤数:    {len(task['steps'])}")
    print(f"  总点击数:      {total} 次")
    print(f"  预计耗时:      ~{est_seconds:.1f} 秒")
    print(f"  模式:          {'DRY-RUN(只打印)' if task.get('dry_run') else '真实执行'}")
    print("-" * 56)
    print(f"  步骤列表:")
    for i, s in enumerate(task["steps"]):
        print(f"    {i+1}. 点击 ({int(s['x'])}, {int(s['y'])}) [{s.get('button','left')}]")
    print("-" * 56)
    print(f"  安全上限:      轮次 {MAX_LOOPS_ABSOLUTE} / 总时长 {MAX_RUNTIME_ABSOLUTE}s / 点击 {MAX_TOTAL_CLICKS}")
    print(f"  停止方式:      任意时刻按 Esc")
    print(f"  紧急停止:      把鼠标甩到屏幕左上角(触发 pyautogui FAILSAFE)")
    print("=" * 56 + "\n")


def _countdown(seconds):
    """倒计时,期间按 Esc 取消"""
    for i in range(seconds, 0, -1):
        print(f"  {i} 秒后开始... (按 Esc 取消)")
        time.sleep(1)
        if _stop_flag.is_set():
            return False
    return True


def _do_click(task, x, y, button):
    """执行点击(dry_run 时只打印)"""
    if task.get("dry_run"):
        print(f"    [DRY-RUN] 点击 ({x}, {y}) [{button}]")
        return
    pyautogui.moveTo(x, y, duration=task.get("move_duration", 0.3), _pause=False)
    pyautogui.click(button=button, _pause=False)


def run_task(task, loops):
    """执行任务,返回 (是否完成, 完成点击数, 原因)"""
    steps = task["steps"]
    interval = task["interval"]

    print("[开始] 倒计时...")
    if not _countdown(COUNTDOWN_SECONDS):
        return False, 0, "倒计时阶段按 Esc 取消"

    print(f"\n[开始] 任务启动,共 {loops} 轮\n")
    start_time = time.time()
    click_count = 0

    for loop_idx in range(loops):
        # 安全检查 1: 总时长
        elapsed = time.time() - start_time
        if elapsed > MAX_RUNTIME_ABSOLUTE:
            return False, click_count, f"超过总运行时间上限 {MAX_RUNTIME_ABSOLUTE}s"

        # 安全检查 2: 总点击数
        if click_count >= MAX_TOTAL_CLICKS:
            return False, click_count, f"超过总点击数上限 {MAX_TOTAL_CLICKS}"

        # 安全检查 3: Esc
        if _stop_flag.is_set():
            return False, click_count, "用户按 Esc 取消"

        print(f"[轮次 {loop_idx+1}/{loops}]  (已运行 {elapsed:.1f}s)")

        for step_idx, step in enumerate(steps):
            if _stop_flag.is_set():
                return False, click_count, "用户按 Esc 取消"

            x, y = int(step["x"]), int(step["y"])
            btn = step.get("button", "left")
            click_count += 1

            print(f"    动作 {step_idx+1}/{len(steps)}: 点击 ({x}, {y}) [{btn}]  累计 {click_count}")
            _do_click(task, x, y, btn)

            # 动作间隔(期间仍可能按 Esc,但要在 sleep 后检查)
            time.sleep(interval)

        # 每轮结束后检查
        if _stop_flag.is_set():
            return False, click_count, "用户按 Esc 取消"

    elapsed = time.time() - start_time
    return True, click_count, f"全部完成,耗时 {elapsed:.1f}s"


def main():
    print(f"\n[启动] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. 校验配置
    ok, errors, loops = _validate_config(TASK)
    if not ok:
        print("配置错误,请检查:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # 2. 打印任务摘要
    _print_task_summary(TASK, loops)

    # 3. 用户确认
    try:
        ans = input("是否开始? (y/N): ")
    except EOFError:
        ans = "n"
    if ans.strip().lower() not in ("y", "yes"):
        print("[取消] 用户取消")
        return

    # 4. 启动 Esc 监听线程
    watcher = threading.Thread(target=_esc_watcher, daemon=True)
    watcher.start()

    # 5. 执行任务
    try:
        completed, clicks, reason = run_task(TASK, loops)
    except pyautogui.FailSafeException:
        print("\n[紧急停止] pyautogui FAILSAFE 触发(鼠标移到了左上角)")
        completed, clicks, reason = False, 0, "FAILSAFE 触发"
    except Exception as e:
        print(f"\n[异常] {type(e).__name__}: {e}")
        completed, clicks, reason = False, 0, f"异常: {e}"
    finally:
        _stop_flag.set()

    # 6. 结束提示
    print("\n" + "=" * 56)
    status = "成功完成" if completed else "提前停止"
    print(f"  状态:  {status}")
    print(f"  原因:  {reason}")
    print(f"  点击:  {clicks} 次")
    print(f"  结束:  {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 56)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[中断] Ctrl+C 退出")
        sys.exit(130)
