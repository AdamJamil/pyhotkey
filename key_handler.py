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
from constants import DEBUG_MODE, CAPS, RLT, RRT, LLT, MODIFIERS, OPEN_BRACKET, CLOSE_BRACKET


import pywinauto.keyboard
from win32gui import GetWindowText, GetForegroundWindow


class KeyHandler:
    def __init__(self):
        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = False

        self.last_press = time.time()
        self.last_esc = time.time()
        self.rep = 1
        self.curr_mods = set()
        self.m_thread = None
        self.s_thread = None
        self.m_cmps = set()
        self.s_cmps = set()
        self.mouse_is_down = False
        self.lock = threading.Lock()
        self.monitors = screeninfo.get_monitors()

        self.alarm_clock = AlarmClock()
        self.done = False

        default = [lambda: True, []]
        press = self.press
        self.binds_down = ddict(
            lambda: ddict(lambda: default),
            {
                frozenset(): ddict(
                    lambda: default,
                    {
                        OPEN_BRACKET: [press, ["backspace"]],
                        CLOSE_BRACKET: [press, ["delete"]],
                    },
                ),
                frozenset([CAPS]): ddict(
                    lambda: default,
                    {
                        "I": [press, ["up"]],
                        "J": [press, ["left"]],
                        "K": [press, ["down"]],
                        "L": [press, ["right"]],
                        "U": [press, ["ctrl", "left"]],
                        "O": [press, ["ctrl", "right"]],
                        "Y": [press, ["end"]],
                        "H": [press, ["home"]],
                        "Oem_3": [press, ["capslock"]],
                        "C": [cli.CLIServer, [self.alarm_clock]],
                    },
                ),
                frozenset([RLT]): ddict(
                    lambda: default,
                    {
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
                    },
                ),
                frozenset([CAPS, RLT]): ddict(
                    lambda: default,
                    {
                        "I": [press, ["shift", "up"]],
                        "J": [press, ["shift", "left"]],
                        "K": [press, ["shift", "down"]],
                        "L": [press, ["shift", "right"]],
                        "U": [press, ["ctrl", "shift", "left"]],
                        "O": [press, ["ctrl", "shift", "right"]],
                        "Y": [press, ["shift", "end"]],
                        "H": [press, ["shift", "home"]],
                    },
                ),
                frozenset([RRT]): ddict(
                    lambda: default,
                    {
                        "R": [self.mouse_down, ["left"]],
                        "3": [self.mouse_down, ["middle"]],
                        "W": [self.mouse_down, ["right"]],
                        "T": [pyautogui.scroll, [-3]],
                        "G": [pyautogui.scroll, [3]],
                        "H": [self.mouse_toggle_screen, []],
                    },
                ),
                frozenset([LLT]): ddict(
                    lambda: default,
                    {
                        "E": [self.mouse_down, ["left"]],
                        "2": [self.mouse_down, ["middle"]],
                        "Q": [self.mouse_down, ["right"]],
                        "W": [pyautogui.scroll, [-6]],
                        "S": [pyautogui.scroll, [6]],
                    },
                ),
                frozenset([RLT, RRT]): ddict(
                    lambda: default,
                    {
                        "R": [self.mouse_down, ["left"]],
                        "3": [self.mouse_down, ["middle"]],
                        "W": [self.mouse_down, ["right"]],
                        "H": [self.mouse_toggle_screen, []],
                    },
                ),
                frozenset([CAPS, RLT, RRT]): ddict(
                    lambda: default,
                    {
                        "Q": [self.exit, []],
                        "R": [self.restart, []],
                    },
                ),
            },
        )

        self.binds_up = ddict(
            lambda: ddict(lambda: default),
            {
                frozenset(): ddict(lambda: default, {}),
                frozenset([RRT]): ddict(
                    lambda: default,
                    {
                        "R": [self.mouse_up, ["left"]],
                        "3": [self.mouse_up, ["middle"]],
                        "W": [self.mouse_up, ["right"]],
                    },
                ),
                frozenset([LLT]): ddict(
                    lambda: default,
                    {
                        "E": [self.mouse_up, ["left"]],
                        "2": [self.mouse_up, ["middle"]],
                        "Q": [self.mouse_up, ["right"]],
                    },
                ),
                frozenset([RLT]): ddict(lambda: default, {}),
                frozenset([RRT, RLT]): ddict(
                    lambda: default,
                    {
                        "R": [self.mouse_up, ["left"]],
                        "3": [self.mouse_up, ["middle"]],
                        "W": [self.mouse_up, ["right"]],
                    },
                ),
            },
        )

        # add default keys
        for key in chain.from_iterable(
            combinations(MODIFIERS, r) for r in range(len(MODIFIERS) + 1)
        ):
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
        for key in filter(lambda x: RRT in x, self.binds_down.keys()):
            for char in move_map.keys():
                self.binds_down[key][char] = [
                    self.key_add,
                    [move_map[char], self.m_cmps, "m_thread", self.mouse_move],
                ]
                self.binds_up[key][char] = [
                    self.key_remove,
                    [move_map[char], self.m_cmps, "m_thread"],
                ]
            for char in scroll_map.keys():
                self.binds_down[key][char] = [
                    self.key_add,
                    [scroll_map[char], self.s_cmps, "s_thread", self.scroll_move],
                ]
                self.binds_up[key][char] = [
                    self.key_remove,
                    [scroll_map[char], self.s_cmps, "s_thread"],
                ]
        scroll_map = {
            "W": -1,
            "S": 1,
        }
        for key in filter(lambda x: LLT in x, self.binds_down.keys()):
            for char in move_map.keys():
                self.binds_down[key][char] = [
                    self.key_add,
                    [move_map[char], self.m_cmps, "m_thread", self.mouse_move],
                ]
                self.binds_up[key][char] = [
                    self.key_remove,
                    [move_map[char], self.m_cmps, "m_thread"],
                ]
            for char in scroll_map.keys():
                self.binds_down[key][char] = [
                    self.key_add,
                    [scroll_map[char], self.s_cmps, "s_thread", self.scroll_move],
                ]
                self.binds_up[key][char] = [
                    self.key_remove,
                    [scroll_map[char], self.s_cmps, "s_thread"],
                ]

        jump_keys = [
            ["U", "I", "O", "P"],
            ["J", "K", "L", "Oem_1"],
            ["M", "Oem_Comma", "Oem_Period", "Oem_2"],
        ]
        jump_map = {
            key: [y, x] for x, row in enumerate(jump_keys) for y, key in enumerate(row)
        }
        for key in filter(lambda x: RRT in x, self.binds_down.keys()):
            for char in jump_map.keys():
                self.binds_down[key][char] = [self.mouse_jump, jump_map[char]]

        # allow for repetition
        for i in range(1, 10):
            self.binds_down[frozenset({CAPS})][str(i)] = [
                partial(self.__setattr__, "rep"),
                [i],
            ]
            self.binds_down[frozenset({CAPS, RLT})][str(i)] = [
                partial(self.__setattr__, "rep"),
                [i],
            ]

        def mod_add(mod):
            with self.lock:
                self.curr_mods.add(mod)

        def mod_remove(mod):
            with self.lock:
                self.curr_mods.discard(mod)

        # insert and remove modifiers
        for key in self.binds_down.keys():
            for modifier in MODIFIERS:
                self.binds_down[key][modifier] = [mod_add, [modifier]]
                self.binds_up[key][modifier] = [mod_remove, [modifier]]

        # soft and mouse reset
        for key in self.binds_up.keys():
            self.binds_up[key][CAPS] = [self.reset, []]
            self.binds_up[key][RRT] = [self.mouse_reset, []]
            self.binds_up[key][LLT] = [self.mouse_reset, []]

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
        if DEBUG_MODE:
            print(event, self.curr_mods)
        return type(value[0](*value[1])) == bool

    pywinmap = {
        "{": "+[",
        "}": "+]",
        "(": "{(}",
        ")": "{)}",
        "+": "{+}",
        "_": "{_}",
    }

    def press(self, *keys):
        if DEBUG_MODE:
            print(f"pressing {keys}")

        for _ in range(self.rep):
            self.last_press = time.time()
            for k in keys:
                pyautogui.keyDown(k)
            for k in reversed(keys):
                pyautogui.keyUp(k)

        if DEBUG_MODE:
            print(f"done pressing {keys}")

        self.rep = 1

    def reset(self):
        if DEBUG_MODE:
            print("reset")
        self.rep = 1
        self.curr_mods.remove(CAPS)
        self.mouse_is_down = False
        self.monitors = screeninfo.get_monitors()
        return True

    def mouse_reset(self):
        self.mouse_is_down = False
        self.m_cmps.clear()
        self.s_cmps.clear()
        if self.m_thread:
            self.m_thread.join()
        if self.s_thread:
            self.s_thread.join()
        self.m_thread, self.s_thread = None, None
        for mod in (LLT, RRT):
            if mod in self.curr_mods:
                self.curr_mods.remove(mod)
        return True

    def hard_reset(self):
        self.last_press = time.time()
        self.last_esc = time.time()
        self.rep = 1
        self.curr_mods.clear()
        self.mouse_reset()
        self.reset()
        return True

    def esc_check(self):
        if time.time() - self.last_esc < 0.5:
            self.hard_reset()
        self.last_esc = time.time()
        return True

    def mouse_down(self, button):
        if not self.mouse_is_down:
            pyautogui.mouseDown(button=button)
        self.mouse_is_down = True

    def mouse_up(self, button):
        self.mouse_is_down = False
        pyautogui.mouseUp(button=button)

    def mouse_move(self):
        last = time.perf_counter()
        base_speed = 25 * 100 / 3840  # percentage of screen per second

        while True:
            with self.lock:
                if not self.m_cmps:
                    break
                cmps = set(self.m_cmps)
                mods = set(self.curr_mods)

            slow = RLT in mods
            vx, vy = [sum(x) for x in zip(*cmps)]
            mag = math.sqrt(vx * vx + vy * vy)

            if mag > 0:
                monitor = self.curr_monitor()
                px_per_s = monitor.width * base_speed
                speed = px_per_s / (3 if slow else 1)
                dist = speed * (time.perf_counter() - last)
                scale = dist / mag
                pyautogui.moveRel(vx * scale, vy * scale)
            last = time.perf_counter()

            time.sleep(0.01)

    def scroll_move(self):
        while True:
            with self.lock:
                if not self.s_cmps:
                    break

                vy = sum(self.s_cmps)
                mag = -vy * (30 if RLT not in self.curr_mods else 10)
            pyautogui.scroll(mag)

            time.sleep(0.01)

    def key_add(self, key, container, thread_name, thread_fxn):
        t = None
        with self.lock:
            if not container or getattr(self, thread_name) is None:
                t = threading.Thread(target=thread_fxn, daemon=True)
                setattr(self, thread_name, t)
            container.add(key)
        if t:
            t.start()

    def key_remove(self, key, container, thread_name):
        with self.lock:
            container.discard(key)
            if not container:
                setattr(self, thread_name, None)

    def curr_monitor(self):
        pos = pyautogui.position()
        for m in self.monitors:
            if m.x <= pos[0] < m.x + m.width and m.y <= pos[1] < m.y + m.height:
                return m

    def mouse_jump(self, x, y):
        m = self.curr_monitor()
        if m is None:
            return
        pyautogui.moveTo(
            m.x + (x + 1) * m.width / 5,
            m.y + (y + 1) * m.height / 4,
        )

    def mouse_toggle_screen(self):
        m = self.curr_monitor()
        if m is None:
            return
        pos = pyautogui.position()
        rel_x, rel_y = (pos[0] - m.x) / m.width, (pos[1] - m.y) / m.height
        monitors = screeninfo.get_monitors()
        next_m = monitors[(monitors.index(m) + 1) % len(monitors)]
        pyautogui.moveTo(
            next_m.x + rel_x * next_m.width,
            next_m.y + rel_y * next_m.height,
        )

    def exit(self):
        if self.done:
            return
        self.done = True

        if self.alarm_clock:
            self.alarm_clock.save()

        threading.Timer(0.1, lambda: os._exit(0)).start()

    def restart(self):
        subprocess.Popen([sys.executable] + sys.argv, close_fds=True)
        self.exit()
