import pyautogui
from state import State
import subprocess
import threading
import queue
import time
import re
import os
import ctypes
from ctypes import wintypes
import logging


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


# ======================== Primary display resolution toggle ========================

_ENUM_CURRENT_SETTINGS = -1
_CDS_UPDATEREGISTRY = 0x01
_DISP_CHANGE_SUCCESSFUL = 0
_DM_PELSWIDTH = 0x00080000
_DM_PELSHEIGHT = 0x00100000


class _DEVMODE(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", ctypes.c_wchar * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmPositionX", wintypes.LONG),
        ("dmPositionY", wintypes.LONG),
        ("dmDisplayOrientation", wintypes.DWORD),
        ("dmDisplayFixedOutput", wintypes.DWORD),
        ("dmColor", wintypes.SHORT),
        ("dmDuplex", wintypes.SHORT),
        ("dmYResolution", wintypes.SHORT),
        ("dmTTOption", wintypes.SHORT),
        ("dmCollate", wintypes.SHORT),
        ("dmFormName", ctypes.c_wchar * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD),
        ("dmICMMethod", wintypes.DWORD),
        ("dmICMIntent", wintypes.DWORD),
        ("dmMediaType", wintypes.DWORD),
        ("dmDitherType", wintypes.DWORD),
        ("dmReserved1", wintypes.DWORD),
        ("dmReserved2", wintypes.DWORD),
        ("dmPanningWidth", wintypes.DWORD),
        ("dmPanningHeight", wintypes.DWORD),
    ]


_RES_4K = (3840, 2160)
_RES_QHD = (2560, 1440)


def _read_primary_devmode() -> _DEVMODE:
    dm = _DEVMODE()
    dm.dmSize = ctypes.sizeof(_DEVMODE)
    # NULL device name == primary display
    if not ctypes.windll.user32.EnumDisplaySettingsW(None, _ENUM_CURRENT_SETTINGS, ctypes.byref(dm)):
        raise OSError("EnumDisplaySettingsW failed for primary display")
    return dm


def _apply_resolution(width: int, height: int) -> int:
    dm = _read_primary_devmode()
    dm.dmPelsWidth = width
    dm.dmPelsHeight = height
    dm.dmFields = _DM_PELSWIDTH | _DM_PELSHEIGHT
    return ctypes.windll.user32.ChangeDisplaySettingsW(ctypes.byref(dm), _CDS_UPDATEREGISTRY)


def _toggle_worker():
    try:
        dm = _read_primary_devmode()
        current = (int(dm.dmPelsWidth), int(dm.dmPelsHeight))
        target = _RES_QHD if current == _RES_4K else _RES_4K
        rc = _apply_resolution(*target)
        if rc != _DISP_CHANGE_SUCCESSFUL:
            logging.error("ChangeDisplaySettingsW failed: rc=%s target=%s", rc, target)
        else:
            logging.info("primary resolution %s -> %s", current, target)
            # Refresh cached monitor rects so curr_monitor() keeps mapping the
            # cursor correctly after the resolution change.
            State.update_monitors()
    except Exception:
        logging.exception("toggle_primary_resolution failed")


def toggle_primary_resolution() -> None:
    # Off-thread: ChangeDisplaySettings can take >100ms and the hook callback
    # must return quickly or Windows' LowLevelHooksTimeout drops the next key.
    threading.Thread(target=_toggle_worker, daemon=True).start()