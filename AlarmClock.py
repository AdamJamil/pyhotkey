import threading
from win10toast import ToastNotifier
from datetime import datetime
import time


class AlarmClock:
    def __init__(self):
        self.lock = threading.Lock()
        self.alarms = []
        self.alarm_thread = AlarmClock.AlarmThread(self)
        self.alarm_thread.start()

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
