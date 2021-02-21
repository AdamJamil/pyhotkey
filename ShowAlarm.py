import threading
from datetime import datetime, timedelta
import NotepadIO


class ShowAlarm(threading.Thread):
    def __init__(self, alarm_clock):
        super().__init__()
        self.alarm_clock = alarm_clock
        self.start()

    def run(self):
        alarms_text = ""
        last_day = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=-1)
        for ptr, alarm in enumerate(self.alarm_clock.alarms):
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
            alarms_text += "\t[" + str(ptr + 1) + "] " + str(alarm_time.strftime("%I:%M%p"))
            if alarm[1] != "":
                alarms_text += ": " + alarm[1]
            alarms_text += "\n"
            if alarm[2] != "":
                alarms_text += "\t\t" + alarm[2].replace("\n", "\n\t\t") + "\n"
        update = NotepadIO.query("Alarms", alarms_text)

        if alarms_text == update:
            return

        print("Updating alarms")
        self.alarm_clock.alarms.clear()
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
                self.alarm_clock.alarms.append([alarm_time, desc, info])

        self.alarm_clock.alarms = sorted(self.alarm_clock.alarms)
