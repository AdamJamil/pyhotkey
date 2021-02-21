import time
from win32gui import GetWindowText, GetForegroundWindow
import pyautogui
import subprocess
import threading
import os
import pathlib


class RunCMDThead(threading.Thread):
    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd

    def run(self):
        print("Running: " + self.cmd)
        subprocess.run(self.cmd)


def query(name, content):
    root_dir = pathlib.Path(__file__).parent.absolute()
    show(name, content)
    time.sleep(0.1)
    pyautogui.press("end")
    curr = GetWindowText(GetForegroundWindow())
    while GetWindowText(GetForegroundWindow()).replace("*", "") == curr:
        time.sleep(0.1)
    file_name = os.path.join(root_dir, "IO", name + ".txt")
    return open(file_name, "r").read()


def show(name, content):
    root_dir = pathlib.Path(__file__).parent.absolute()
    file_name = os.path.join(root_dir, "IO", name + ".txt")
    file = open(file_name, "w")
    file.write(content)
    file.close()
    RunCMDThead("notepad.exe " + file_name).start()
