import threading
from datetime import datetime, timedelta
from time import sleep
import pathlib
import os
from datetime import datetime as dt
from dataclasses import dataclass, field
from typing import Iterable, Union
import pickle
import traceback
from functools import total_ordering
import output

import platform

if platform.system() == "Windows":
    import pyttsx3
    from win10toast import ToastNotifier


def short_time_view(time: dt) -> str:
    return time.strftime("%#I%p") if time.minute == 0 else time.strftime("%#I:%M%p")


def duration(dur: str) -> timedelta:
    ret: timedelta = timedelta()
    ptr = 0
    while ptr < len(dur):
        cur = 0
        while dur[ptr] not in ['m', 'h', 'd', 's']:
            cur = 10 * cur + int(dur[ptr])
            ptr += 1
        time_map = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        ret += timedelta(seconds=cur) * time_map[dur[ptr]]
        ptr += 1
    return ret


def parse_time(time_string: str) -> dt:
    if time_string[0] == "+":
        return dt.now() + duration(time_string[1:])

    hour = int(time_string[0]) if len(time_string) % 3 == 0 else int(time_string[:2])
    hour = (hour % 12) + (12 * (time_string[-2].lower() == "p"))
    minute = int(time_string.split(":")[1][:2]) if len(time_string) > 4 else 0
    return dt.now().replace(microsecond=0, second=0, minute=minute, hour=hour)


@total_ordering
@dataclass
class Notif:
    time: dt
    name: str
    body: str
    remove: bool = False
    parent: "Event" = None

    def __lt__(self, other: "Notif"):
        return self.time < other.time

    def __repr__(self):
        ret = "Notif("
        ret += self.time.strftime("%#m/%#d %#I:%M%p %#Ss")
        if len(self.name) > 0:
            ret += ", " + self.name
        if len(self.body) > 0:
            ret += ", " + self.body
        if self.remove:
            ret += ", True"
        if self.parent:
            ret += ", Event(" + self.parent.name + ")"
        ret += ")"
        return ret


@total_ordering
@dataclass
class Event:
    time: dt
    end: dt = None
    name: str = ""
    info: str = ""
    options: dict[str, Union[int, list[int]]] = field(default_factory=lambda: {
        "s_remind": 1,
        "s_remind_list": [],
        "e_remind": 0,
        "e_remind_list": [],
    })

    no_opt = {
        "s_remind": 0,
        "s_remind_list": [],
        "e_remind": 0,
        "e_remind_list": [],
    }

    def day_string(self):
        now = dt.now().replace(hour=0, second=0, microsecond=0)
        day = self.time.replace(hour=0, second=0, microsecond=0)

        if day.year != now.year:
            return day.strftime("%#m/%#d/%y")
        if day.month != now.month:
            return day.strftime("%#m/%#d")

        if day.day == now.day:
            return "today"
        if day.day == (now + timedelta(days=1)).day:
            return "tomorrow"
        if day.day == (now + timedelta(days=2)).day:
            return "2morrow"
        for dist in range(2, 7):
            if day.day == (now + timedelta(days=dist)).day:
                return day.strftime("this %A").lower()
        for dist in range(8, 14):
            if day.day == (now + timedelta(days=dist)).day:
                return day.strftime("next %A").lower()

        return day.strftime("%#m/%#d")

    def parse(self) -> list[Notif]:
        notifs = [Notif(time=self.time, name=self.name, body=self.info)]

        def f(x: dt, y: Iterable[int], c: int) -> Iterable[Notif]:
            if len(list(y)) == 0:
                return ()
            name_suf = (" starts" if x == self.time else " ends") + " in "
            return (Notif(x - timedelta(minutes=c * i), self.name + name_suf + str(i * c), self.info) for i in y)

        notifs += f(self.time, range(1, self.options["s_remind"] + 1), 5)
        notifs += f(self.end, range(1, self.options["e_remind"] + 1), 5)
        notifs += f(self.time, self.options["s_remind_list"], 1)
        notifs += f(self.end, self.options["e_remind_list"], 1)

        notifs.sort()
        notifs[-1].remove = True
        notifs[-1].parent = self

        return notifs

    def schedule_view(self):
        view = "\t" + short_time_view(self.time)
        if self.end:
            view += " - " + short_time_view(self.end)
        if len(self.name) > 0:
            view += ": " + self.name
        if len(self.info) > 0:
            view += "\n\t\t" + self.info.replace("\n", "\n\t\t")
        return view

    def __lt__(self, other):
        return self.time < other.time


class AlarmThread(threading.Thread):
    def __init__(self, alarm_clock):
        super().__init__()
        self.daemon = True
        self.alarm_clock = alarm_clock

    def run(self):
        while True:
            sleep(1)
            self.alarm_clock.lock.acquire()
            notifs: list[Notif] = self.alarm_clock.notifs
            if len(notifs) > 0 and notifs[0].time < datetime.today():
                print("u should see a toast")
                toast = ToastNotifier()
                name = notifs[0].name if len(notifs[0].name) > 0 else "Event"
                body = notifs[0].body if len(notifs[0].body) > 0 else "bottom text"
                thread1 = threading.Thread(target=lambda: (toast.show_toast(name, body)))
                thread2 = threading.Thread(target=lambda: (
                    self.alarm_clock.speaker.say(name),
                    self.alarm_clock.speaker.runAndWait())
                                           )
                thread1.start()
                thread2.start()

                if notifs[0].remove:
                    self.alarm_clock.events.remove(notifs[0].parent)

                self.alarm_clock.notifs = notifs[1:]
                self.alarm_clock.save()
            self.alarm_clock.lock.release()


