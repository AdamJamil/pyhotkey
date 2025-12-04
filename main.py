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
        speaker.say("gaming time")
        speaker.runAndWait()
        hm = PyHook3.HookManager()
        hm.KeyDown = handler.key_down
        hm.KeyUp = handler.key_up
        hm.HookKeyboard()
        pythoncom.PumpMessages()
        atexit.register(at_exit, handler)
        signal_exit.handler = handler
        signal.signal(signal.SIGTERM, signal_exit)
        signal.signal(signal.SIGINT, signal_exit)
        pythoncom.PumpMessages()
    else:
        args = {"on_press": handler.mac_down, "on_release": handler.mac_up, "darwin_intercept": handler.darwin_intercept}
        with keyboard.Listener(**args) as listener:
            listener.join()


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
