import subprocess
import threading


class RunCMDThread(threading.Thread):
    def __init__(self, cmd, **kwargs):
        super().__init__()
        self.daemon = True
        self.cmd = cmd
        self.kwargs = kwargs
        self.start()

    def run(self):
        print("Running: " + self.cmd)
        subprocess.run(self.cmd, **self.kwargs)
