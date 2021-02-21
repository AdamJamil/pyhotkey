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
        self.alarm_clock.load_alarms(update)
