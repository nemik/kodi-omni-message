"""Stand-in for Kodi's ``xbmcvfs``. Present so imports resolve."""

import os


def translatePath(path):
    return path


def exists(path):
    return os.path.exists(path)
