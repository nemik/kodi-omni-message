"""Stand-in for Kodi's ``xbmcaddon``, backed by a plain dict."""

SETTINGS = {
    "enabled": True,
    "heading": "Playback blocked",
    "message": "Playback is currently disabled.",
    "display_mode": "dialog",
    "notification_seconds": 5,
    "pin": "",
    "unlock_minutes": 30,
    "debug_logging": False,
}

STRINGS = {
    30020: "OK",
    30021: "Enter PIN",
    30022: "Enter PIN to allow playback",
    30023: "Incorrect PIN",
    30024: "Playback allowed for {} minutes",
}

DEFAULTS = dict(SETTINGS)


def reset():
    SETTINGS.clear()
    SETTINGS.update(DEFAULTS)


class Addon:
    def __init__(self, addon_id=""):
        self.id = addon_id

    def getSettingBool(self, key):
        return bool(SETTINGS[key])

    def getSettingString(self, key):
        return str(SETTINGS[key])

    def getSettingInt(self, key):
        return int(SETTINGS[key])

    def getLocalizedString(self, string_id):
        return STRINGS.get(string_id, "")

    def getAddonInfo(self, key):
        return {"id": self.id, "version": "1.0.0"}.get(key, "")
