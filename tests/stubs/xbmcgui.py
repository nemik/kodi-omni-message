"""Stand-in for Kodi's ``xbmcgui``.

Dialog answers are queued up front by the tests; every call is recorded.
"""

NOTIFICATION_INFO = "info"
NOTIFICATION_WARNING = "warning"
NOTIFICATION_ERROR = "error"

INPUT_ALPHANUM = 0
INPUT_NUMERIC = 1
ALPHANUM_HIDE_INPUT = 2

CALLS = []
YESNO_ANSWERS = []
INPUT_ANSWERS = []


def reset():
    CALLS.clear()
    YESNO_ANSWERS.clear()
    INPUT_ANSWERS.clear()


class Dialog:
    def ok(self, heading, message):
        CALLS.append(("ok", heading, message))
        return True

    def yesno(self, heading, message, nolabel="", yeslabel="", **kwargs):
        CALLS.append(("yesno", heading, message, nolabel, yeslabel))
        return YESNO_ANSWERS.pop(0) if YESNO_ANSWERS else False

    def input(self, heading, defaultt="", type=INPUT_ALPHANUM, option=0, **kwargs):
        CALLS.append(("input", heading, type, option))
        return INPUT_ANSWERS.pop(0) if INPUT_ANSWERS else ""

    def notification(self, heading, message, icon=NOTIFICATION_INFO, time=5000, **kwargs):
        CALLS.append(("notification", heading, message, icon, time))
