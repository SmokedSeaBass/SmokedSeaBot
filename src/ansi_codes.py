from typing import NamedTuple


class EscapeCodes(NamedTuple):
    ESC = "\x1b"
    CSI = "\x1b["

class ColorCodes(NamedTuple):
    RESET = EscapeCodes.ESC + "[0m"

    ERROR = EscapeCodes.ESC + "[31m"
    WARNING = EscapeCodes.ESC + "[33m"
    INFO = EscapeCodes.ESC + "[39m"
    DEBUG = EscapeCodes.ESC + "[36m"
    CHAT = EscapeCodes.ESC + "[35m"

class CursorCodes(NamedTuple):
    HIDE = EscapeCodes.ESC + "[?25l"
    SHOW = EscapeCodes.ESC + "[?25h"


def color_str(msg: str, color: ColorCodes = None) -> str:
    if color is None:
        return msg
    return ''.join([color, msg, ColorCodes.RESET])