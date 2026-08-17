"""Kodi player/monitor glue.

Kodi runs player callbacks on its own thread and warns against doing slow work
there, so the callbacks stay tiny: note the item, stop it, and hand the block
over to the service loop through ``blocked``.
"""

import base64
import binascii
import json
import threading

import xbmc

from resources.lib import settings as settings_module

# Custom JSON-RPC notifications (JSONRPC.NotifyAll) reach add-ons with the
# message name prefixed by "Other.". Anything else is Kodi's own traffic.
NOTIFICATION_PREFIX = "Other."
# Remote control is the master switch, not a timed unlock: "disable" allows
# playback until something turns blocking back on, here or in Kodi's settings.
MESSAGE_ENABLE = "enable"
MESSAGE_DISABLE = "disable"
REMOTE_MESSAGES = (MESSAGE_ENABLE, MESSAGE_DISABLE)


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

    def onNotification(self, sender, method, data):
        """Flip the master switch from JSONRPC.NotifyAll.

            {"jsonrpc": "2.0", "id": 1, "method": "JSONRPC.NotifyAll",
             "params": {"sender": "homebridge", "message": "disable",
                        "data": {"pin": "1234"}}}

        "enable" blocks playback and shows the message; "disable" allows
        everything. Both are written to the add-on settings, so the choice
        sticks until something changes it again — here, or in Kodi's own
        settings screen.

        Never raises: an exception here would take the monitor down with it.
        """
        if not method.startswith(NOTIFICATION_PREFIX):
            return
        message = method[len(NOTIFICATION_PREFIX):]
        if message not in REMOTE_MESSAGES:
            return

        try:
            enable = message == MESSAGE_ENABLE
            if not enable and not self._authorised(decode_notification_data(data)):
                settings_module.log(
                    "rejected {} from {}: bad PIN".format(message, sender)
                )
                return

            self._set_blocking(enable)
            settings_module.log(
                "blocking turned {} by {}".format("on" if enable else "off", sender)
            )
        except Exception as exc:  # pragma: no cover - defensive
            settings_module.log(
                "failed to handle {} from {}: {}".format(method, sender, exc),
                xbmc.LOGERROR,
            )

    def _set_blocking(self, enable):
        # Update in memory first so the next play attempt sees it even if the
        # settings write is slow, then persist. Writing the setting fires
        # onSettingsChanged, which reloads the same value harmlessly.
        current = self._policy.settings
        current.enabled = enable
        self._policy.update_settings(current)
        if enable:
            # Drop any PIN unlock window still running, so "on" means blocked
            # right now rather than once the window runs out.
            self._policy.revoke()
        settings_module.set_enabled(enable)

    def _authorised(self, payload):
        if not self._policy.has_pin():
            # No PIN configured means nothing to check against. Anyone who can
            # reach JSON-RPC can already disable the add-on outright.
            return True
        return self._policy.check_pin(str(payload.get("pin", "")))


def decode_notification_data(data):
    """Kodi hands the ``data`` param over as JSON text, base64 in old builds."""
    if isinstance(data, dict):
        return data
    if not data:
        return {}
    if isinstance(data, bytes):
        data = data.decode("utf-8", "replace")

    try:
        payload = json.loads(data)
    except ValueError:
        try:
            payload = json.loads(base64.b64decode(data).decode("utf-8"))
        except (ValueError, binascii.Error, UnicodeDecodeError):
            return {}
    return payload if isinstance(payload, dict) else {}
