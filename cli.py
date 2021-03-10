import threading
import socket
from run_cmd import RunCMDThead
from alarm_clock import AlarmClock
import output
import pathlib
import os


class CLIServer(threading.Thread):
    def __init__(self, alarm_clock):
        super().__init__()
        self.daemon = True
        self.alarm_clock: AlarmClock = alarm_clock
        self.start()
        root_dir = pathlib.Path(__file__).parent.absolute()
        RunCMDThead("start /wait python " + os.path.join(root_dir, "cli.py"), shell=True)

    def run(self):
        s = socket.socket()  # Create a socket object
        s.bind((socket.gethostname(), 37156))

        s.listen(5)
        c, addr = s.accept()
        next_line = c.recv(1024).decode()
        prev = ""

        while next_line != "q":
            if next_line == "&^EMPTY":
                next_line = ""
            cmds = next_line.split(";")
            if len(prev) > 0:
                cmds[0] = prev + "\n" + cmds[0]

            send = []

            for cmd in (cmds if len(next_line) > 0 and next_line[-1] == ";" else cmds[:-1]):
                if cmd == "":
                    continue
                lines = [x.split(" ") for x in cmd.split("\n")]
                lines = [line for line in lines if len(line) > 0]

                if lines[0][0] == "a":
                    send.append(self.alarm_clock.add_argparse(lines))
                elif lines[0][0] == "v":
                    output.show(self.alarm_clock.show_events(), "schedule")
                    send.append("Opened schedule :D\n")
                elif lines[0][0] == "r":
                    send.append(self.alarm_clock.remove(lines[0][1]))
                elif lines[0][0] == "c":
                    send.append(self.alarm_clock.chain(lines))
                else:
                    send.append("wtf did u jsut say to me\n")

            if len(next_line) > 0 and next_line[-1] == ";":
                prev = ""
            else:
                prev = cmds[-1]
                send.append("..")

            c.send("".join(send).encode())
            next_line = c.recv(1024).decode()

        c.send("q".encode())
        c.close()
        s.close()


# client program
def client():
    server_socket = socket.socket()
    server_socket.connect((socket.gethostname(), 37156))

    def read():
        x = input()
        if x == "":
            return "&^EMPTY"
        return x

    while True:
        server_socket.send(read().encode())
        response = server_socket.recv(1024).decode()

        if response == "q":
            server_socket.close()
            break

        print(response, end="")


if __name__ == "__main__":
    client()