class AlarmClock:
    def __init__(self):
        self.lock = threading.Lock()
        self.events: list[Event] = []
        self.notifs: list[Notif] = []
        file_name = os.path.join(pathlib.Path(__file__).parent.absolute(), "IO", "events")
        if os.path.exists(file_name):
            self.load()
        self.alarm_thread = AlarmThread(self)
        self.alarm_thread.start()
        self.speaker = pyttsx3.init()

    def add(self, event):
        self.events.append(event)
        self.events.sort()
        self.update()

    def remove_(self, pos):
        n = self.events.pop(int(pos) - 1).name
        self.update()
        return n

    def remove(self, pos):
        try:
            ret = "Removed event " + self.remove_(pos) + " :D\n"
            return ret
        except (IndexError, ValueError):
            return "Fuck off moron :D\n"

    def add_argparse(self, lines):
        try:
            start_time: dt = parse_time(lines[0][1].split("-")[0])
            end_time: dt = parse_time(lines[0][1].split("-")[1]) if "-" in lines[0][1] else None
            name = " ".join(lines[0][2:])
            info = ""
            options = {
                "s_remind": 1,
                "s_remind_list": [],
                "e_remind": 0,
                "e_remind_list": [],
            }

            for line in lines[1:]:
                if line == "":
                    continue
                i = 0
                while i < len(line):
                    if line[i][0] != "-":
                        info += " ".join(line[i:])
                        break
                    elif line[i] == "-s":
                        if line[i + 1][0] == "[":
                            options["s_remind_list"] = [int(x) for x in line[i + 1][1:-1].split(",")]
                        else:
                            options["s_remind"] = int(line[i + 1])
                        i += 2
                    elif line[i] == "-e":
                        if line[i + 1][0] == "[":
                            options["e_remind_list"] = [int(x) for x in line[i + 1][1:-1].split(",")]
                        else:
                            options["e_remind"] = int(line[i + 1])
                        i += 2
                    elif line[i] == "-d":
                        date = line[i + 1].split("/")
                        month = int(date[0])
                        day = int(date[1])
                        year = start_time.year
                        if len(date) == 3:
                            year = int(date[2])

                        if end_time:
                            end_time += start_time.replace(day=day, month=month, year=year) - start_time
                        start_time = start_time.replace(day=day, month=month, year=year)
                        i += 2
                    else:
                        break

            self.add(Event(start_time, end_time, name, info, options))
            return "Alarm added successfully :D\n"
        except (IndexError, ValueError):
            traceback.print_exc()
            return "Fuck off moron :D\n"

    def chain(self, lines):
        num_events = 0
        try:
            curr = parse_time(lines[0][1])
            for line in lines[1:]:
                if len(line) == 0:
                    continue
                if line[0][0] != "-":
                    name = " ".join(line[:-1])
                    event_dur = duration(line[-1])
                    self.add(Event(curr, curr + event_dur, name, "", {
                        "s_remind": 0,
                        "s_remind_list": [],
                        "e_remind": 0,
                        "e_remind_list": [2],
                    }))
                    curr += event_dur
                    num_events += 1
                elif line[0] == "-g":
                    curr += duration(line[1])
                elif line[0] == "-e":
                    self.add(Event(time=curr, name=" ".join(line[1:]), info="bottom text", options=Event.no_opt))
            return "Successfully set " + str(num_events) + " events :D\n"
        except (IndexError, ValueError):
            return "Fuck off moron :D\n"

    def delay(self, lines):
        self.events.sort()
        try:
            delay = duration(lines[0][1])
            self.events[0].time += delay
            if self.events[0].end:
                self.events[0].end += delay
            else:
                self.update()
                return "Successfully delayed your day! :D\n"
            for i in range(len(self.events) - 1):
                if self.events[i + 1].time == self.events[i].end:
                    self.events[i + 1].time += delay
                    if self.events[i + 1].end:
                        self.events[i + 1].end += delay
                    else:
                        break
                else:
                    break
            self.update()
            return "Successfully delayed your day! :D\n"
        except:
            traceback.print_exc()
            return "Fuck off moron :D\n"

    def load(self):
        root_dir = pathlib.Path(__file__).parent.absolute()
        file_name = os.path.join(root_dir, "IO", "events")
        with open(file_name, "rb") as f:
            self.events: list[Event] = pickle.load(f)
            self.events.sort()
        self.update()

    def update(self):
        self.events.sort()

        temp_notifs: list[Notif] = [x for y in self.events for x in y.parse()]
        self.notifs: list[Notif] = [x for x in temp_notifs if x.time > datetime.now()]

        for x in filter(lambda x: x not in self.notifs and x.remove, temp_notifs):
            self.events.remove(x.parent)

        self.notifs.sort()

        self.save()

    def save(self):
        root_dir = pathlib.Path(__file__).parent.absolute()
        file_name = os.path.join(root_dir, "IO", "events")
        with open(file_name, "wb") as f:
            pickle.dump(self.events, f)

    def show_events(self):
        if len(self.events) == 0:
            return ""

        last_label = self.events[0].day_string()
        events_string = "[" + last_label + "]\n" + self.events[0].schedule_view() + "\n"

        for event in self.events[1:]:
            if event.day_string() != last_label:
                events_string += "\n[" + event.day_string() + "]\n"
            last_label = event.day_string()
            events_string += event.schedule_view() + "\n"

        return events_string
