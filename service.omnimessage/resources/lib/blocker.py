"""Kodi player/monitor glue.

Kodi runs player callbacks on its own thread and warns against doing slow work
there, so the callbacks stay tiny: note the item, stop it, and hand the block
over to the service loop through ``blocked``.
"""

import threading

import xbmc

from resources.lib import settings as settings_module


class OmniPlayer(xbmc.Player):
    def __init__(self, policy):
        super().__init__()
        self._policy = policy
        self.blocked = threading.Event()
        self._path_lock = threading.Lock()
        self._blocked_path = None

    def onPlayBackStarted(self):
        self._intercept("onPlayBackStarted")

    def onAVStarted(self):
        # Safety net: some plugin and PVR paths reach AV without a usable
        # onPlayBackStarted, and should_block() is a no-op once we are unlocked.
        self._intercept("onAVStarted")

    def _intercept(self, source):
        if not self._policy.should_block():
            return

        path = self._current_path()
        with self._path_lock:
            self._blocked_path = path
        try:
            self.stop()
        except Exception as exc:  # pragma: no cover - Kodi runtime only
            settings_module.log("failed to stop playback: {}".format(exc), xbmc.LOGERROR)
        settings_module.debug(
            self._policy.settings, "blocked via {}: {}".format(source, path)
        )
        self.blocked.set()

    def _current_path(self):
        try:
            path = self.getPlayingFile()
        except Exception:
            path = ""
        if not path:
            path = xbmc.getInfoLabel("Player.FilenameAndPath")
        return path

    def take_blocked_path(self):
        with self._path_lock:
            path, self._blocked_path = self._blocked_path, None
        return path


class OmniMonitor(xbmc.Monitor):
    def __init__(self, policy):
        super().__init__()
        self._policy = policy

    def onSettingsChanged(self):
        current = settings_module.load()
        self._policy.update_settings(current)
        if not current.enabled:
            # Nothing to unlock while blocking is off; start clean when it
            # comes back on.
            self._policy.revoke()
        settings_module.debug(current, "settings reloaded")
