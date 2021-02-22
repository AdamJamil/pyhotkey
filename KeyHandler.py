from collections import defaultdict as ddict
from functools import partial
from SetAlarm import SetAlarm
from ShowAlarm import ShowAlarm
from AlarmClock import AlarmClock
import pyautogui
import time
import threading
import math
from itertools import chain, combinations
import pathlib
import os
import sys


class KeyHandler:
    def __init__(self):
        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = False

        self.last_press = time.time()
        self.last_esc = time.time()
        self.rep = 1
        self.modifiers = {"Capital", "F13", "F14"}
        self.curr_mods = set()
        self.m_thread = None
        self.m_cmps = set()
        self.alarm_clock = AlarmClock()
        self.done = False

        default = [lambda: True, []]
        press = self.press
        mouse_add = self.mouse_add
        mouse_remove = self.mouse_remove
        self.binds_down = ddict(lambda: ddict(lambda: default), {
            frozenset(): ddict(lambda: default, {
                "Oem_4": [press, ["backspace"]],
                "Oem_6": [press, ["delete"]],
            }),
            frozenset(["Capital"]): ddict(lambda: default, {
                "I": [press, ["up"]],
                "J": [press, ["left"]],
                "K": [press, ["down"]],
                "L": [press, ["right"]],
                "U": [press, ["ctrl", "left"]],
                "O": [press, ["ctrl", "right"]],
                "Y": [press, ["end"]],
                "H": [press, ["home"]],
                "R": [pyautogui.mouseDown, []],
                "Oem_3": [press, ["capslock"]],
            }),
            frozenset(["F13"]): ddict(lambda: default, {
                "A": [press, ["["]],
                "S": [press, ["{"]],
                "D": [press, ["("]],
                "F": [press, ["\\"]],
                "G": [press, ["+"]],
                "T": [press, ["_"]],
                "Y": [press, ["="]],
                "H": [press, ["-"]],
                "J": [press, ["/"]],
                "K": [press, [")"]],
                "L": [press, ["}"]],
                "Oem_1": [press, ["]"]],
                "Q": [press, ["volumemute"]],
                "W": [press, ["volumedown"]],
                "E": [press, ["volumeup"]],
            }),
            frozenset(["Capital", "F13"]): ddict(lambda: default, {
                "I": [press, ["shift", "up"]],
                "J": [press, ["shift", "left"]],
                "K": [press, ["shift", "down"]],
                "L": [press, ["shift", "right"]],
                "U": [press, ["ctrl", "shift", "left"]],
                "O": [press, ["ctrl", "shift", "right"]],
                "Y": [press, ["shift", "end"]],
                "H": [press, ["shift", "home"]],
                "R": [pyautogui.mouseDown, []],
            }),
            frozenset(["F14"]): ddict(lambda: default, {
                "A": [SetAlarm, [self.alarm_clock]],
                "V": [ShowAlarm, [self.alarm_clock]],
            }),
            frozenset(["Capital", "F13", "F14"]): ddict(lambda: default, {
                "Q": [self.exit, []]
            })
        })

        self.binds_up = ddict(lambda: ddict(lambda: default), {
            frozenset(): ddict(lambda: default, {}),
            frozenset(["Capital"]): ddict(lambda: default, {
                "R": [pyautogui.mouseUp, []],
            }),
            frozenset(["F13"]): ddict(lambda: default, {}),
            frozenset(["Capital", "F13"]): ddict(lambda: default, {
                "R": [pyautogui.mouseUp, []],
            })
        })

        # add default keys
        mods_list = list(self.modifiers)
        for key in chain.from_iterable(combinations(mods_list, r) for r in range(len(mods_list) + 1)):
            if frozenset(key) not in self.binds_down:
                self.binds_down[frozenset(key)] = ddict(lambda: default)
            if frozenset(key) not in self.binds_up:
                self.binds_up[frozenset(key)] = ddict(lambda: default)

        # mouse movement
        move_map = {
            "E": [0, -1],
            "S": [-1, 0],
            "D": [0, 1],
            "F": [1, 0],
        }
        for key in filter(lambda x: "Capital" in x, self.binds_down.keys()):
            for char in move_map.keys():
                self.binds_down[key][char] = [mouse_add, move_map[char]]
                self.binds_up[key][char] = [mouse_remove, move_map[char]]

        # allow for repetition
        for i in range(1, 10):
            self.binds_down[frozenset(["Capital"])][str(i)] = [partial(self.__setattr__, "rep"), [i]]
            self.binds_down[frozenset(["Capital", "F13"])][str(i)] = [partial(self.__setattr__, "rep"), [i]]

        # insert and remove modifiers
        for key in self.binds_down.keys():
            for modifier in self.modifiers:
                self.binds_down[key][modifier] = [self.curr_mods.add, [modifier]]
                self.binds_up[key][modifier] = [self.curr_mods.remove, [modifier]]

        # soft reset
        for key in self.binds_up.keys():
            self.binds_up[key]["Capital"] = [self.reset, []]

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
        return type(value[0](*value[1])) == bool

    def press(self, *keys):
        for _ in range(self.rep):
            self.last_press = time.time()
            for k in keys:
                pyautogui.keyDown(k)
            for k in reversed(keys):
                pyautogui.keyUp(k)
        self.rep = 1

    def reset(self):
        self.rep = 1
        self.m_cmps.clear()
        if self.m_thread is not None:
            self.m_thread.join()
        self.curr_mods.remove("Capital")
        return True

    def hard_reset(self):
        self.last_press = time.time()
        self.last_esc = time.time()
        self.rep = 1
        self.curr_mods.clear()
        self.m_cmps.clear()
        if self.m_thread is not None:
            self.m_thread.join()
        self.m_thread = None

    def esc_check(self):
        if time.time() - self.last_esc < 0.5:
            self.hard_reset()
        self.last_esc = time.time()
        return True

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
            mag = math.sqrt(vx * vx + vy * vy) / 6 / (1 + 4 * ("F13" not in self.curr_mods))

            if mag > 0:
                pyautogui.move(vx / mag, vy / mag)

    def mouse_add(self, *vel):
        lock = threading.Lock()
        lock.acquire()
        if not self.m_cmps:
            self.m_thread = threading.Thread(target=self.mouse_move)
            self.m_thread.start()
        self.m_cmps.add(vel)
        lock.release()

    def mouse_remove(self, *vel):
        lock = threading.Lock()
        lock.acquire()
        self.m_cmps.remove(vel)
        if not self.m_cmps:
            self.m_thread.join()
        lock.release()

    def exit(self):
        if self.done:
            return
        self.done = True
        self.alarm_clock.save()
        exit()
