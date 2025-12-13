import pyautogui
from state import State
import subprocess
import threading
import queue
import time
import re
import os


_TWINKLE = r"C:\Users\adama\AppData\Local\Programs\twinkle-tray\Twinkle Tray.exe"
_NO_WINDOW = 0x08000000
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def curr_monitor():
    pos = pyautogui.position()
    for m in State.monitors:
        if m.x <= pos[0] < m.x + m.width and m.y <= pos[1] < m.y + m.height:
            return m

_TWINKLE = r"C:\Users\adama\AppData\Local\Programs\twinkle-tray\Twinkle Tray.exe"
_NO_WINDOW = 0x08000000
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)

def _twinkle_running() -> bool:
    # avoids extra deps like psutil
    p = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq Twinkle Tray.exe"],
        text=True,
        capture_output=True,
        creationflags=_NO_WINDOW,
    )
    return "Twinkle Tray.exe" in (p.stdout or "")

def _parse_list(stdout: str):
    blocks = re.split(r"\r?\n\r?\n+", (stdout or "").strip())
    mons = []
    for b in blocks:
        m = {}
        for line in b.splitlines():
            line = _strip_ansi(line).strip()
            if ":" in line:
                k, v = line.split(":", 1)
                m[k.strip()] = v.strip()
        if m:
            mons.append(m)
    return mons

def _run_capture(args):
    return subprocess.run(args, text=True, capture_output=True, creationflags=_NO_WINDOW)

def _run_quiet(args):
    return subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=_NO_WINDOW)

_MONITOR_IDS = []
_Q = queue.Queue()
_started = False

def init_twinkle_brightness():
    global _MONITOR_IDS, _started
    if _started:
        return
    _started = True

    def init_loop():
        global _MONITOR_IDS
        while True:
            if not _twinkle_running():
                time.sleep(1.0)
                continue

            p = _run_capture([_TWINKLE, "--List"])
            if p.returncode == 0:
                mons = _parse_list(p.stdout)
                ids = [m.get("MonitorID") for m in mons]
                if ids and all(ids):
                    _MONITOR_IDS = ids
                    threading.Thread(target=_worker, daemon=True).start()
                    return
            time.sleep(1.0)

    threading.Thread(target=init_loop, daemon=True).start()

def _worker():
    pending = [0] * max(1, len(_MONITOR_IDS))
    last_flush = time.time()

    while True:
        try:
            idx, delta = _Q.get(timeout=0.05)
            if 0 <= idx < len(pending):
                pending[idx] += int(delta)
        except queue.Empty:
            pass

        now = time.time()
        if now - last_flush >= 0.08 and any(pending):
            # if Twinkle dies, don’t spam-relaunch
            if not _twinkle_running():
                pending[:] = [0] * len(pending)
                time.sleep(0.5)
                continue

            for i, d in enumerate(pending):
                if d:
                    mon_id = _MONITOR_IDS[i]
                    _run_quiet([_TWINKLE, f"--MonitorID={mon_id}", f"--Offset={d}"])
                    pending[i] = 0
            last_flush = now

def change_brightness(idx: int, delta: int) -> None:
    _Q.put((idx, delta))

# call once (safe)
init_twinkle_brightness()