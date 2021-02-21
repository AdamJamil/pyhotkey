import PyHook3
import pythoncom
from KeyHandler import KeyHandler


def main():
    hm = PyHook3.HookManager()
    handler = KeyHandler()
    hm.KeyDown = handler.key_down
    hm.KeyUp = handler.key_up
    hm.HookKeyboard()
    pythoncom.PumpMessages()


if __name__ == "__main__":
    main()
