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


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def _run_quiet(args):
    # no capture_output -> much faster + less overhead
    return subprocess.run(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_NO_WINDOW,
    )


def _parse_list(stdout: str):
    blocks = re.split(r"\r?\n\r?\n+", stdout.strip())
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


# --- global state ---
_MONITOR_IDS = []  # idx -> MonitorID
_Q = queue.Queue()  # (idx, delta)


def init_twinkle_brightness():
    if not os.path.exists(_TWINKLE):
        raise FileNotFoundError(_TWINKLE)

    p = subprocess.run(
        [_TWINKLE, "--List"], text=True, capture_output=True, creationflags=_NO_WINDOW
    )
    if p.returncode != 0:
        raise RuntimeError(
            p.stderr.strip() or p.stdout.strip() or "Twinkle Tray --List failed"
        )

    mons = _parse_list(p.stdout)
    ids = [m.get("MonitorID") for m in mons]
    if any(x is None for x in ids):
        raise RuntimeError(f"Failed to parse MonitorID(s): {mons}")

    global _MONITOR_IDS
    _MONITOR_IDS = ids

    # start worker once
    threading.Thread(target=_worker, daemon=True).start()


def _worker():
    # batch deltas so holding a key doesn't spawn 60 processes/sec
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
        # flush every 80ms if anything pending
        if now - last_flush >= 0.08 and any(pending):
            for i, d in enumerate(pending):
                if d:
                    mon_id = _MONITOR_IDS[i]
                    _run_quiet([_TWINKLE, f"--MonitorID={mon_id}", f"--Offset={d}"])
                    pending[i] = 0
            last_flush = now


def change_brightness(idx: int, delta: int) -> None:
    _Q.put((idx, delta))


init_twinkle_brightness()
