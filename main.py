import PyHook3
import pythoncom
from key_handler import KeyHandler
import atexit
import win32api
import win32con
import signal
import pathlib


def main():
    hm = PyHook3.HookManager()
    handler = KeyHandler()
    hm.KeyDown = handler.key_down
    hm.KeyUp = handler.key_up
    hm.HookKeyboard()
    atexit.register(at_exit, handler)
    signal_exit.handler = handler
    signal.signal(signal.SIGTERM, signal_exit)
    signal.signal(signal.SIGINT, signal_exit)
    pythoncom.PumpMessages()


def at_exit(handler):
    handler.exit()
    main_thread_id = win32api.GetCurrentThreadId()
    win32api.PostThreadMessage(main_thread_id, win32con.WM_QUIT, 0, 0)


def signal_exit(sig, frame):
    signal_exit.handler.exit()
    main_thread_id = win32api.GetCurrentThreadId()
    win32api.PostThreadMessage(main_thread_id, win32con.WM_QUIT, 0, 0)


if __name__ == "__main__":
    main()
