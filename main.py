import PyHook3
import pythoncom
import pyautogui
import time
from datetime import datetime, date, timedelta
import threading
import math
from collections import defaultdict as ddict
from functools import partial
import subprocess
import os
from win32gui import GetWindowText, GetForegroundWindow
from win10toast import ToastNotifier


class RunCMDThead(threading.Thread):
    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd

    def run(self):
        print("Running: " + self.cmd)
        subprocess.run(self.cmd)


class NotepadIO:
    @staticmethod
    def query(name, content):
        NotepadIO.show(name, content)
        time.sleep(0.1)
        pyautogui.press("end")
        while GetWindowText(GetForegroundWindow()).split(" ")[-1] == "Notepad":
            time.sleep(0.5)
        return open(os.getcwd() + "\\" + name + ".txt", "r").read()

    @staticmethod
    def show(name, content):
        file_name = os.getcwd() + "\\" + name + ".txt"
        file = open(file_name, "w")
        file.write(content)
        file.close()
        RunCMDThead("notepad.exe " + file_name).start()


class AlarmClock:
    def __init__(self):
        self.lock = threading.Lock()
        self.alarms = []
        self.alarm_thread = AlarmClock.AlarmThread(self)
        self.alarm_thread.start()

    def show_alarms(self):
        alarms_text = ""
        label = ""
        last_day = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=-1)
        for i, alarm in enumerate(self.alarms):
            alarm_time = alarm[0]
            if alarm_time > last_day + timedelta(days=1):
                last_day = alarm_time.replace(hour=0, minute=0, second=0, microsecond=0)
                if last_day <= datetime.today():
                    label = "[today]"
                elif last_day <= datetime.today() + timedelta(days=1):
                    label = "[tomorrow]"
                else:
                    label = "[" + str(last_day.month) + "/" + str(last_day.day) + "]"
                alarms_text += label + "\n"
            alarms_text += "\t[" + str(i+1) + "] " + str(alarm_time.strftime("%I:%M%p"))
            if alarm[1] != "":
                alarms_text += ": " + alarm[1]
            alarms_text += "\n"
            if alarm[2] != "":
                alarms_text += "\t\t" + alarm[2].replace("\n", "\n\t\t") + "\n"
        NotepadIO.show("Alarms", alarms_text)

        # you are allowed to edit the alarms
            # [R]

    class AlarmThread(threading.Thread):
        def __init__(self, alarm_clock):
            super().__init__()
            self.alarm_clock = alarm_clock

        def run(self):
            while True:
                time.sleep(1)
                self.alarm_clock.lock.acquire()
                alarms = self.alarm_clock.alarms
                if len(alarms) > 0 and alarms[0][0] < datetime.today():
                    print("u should see a toast")
                    toast = ToastNotifier()
                    if alarms[0][1] == "":
                        alarms[0][1] += "Alarm"
                    if alarms[0][2] == "":
                        alarms[0][2] += "Alarm"
                    toast.show_toast(alarms[0][1], alarms[0][2])
                    self.alarm_clock.alarms = alarms[1:]
                self.alarm_clock.lock.release()

    class SetAlarmThread(threading.Thread):
        def __init__(self, alarm_clock, q):
            super().__init__()
            self.alarm_clock = alarm_clock
            self.q = q

        def run(self):
            f = NotepadIO.query(self.q, "Time: \nName: \nInfo: ")
            time_text, alarm_name = f.split("\n")[:2]
            time_text = "".join(time_text.split(" ")[1:])
            alarm_name = " ".join(alarm_name.split(" ")[1:])
            alarm_info = f.split("\n")[2:]
            alarm_info = " ".join(("\n".join(alarm_info)).split(" ")[1:])

            # alarm time : can either provide delta or actual time
            # delta ex: +15m, +3h5m
            # actual ex: 3:10pm, 9:00am 2/15
            alarm_time = datetime.today().replace(microsecond=0)
            if time_text[0] == "+":
                ptr = 1
                while ptr < len(time_text):
                    cur = 0
                    while time_text[ptr] not in ['m', 'h', 'd', 's']:
                        cur = 10 * cur + int(time_text[ptr])
                        ptr += 1
                    alarm_time += timedelta(seconds=cur) * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[time_text[ptr]]
                    ptr += 1
            else:
                alarm_time = alarm_time.replace(second=0, microsecond=0)
                if len(time_text.split(" ")) == 2:
                    # M/D format
                    alarm_time = alarm_time.replace(day=int(time_text.split(" ")[1].split("/")[1]))
                    alarm_time = alarm_time.replace(month=int(time_text.split(" ")[1].split("/")[0]))
                # [h]h:mm<am/pm> format
                alarm_time = alarm_time.replace(hour=int(time_text.split(" ")[0].split(":")[0]))
                alarm_time = alarm_time.replace(minute=int(time_text.split(" ")[0].split(":")[1][:2]))
                if time_text.split(" ")[0].split(":")[1][2] == "p" and alarm_time.hour != 12:
                    alarm_time += timedelta(hours=12)

            if alarm_time < datetime.today():
                alarm_time += timedelta(days=1)

            print("Alarm set for " + str(alarm_time))

            self.alarm_clock.lock.acquire()
            self.alarm_clock.alarms.append([alarm_time, alarm_name, alarm_info])
            self.alarm_clock.alarms = sorted(self.alarm_clock.alarms)
            self.alarm_clock.lock.release()

    def add_alarm(self):
        AlarmClock.SetAlarmThread(self, "Set_an_alarm!").start()


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

        press = self.press
        mouse_add = self.mouse_add
        mouse_remove = self.mouse_remove
        default = [lambda: True, []]
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
                "E": [mouse_add, [0, -1]],
                "S": [mouse_add, [-1, 0]],
                "D": [mouse_add, [0, 1]],
                "F": [mouse_add, [1, 0]],
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
                "A": [self.alarm_clock.add_alarm, []],
                "V": [self.alarm_clock.show_alarms, []],
            }),
        })

        self.binds_up = ddict(lambda: ddict(lambda: default), {
            frozenset(): ddict(lambda: default, {}),
            frozenset(["Capital"]): ddict(lambda: default, {
                "E": [mouse_remove, [0, -1]],
                "S": [mouse_remove, [-1, 0]],
                "D": [mouse_remove, [0, 1]],
                "F": [mouse_remove, [1, 0]],
                "R": [pyautogui.mouseUp, []],
            }),
            frozenset(["F13"]): ddict(lambda: default, {}),
            frozenset(["Capital", "F13"]): ddict(lambda: default, {
                "R": [pyautogui.mouseUp, []],
            })
        })

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
        if self.m_thread is not None:
            self.m_thread.join()
        self.curr_mods.remove("Capital")
        return True

    def hard_reset(self):
        print("wtf")
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

    def key_down(self, event):
        if time.time() - self.last_press < 0.001:
            return True
        value = self.binds_down[frozenset(self.curr_mods)][event.Key]
        return value[0](*value[1]) is not None

    def key_up(self, event):
        value = self.binds_up[frozenset(self.curr_mods)][event.Key]
        return value[0](*value[1]) is not None


def main():
    hm = PyHook3.HookManager()
    handler = KeyHandler()
    hm.KeyDown = handler.key_down
    hm.KeyUp = handler.key_up
    hm.HookKeyboard()
    pythoncom.PumpMessages()


if __name__ == "__main__":
    main()
