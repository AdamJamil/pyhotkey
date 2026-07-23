import os
import sys
import pathlib
import logging
import threading
from datetime import datetime, timedelta

# Per-session log file. pythonw.exe discards stderr, so we route everything
# through logging and a sys.excepthook to capture import-time and runtime crashes.
try:
    _logs_dir = pathlib.Path(__file__).parent / "logs"
    _logs_dir.mkdir(exist_ok=True)
    _log_path = _logs_dir / f"pyhotkey-{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.log"
    logging.basicConfig(
        filename=str(_log_path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    sys.excepthook = lambda et, ev, tb: logging.error(
        "uncaught exception", exc_info=(et, ev, tb)
    )
    if hasattr(threading, "excepthook"):
        threading.excepthook = lambda args: logging.error(
            "uncaught thread exception in %s", args.thread,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
    # Drop session logs older than 30 days so the directory doesn't grow forever.
    _cutoff = datetime.now() - timedelta(days=30)
    for _f in _logs_dir.glob("pyhotkey-*.log"):
        try:
            if datetime.fromtimestamp(_f.stat().st_mtime) < _cutoff:
                _f.unlink()
        except OSError:
            pass
    logging.info("startup pid=%d", os.getpid())
except Exception:
    pass

from key_handler import KeyHandler
import atexit

import platform

if platform.system() == "Windows":
    import pyWinhook as PyHook3
    import pythoncom
    import pythoncom
    import win32api
    import win32con
    import signal
    import pyttsx3
else:
    import pynput
    from pynput import keyboard


def main():
    handler = KeyHandler()
    if platform.system() == "Windows":
        speaker = pyttsx3.init()
        # speaker.say("gaming time")
        speaker.runAndWait()
        hm = PyHook3.HookManager()
        hm.KeyDown = handler.key_down
        hm.KeyUp = handler.key_up
        hm.HookKeyboard()
        logging.info("entering message pump #1")
        pythoncom.PumpMessages()
        logging.warning("message pump #1 returned")
        atexit.register(at_exit, handler)
        signal_exit.handler = handler
        signal.signal(signal.SIGTERM, signal_exit)
        signal.signal(signal.SIGINT, signal_exit)
        logging.info("entering message pump #2")
        pythoncom.PumpMessages()
        logging.warning("message pump #2 returned")
    else:
        args = {"on_press": handler.mac_down, "on_release": handler.mac_up, "darwin_intercept": handler.darwin_intercept}
        with keyboard.Listener(**args) as listener:
            listener.join()


def at_exit(handler):
    logging.info("at_exit fired")
    handler.exit()
    main_thread_id = win32api.GetCurrentThreadId()
    win32api.PostThreadMessage(main_thread_id, win32con.WM_QUIT, 0, 0)


def signal_exit(sig, frame):
    logging.warning("signal_exit fired with signal=%s", sig)
    signal_exit.handler.exit()
    main_thread_id = win32api.GetCurrentThreadId()
    win32api.PostThreadMessage(main_thread_id, win32con.WM_QUIT, 0, 0)


if __name__ == "__main__":
    main()
