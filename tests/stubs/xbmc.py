"""Minimal stand-in for Kodi's built-in ``xbmc`` module.

Only covers what the add-on touches, so the real code can be imported and
driven on a machine with no Kodi installed.
"""

LOGDEBUG = 0
LOGINFO = 1
LOGWARNING = 2
LOGERROR = 3
LOGFATAL = 4

LOG = []
INFO_LABELS = {}


def log(msg, level=LOGINFO):
    LOG.append((level, msg))


def getInfoLabel(label):
    return INFO_LABELS.get(label, "")


def reset():
    LOG.clear()
    INFO_LABELS.clear()


class Player:
    """Records the calls the add-on makes instead of touching a real player."""

    def __init__(self):
        self.playing_file = ""
        self.stop_calls = 0
        self.played = []

    def getPlayingFile(self):
        if not self.playing_file:
            raise RuntimeError("Kodi is not playing a file")
        return self.playing_file

    def stop(self):
        self.stop_calls += 1
        self.playing_file = ""

    def play(self, item="", listitem=None, windowed=False, startpos=-1):
        self.played.append(item)
        self.playing_file = item


class Monitor:
    def __init__(self):
        self._abort = False

    def abortRequested(self):
        return self._abort

    def waitForAbort(self, timeout=None):
        return self._abort

    def onSettingsChanged(self):
        pass
