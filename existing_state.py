from typing import List
import screeninfo


class ExistingState:
    monitors: List[screeninfo.Monitor]

    @staticmethod
    def init():
        ExistingState.update_monitors(ExistingState)

    @staticmethod
    def update_monitors(self):
        self.monitors = screeninfo.get_monitors()


ExistingState.init()
