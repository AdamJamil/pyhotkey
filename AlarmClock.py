import threading
from win10toast import ToastNotifier
from datetime import datetime, timedelta
import time
import pathlib
import os


class AlarmClock:
    def __init__(self):
        self.lock = threading.Lock()
        self.alarms = []
        file_name = os.path.join(pathlib.Path(__file__).parent.absolute(), "IO", "data.txt")
        if os.path.exists(file_name):
            self.load_alarms(open(file_name, "r").read())
        self.alarm_thread = AlarmClock.AlarmThread(self)
        self.alarm_thread.start()

    class AlarmThread(threading.Thread):
        def __init__(self, alarm_clock):
            super().__init__()
            self.daemon = True
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

    def load_alarms(self, update):
        self.alarms.clear()
        curr_label = "[today]"
        lines = update.split("\n")
        ptr = 0
        while ptr < len(lines):
            line = lines[ptr]
            if len(line) == 0:
                ptr += 1
                pass
            elif line[0] == "[":
                ptr += 1
                curr_label = line.strip()
            elif line[1] == "[":
                if line[2] == "-":
                    ptr += 1
                    while ptr < len(lines) and len(lines[ptr]) > 1 and "[" in lines[ptr][:2]:
                        ptr += 1
                    continue

                alarm_time_text = ":".join(line.split(" ")[1].split(":")[:2])
                alarm_time = datetime.strptime(alarm_time_text, "%I:%M%p")
                ref_time = datetime.now()
                day = curr_label[1:-1]
                if day == "tomorrow":
                    ref_time += timedelta(days=1)
                elif day != "today":
                    ref_time = ref_time.replace(month=int(day.split("/")[0]), day=int(day.split("/")[1]))

                alarm_time = alarm_time.replace(month=ref_time.month, day=ref_time.day, year=ref_time.year)

                desc = ""
                if len(line.split(":")) >= 3:
                    desc = ":".join(line.split(":")[2:])

                info = ""
                ptr += 1
                while ptr < len(lines) and len(lines[ptr]) >= 2 and lines[ptr][:2] == "\t\t":
                    info += lines[ptr][2:] + "\n"
                    ptr += 1
                if len(info) > 0:
                    info = info[:-1]
                self.alarms.append([alarm_time, desc, info])

        self.alarms = sorted(self.alarms)
