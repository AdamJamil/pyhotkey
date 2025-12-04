import sys
import platform

IS_WINDOWS = platform.system() == "Windows"
DEBUG_MODE = sys.stdout is not None and sys.stdout.isatty()

CAPS = "F13"
LLT = "F14"  # left left thumb
RLT = "F15"  # right left thumb
RRT = "F16"  # right right thumb
MODIFIERS = [CAPS, LLT, RLT, RRT]


OPEN_BRACKET = "Oem_4" if IS_WINDOWS else "["
CLOSE_BRACKET = "Oem_6" if IS_WINDOWS else "]"