import time
from win32gui import GetWindowText, GetForegroundWindow
import pyautogui
import subprocess
import threading
import os


class RunCMDThead(threading.Thread):
    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd

    def run(self):
        print("Running: " + self.cmd)
        subprocess.run(self.cmd)


def query(name, content):
    show(name, content)
    time.sleep(0.1)
    pyautogui.press("end")
    curr = GetWindowText(GetForegroundWindow())
    while GetWindowText(GetForegroundWindow()).replace("*", "") == curr:
        time.sleep(0.1)
    return open(os.getcwd() + "\\" + name + ".txt", "r").read()


def show(name, content):
    file_name = os.getcwd() + "\\" + name + ".txt"
    file = open(file_name, "w")
    file.write(content)
    file.close()
    RunCMDThead("notepad.exe " + file_name).start()
