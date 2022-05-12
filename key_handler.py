from collections import defaultdict as ddict, namedtuple
from functools import partial
from alarm_clock import AlarmClock
import time
import threading
import math
from itertools import chain, combinations
import cli
from run_cmd import RunCMDThread
import os
import signal
import sys
import pathlib
import subprocess
import pyautogui
import screeninfo
from codeforces import put_code

import platform

if platform.system() == "Windows":
    import pywinauto.keyboard
    from win32gui import GetWindowText, GetForegroundWindow
else:
    from pynput.keyboard import Key, Controller

class KeyHandler:
    def __init__(self):
        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = False

        if platform.system() != "Windows":
            self.KeyEvent = namedtuple("KeyEvent", ["Key"])
            self.keyboard = Controller()
            self.flag = True

        self.last_press = time.time()
        self.last_esc = time.time()
        self.rep = 1
        self.mods = ["F15", "F13", "F14"]
        self.curr_mods = set()
        self.m_thread = None
        self.s_thread = None
        self.m_cmps = set()
        self.s_cmps = set()

        self.alarm_clock = AlarmClock() if platform.system() == "Windows" else None
        self.done = False

        sbo = "Oem_4" if platform.system() == "Windows" else "["
        sbc = "Oem_6" if platform.system() == "Windows" else "]"
        # cbo = "Oem_4" if platform.system() == "Windows" else "["
        # cbc = "Oem_4" if platform.system() == "Windows" else "["

        default = [lambda: True, []]
        press = self.press
        self.binds_down = ddict(lambda: ddict(lambda: default), {
            frozenset(): ddict(lambda: default, {
                sbo: [press, ["backspace"]],
                sbc: [press, ["delete"]],
            }),
            frozenset([self.mods[0]]): ddict(lambda: default, {
                "I": [press, ["up"]],
                "J": [press, ["left"]],
                "K": [press, ["down"]],
                "L": [press, ["right"]],
                "U": [press, ["ctrl", "left"]],
                "O": [press, ["ctrl", "right"]],
                "Y": [press, ["end"]],
                "H": [press, ["home"]],
                "Oem_3": [press, ["capslock"]],
                "C": [cli.CLIServer, [self.alarm_clock]]
            }),
            frozenset([self.mods[1]]): ddict(lambda: default, {
                "A": [press, ["["]],
                "S": [press, ["shift", "{"]],
                "D": [press, ["shift", "("]],
                "F": [press, ["\\"]],
                "G": [press, ["+"]],
                "T": [press, ["_"]],
                "Y": [press, ["="]],
                "H": [press, ["-"]],
                "J": [press, ["/"]],
                "K": [press, ["shift", ")"]],
                "L": [press, ["shift", "}"]],
                "Oem_1": [press, ["]"]],
                "Q": [press, ["volumemute"]],
                "W": [press, ["volumedown"]],
                "E": [press, ["volumeup"]],
                "C": [put_code, []],
            }),
            frozenset([self.mods[0], self.mods[1]]): ddict(lambda: default, {
                "I": [press, ["shift", "up"]],
                "J": [press, ["shift", "left"]],
                "K": [press, ["shift", "down"]],
                "L": [press, ["shift", "right"]],
                "U": [press, ["ctrl", "shift", "left"]],
                "O": [press, ["ctrl", "shift", "right"]],
                "Y": [press, ["shift", "end"]],
                "H": [press, ["shift", "home"]],
            }),
            frozenset([self.mods[2]]): ddict(lambda: default, {
                "R": [self.mouse_down, ["left"]],
                "3": [self.mouse_down, ["middle"]],
                "W": [self.mouse_down, ["right"]],
                "T": [pyautogui.scroll, [-3]],
                "G": [pyautogui.scroll, [3]],
                "H": [self.mouse_toggle_screen, []],
            }),
            frozenset([self.mods[1], self.mods[2]]): ddict(lambda: default, {
                "R": [self.mouse_down, ["left"]],
                "3": [self.mouse_down, ["middle"]],
                "W": [self.mouse_down, ["right"]],
                "H": [self.mouse_toggle_screen, []],
            }),
            frozenset([self.mods[0], self.mods[1], self.mods[2]]): ddict(lambda: default, {
                "Q": [self.exit, []],
                "R": [self.restart, []],
            })
        })

        self.binds_up = ddict(lambda: ddict(lambda: default), {
            frozenset(): ddict(lambda: default, {}),
            frozenset([self.mods[2]]): ddict(lambda: default, {
                "R": [self.mouse_up, ["left"]],
                "3": [self.mouse_up, ["middle"]],
                "W": [self.mouse_up, ["right"]],
            }),
            frozenset([self.mods[1]]): ddict(lambda: default, {}),
            frozenset([self.mods[2], self.mods[1]]): ddict(lambda: default, {
                "R": [self.mouse_up, ["left"]],
                "3": [self.mouse_up, ["middle"]],
                "W": [self.mouse_up, ["right"]],
            })
        })

        # add default keys
        for key in chain.from_iterable(combinations(self.mods, r) for r in range(len(self.mods) + 1)):
            if frozenset(key) not in self.binds_down:
                self.binds_down[frozenset(key)] = ddict(lambda: default)
            if frozenset(key) not in self.binds_up:
                self.binds_up[frozenset(key)] = ddict(lambda: default)

        # mouse movement
        move_map = {
            "E": (0, -1),
            "S": (-1, 0),
            "D": (0, 1),
            "F": (1, 0),
        }
        scroll_map = {
            "T": -1,
            "G": 1,
        }
        for key in filter(lambda x: self.mods[2] in x, self.binds_down.keys()):
            for char in move_map.keys():
                self.binds_down[key][char] = [self.key_add, [move_map[char], self.m_cmps, "m_thread", self.mouse_move]]
                self.binds_up[key][char] = [self.key_remove, [move_map[char], self.m_cmps, "m_thread"]]
            for char in scroll_map.keys():
                self.binds_down[key][char] = [self.key_add, [scroll_map[char], self.s_cmps, "s_thread", self.scroll_move]]
                self.binds_up[key][char] = [self.key_remove, [scroll_map[char], self.s_cmps, "s_thread"]]

        jump_keys = [["U", "I", "O", "P"], ["J", "K", "L", "Oem_1"], ["M", "Oem_Comma", "Oem_Period", "Oem_2"]]
        jump_map = {key: [y, x] for x, row in enumerate(jump_keys) for y, key in enumerate(row)}
        for key in filter(lambda x: self.mods[2] in x, self.binds_down.keys()):
            for char in jump_map.keys():
                self.binds_down[key][char] = [self.mouse_jump, jump_map[char]]

        # allow for repetition
        for i in range(1, 10):
            self.binds_down[frozenset([self.mods[0]])][str(i)] = [partial(self.__setattr__, "rep"), [i]]
            self.binds_down[frozenset([self.mods[0], self.mods[1]])][str(i)] = [partial(self.__setattr__, "rep"), [i]]

        # insert and remove modifiers
        for key in self.binds_down.keys():
            for modifier in self.mods:
                self.binds_down[key][modifier] = [self.curr_mods.add, [modifier]]
                self.binds_up[key][modifier] = [self.curr_mods.remove, [modifier]]

        # soft and mouse reset
        for key in self.binds_up.keys():
            self.binds_up[key][self.mods[0]] = [self.reset, []]
            self.binds_up[key][self.mods[2]] = [self.mouse_reset, []]

        # hard reset check (double press esc)
        for key in self.binds_down.keys():
            self.binds_down[key]["Escape"] = [self.esc_check, []]

    def key_down(self, event):
        if time.time() - self.last_press < 0.001:
            return True
        value = self.binds_down[frozenset(self.curr_mods)][event.Key]
        return type(value[0](*value[1])) == bool

    def key_up(self, event):
        value = self.binds_up[frozenset(self.curr_mods)][event.Key]
        print(event, self.curr_mods)
        return type(value[0](*value[1])) == bool

    def darwin_intercept(self, _, event):
        temp = self.flag
        self.flag = True
        return event if temp else None

    def mac_down(self, *args, **kwargs):
        print(f'down key: {str(args[0]).split(".")[-1] if "." in str(args[0]) else str(args[0])[1:-1]}')
        if time.time() - self.last_press < 0.001:
            print("\tignored")
            return True
        # print(f"down arg: {str(args[0])}")
        key = str(args[0]).split(".")[-1] if "." in str(args[0]) else str(args[0])[1:-1]
        self.flag = self.key_down(self.KeyEvent(key.upper()))
        print(f"curr_mods: {self.curr_mods}")

    def mac_up(self, *args, **kwargs):
        # print(f"up arg: {str(args[0])}")
        print(f'up key: {str(args[0]).split(".")[-1] if "." in str(args[0]) else str(args[0])[1:-1]}')
        key = str(args[0]).split(".")[-1] if "." in str(args[0]) else str(args[0])[1:-1]
        self.key_up(self.KeyEvent(key.upper()))

    pywinmap = {
        "{": "+[",
        "}": "+]",
        "(": "{(}",
        ")": "{)}",
        "+": "{+}",
        "_": "{_}",
    }

    def press(self, *keys):
        # time.sleep(0.2)
        print(f"pressing {keys}")
        if platform.system() == "Windows":
            if "xonsh" in GetWindowText(GetForegroundWindow()) and keys[0] in self.pywinmap.keys():
                self.last_press = time.time()
                pywinauto.keyboard.send_keys(self.pywinmap[keys[0]], pause=0)
                self.last_press = time.time()
                return
        # else:
        #     curr_mods = self.curr_mods
        #     for mod in curr_mods:
        #         pyautogui.keyUp(mod)

        if platform.system() != "Windows":
            mp = {
                "shift": Key.shift,
                "backspace": Key.backspace,
                "delete": Key.delete,
            }
        for _ in range(self.rep):
            self.last_press = time.time()
            for k in keys:
                if platform.system() == "Windows":
                    pyautogui.keyDown(k)
                else:
                    if k in mp.keys():
                        k = mp[k]
                    self.keyboard.press(k)
            for k in reversed(keys):
                if platform.system() == "Windows":
                    pyautogui.keyUp(k)
                else:
                    if k in mp.keys():
                        k = mp[k]
                    self.keyboard.release(k)
        # if platform.system() != "Windows":
        #     for mod in curr_mods:
        #         pyautogui.keyDown(mod)
        print(f"done pressing {keys}")

        self.rep = 1

    def reset(self):
        print("reset")
        self.rep = 1
        self.curr_mods.remove(self.mods[0])
        return True

    def mouse_reset(self):
        self.m_cmps.clear()
        self.s_cmps.clear()
        if self.m_thread:
            self.m_thread.join()
        if self.s_thread:
            self.s_thread.join()
        self.m_thread, self.s_thread = None, None
        self.curr_mods.remove(self.mods[2])
        return True

    def hard_reset(self):
        self.last_press = time.time()
        self.last_esc = time.time()
        self.rep = 1
        self.curr_mods.clear()
        self.mouse_reset()
        return True

    def esc_check(self):
        if time.time() - self.last_esc < 0.5:
            self.hard_reset()
        self.last_esc = time.time()
        return True

    def mouse_down(self, button):
        pyautogui.mouseDown(button=button)

    def mouse_up(self, button):
        pyautogui.mouseUp(button=button)

    def mouse_move(self):
        while True:
            time.sleep(0.01)
            lock = threading.Lock()
            lock.acquire()

            if not self.m_cmps:
                lock.release()
                break

            vx, vy = [sum(x) for x in zip(*self.m_cmps)]
            lock.release()
            mag = math.sqrt(vx * vx + vy * vy) / 6 / (1 + 4 * (self.mods[1] not in self.curr_mods))

            if mag > 0:
                pyautogui.move(vx / mag, vy / mag)

    def scroll_move(self):
        if self.mods[1] in self.curr_mods:
            time.sleep(0.01)
            lock = threading.Lock()
            lock.acquire()
            vy = sum(self.s_cmps)
            lock.release()
            mag = -vy * 200
            pyautogui.scroll(mag)

        while True:
            time.sleep(0.01)
            lock = threading.Lock()
            lock.acquire()

            if not self.s_cmps:
                lock.release()
                break

            vy = sum(self.s_cmps)
            lock.release()
            mag = -vy * (30 if self.mods[1] not in self.curr_mods else 10)
            pyautogui.scroll(mag)

    def key_add(self, key, container, thread_name, thread_fxn):
        lock = threading.Lock()
        lock.acquire()
        if not container:
            setattr(self, thread_name, threading.Thread(target=thread_fxn))
            getattr(self, thread_name).start()
        container.add(key)
        lock.release()

    def key_remove(self, key, container, thread_name):
        lock = threading.Lock()
        lock.acquire()
        container.remove(key)
        if not container:
            getattr(self, thread_name).join()
        lock.release()

    def curr_monitor(self):
        pos = pyautogui.position()
        for m in screeninfo.get_monitors():
            if m.x <= pos[0] < m.x + m.width and m.y <= pos[1] < m.y + m.height:
                return m

    def mouse_jump(self, x, y):
        m = self.curr_monitor()
        pyautogui.moveTo(m.x + (x + 1) * m.width / 5, m.y + (y + 1) * m.height / 4)

    def mouse_toggle_screen(self):
        m = self.curr_monitor()
        pos = pyautogui.position()
        rel_x, rel_y = (pos[0] - m.x) / m.width, (pos[1] - m.y) / m.height
        monitors = screeninfo.get_monitors()
        next_m = monitors[(monitors.index(m) + 1) % len(monitors)]
        pyautogui.moveTo(next_m.x + rel_x * next_m.width, next_m.y + rel_y * next_m.height)

    def exit(self):
        if self.done:
            return
        self.done = True
        self.alarm_clock.save()
        pid = os.getpid()
        thread = threading.Thread(target=lambda: (time.sleep(0.1), os.kill(pid, signal.SIGTERM)))
        thread.start()

    def restart(self):
        RunCMDThread("CScript \"C:\\Users\\adama\\AppData\\Roaming\\Microsoft\\Windows\\Start "
                     "Menu\\Programs\\Startup\\launch_script.vbs\"", daemon=False)
        self.exit()
