# this is leftover code from when I used this script on macos
# it will likely need some work to revive it

from pynput.keyboard import Key, Controller
from collections import namedtuple
import time


def init_code(self):
    self.KeyEvent = namedtuple("KeyEvent", ["Key"])
    self.keyboard = Controller()
    self.flag = True


def mac_down(self, *args, **kwargs):
    print(
        f'down key: {str(args[0]).split(".")[-1] if "." in str(args[0]) else str(args[0])[1:-1]}'
    )
    if time.time() - self.last_press < 0.001:
        print("\tignored")
        return True
    # print(f"down arg: {str(args[0])}")
    key = str(args[0]).split(".")[-1] if "." in str(args[0]) else str(args[0])[1:-1]
    self.flag = self.key_down(self.KeyEvent(key.upper()))
    print(f"curr_mods: {self.curr_mods}")


def mac_up(self, *args, **kwargs):
    # print(f"up arg: {str(args[0])}")
    print(
        f'up key: {str(args[0]).split(".")[-1] if "." in str(args[0]) else str(args[0])[1:-1]}'
    )
    key = str(args[0]).split(".")[-1] if "." in str(args[0]) else str(args[0])[1:-1]
    self.key_up(self.KeyEvent(key.upper()))


def example_code(
    self,
):
    mp = {
        "shift": Key.shift,
        "backspace": Key.backspace,
        "delete": Key.delete,
    }

    # to press a key:
    if k in mp.keys():
        k = mp[k]
    self.keyboard.press(k)

    # to release a key:
    if k in mp.keys():
        k = mp[k]
    self.keyboard.release(k)


    # this might be required?
    
    # if platform.system() != "Windows":
    #     for mod in curr_mods:
    #         pyautogui.keyDown(mod)