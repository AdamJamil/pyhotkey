from collections import defaultdict as ddict, namedtuple
from functools import partial
import time
import threading
import math
from itertools import chain, combinations
import cli
from mouse import mouse_down, mouse_jump, mouse_move, mouse_toggle_screen, mouse_up, scroll_move
from state import State
from monitor import curr_monitor
from run_cmd import RunCMDThread
import os
import signal
import sys
import pathlib
import subprocess
import pyautogui
import screeninfo
from codeforces import put_code
from constants import (
    DEBUG_MODE,
    CAPS,
    RLT,
    RRT,
    LLT,
    MODIFIERS,
    OPEN_BRACKET,
    CLOSE_BRACKET,
)


import pywinauto.keyboard
from win32gui import GetWindowText, GetForegroundWindow


class KeyHandler:
    def __init__(self):
        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = False

        self.last_press = time.time()
        self.last_esc = time.time()
        self.rep = 1

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
                        # "C": [cli.CLIServer, [self.alarm_clock]],
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
                        "R": [mouse_down, ["left"]],
                        "3": [mouse_down, ["middle"]],
                        "W": [mouse_down, ["right"]],
                        "T": [pyautogui.scroll, [-3]],
                        "G": [pyautogui.scroll, [3]],
                        "H": [mouse_toggle_screen, []],
                    },
                ),
                frozenset([LLT]): ddict(
                    lambda: default,
                    {
                        "E": [mouse_down, ["left"]],
                        "2": [mouse_down, ["middle"]],
                        "Q": [mouse_down, ["right"]],
                        "W": [pyautogui.scroll, [-6]],
                        "S": [pyautogui.scroll, [6]],
                    },
                ),
                frozenset([RLT, RRT]): ddict(
                    lambda: default,
                    {
                        "R": [mouse_down, ["left"]],
                        "3": [mouse_down, ["middle"]],
                        "W": [mouse_down, ["right"]],
                        "H": [mouse_toggle_screen, []],
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
                        "R": [mouse_up, ["left"]],
                        "3": [mouse_up, ["middle"]],
                        "W": [mouse_up, ["right"]],
                    },
                ),
                frozenset([LLT]): ddict(
                    lambda: default,
                    {
                        "E": [mouse_up, ["left"]],
                        "2": [mouse_up, ["middle"]],
                        "Q": [mouse_up, ["right"]],
                    },
                ),
                frozenset([RLT]): ddict(lambda: default, {}),
                frozenset([RRT, RLT]): ddict(
                    lambda: default,
                    {
                        "R": [mouse_up, ["left"]],
                        "3": [mouse_up, ["middle"]],
                        "W": [mouse_up, ["right"]],
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
                    self.mouse_key_add,
                    [move_map[char]],
                ]
                self.binds_up[key][char] = [
                    self.mouse_key_remove,
                    [move_map[char]],
                ]
            for char in scroll_map.keys():
                self.binds_down[key][char] = [
                    self.scroll_key_add,
                    [scroll_map[char]],
                ]
                self.binds_up[key][char] = [
                    self.scroll_key_remove,
                    [scroll_map[char]],
                ]
        scroll_map = {
            "W": -1,
            "S": 1,
        }
        for key in filter(lambda x: LLT in x, self.binds_down.keys()):
            for char in move_map.keys():
                self.binds_down[key][char] = [
                    self.mouse_key_add,
                    [move_map[char]],
                ]
                self.binds_up[key][char] = [
                    self.mouse_key_remove,
                    [move_map[char]],
                ]
            for char in scroll_map.keys():
                self.binds_down[key][char] = [
                    self.scroll_key_add,
                    [scroll_map[char]],
                ]
                self.binds_up[key][char] = [
                    self.scroll_key_remove,
                    [scroll_map[char]],
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
                self.binds_down[key][char] = [mouse_jump, jump_map[char]]

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

        # insert and remove modifiers
        for key in self.binds_down.keys():
            for modifier in MODIFIERS:
                self.binds_down[key][modifier] = [State.add_modifier, [modifier]]
                self.binds_up[key][modifier] = [State.remove_modifier, [modifier]]

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
        value = self.binds_down[frozenset(State.get_held_modifiers())][event.Key]
        return type(value[0](*value[1])) == bool

    def key_up(self, event):
        value = self.binds_up[frozenset(State.get_held_modifiers())][event.Key]
        if DEBUG_MODE:
            print(event, State.get_held_modifiers())
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
        State.remove_modifier(CAPS)
        self.LMB_held = False
        State.update_monitors()

        return True

    def mouse_reset(self):
        State.LMB_held = False
        State.reset_mouse_direction()
        State.reset_scroll_direction()
        for mod in (LLT, RRT):
            State.remove_modifier(mod)
        return True

    def hard_reset(self):
        self.last_press = time.time()
        self.last_esc = time.time()
        self.rep = 1
        State.reset_modifiers()
        self.mouse_reset()
        self.reset()
        return True

    def esc_check(self):
        if time.time() - self.last_esc < 0.5:
            self.hard_reset()
        self.last_esc = time.time()
        return True

    def mouse_key_add(self, key):
        State.add_mouse_direction(*key)

        if State._mouse_move_thread is None:
            State._mouse_move_thread = threading.Thread(
                target=mouse_move, daemon=True
            )
            State._mouse_move_thread.start()

    def mouse_key_remove(self, key):
        State.remove_mouse_direction(*key)
        if not State.any_mouse_direction_held():
            State._mouse_move_thread = None

    def scroll_key_add(self, key):
        State.add_scroll_direction(key)

        if State._scroll_move_thread is None:
            State._scroll_move_thread = threading.Thread(
                target=scroll_move, daemon=True
            )
            State._scroll_move_thread.start()

    def scroll_key_remove(self, key):
        State.remove_scroll_direction(key)
        if not State.any_scroll_direction_held():
            State._scroll_move_thread = None

    def exit(self):
        if self.done:
            return
        self.done = True

        # if self.alarm_clock:
        #     self.alarm_clock.save()

        threading.Timer(0.1, lambda: os._exit(0)).start()

    def restart(self):
        subprocess.Popen([sys.executable] + sys.argv, close_fds=True)
        self.exit()
