import threading
import NotepadIO
from datetime import datetime, timedelta


class SetAlarm(threading.Thread):
    def __init__(self, alarm_clock):
        super().__init__()
        self.alarm_clock = alarm_clock
        self.daemon = True
        self.start()

    def run(self):
        f = NotepadIO.query("Set_an_alarm!", "Time: \nName: \nInfo: ")
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
        self.alarm_clock.save()
        self.alarm_clock.lock.release()
