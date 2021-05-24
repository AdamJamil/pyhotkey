import subprocess
import threading


class RunCMDThread(threading.Thread):
    def __init__(self, cmd, daemon=True, **kwargs):
        super().__init__()
        self.daemon = daemon
        self.cmd = cmd
        self.kwargs = kwargs
        self.start()

    def run(self):
        print("Running: " + self.cmd)
        subprocess.run(self.cmd, **self.kwargs)
