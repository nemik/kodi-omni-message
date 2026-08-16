"""Typed snapshot of the add-on settings."""

import xbmc
import xbmcaddon

DISPLAY_DIALOG = "dialog"
DISPLAY_NOTIFICATION = "notification"

ADDON_ID = "service.omnimessage"


class Settings:
    __slots__ = (
        "enabled",
        "heading",
        "message",
        "display_mode",
        "notification_seconds",
        "pin",
        "unlock_minutes",
        "debug_logging",
    )

    def __init__(
        self,
        enabled=True,
        heading="Playback blocked",
        message="Playback is currently disabled.",
        display_mode=DISPLAY_DIALOG,
        notification_seconds=5,
        pin="",
        unlock_minutes=30,
        debug_logging=False,
    ):
        self.enabled = enabled
        self.heading = heading
        self.message = message
        self.display_mode = display_mode
        self.notification_seconds = notification_seconds
        self.pin = pin
        self.unlock_minutes = unlock_minutes
        self.debug_logging = debug_logging


def load():
    """Read current settings from Kodi.

    A fresh ``Addon`` instance every time: cached ones go stale in Kodi 19+ and
    keep handing back the values from when they were created.
    """
    addon = xbmcaddon.Addon(ADDON_ID)
    return Settings(
        enabled=addon.getSettingBool("enabled"),
        heading=addon.getSettingString("heading"),
        message=addon.getSettingString("message"),
        display_mode=addon.getSettingString("display_mode"),
        notification_seconds=addon.getSettingInt("notification_seconds"),
        pin=addon.getSettingString("pin"),
        unlock_minutes=addon.getSettingInt("unlock_minutes"),
        debug_logging=addon.getSettingBool("debug_logging"),
    )


def log(message, level=xbmc.LOGINFO):
    xbmc.log("[{}] {}".format(ADDON_ID, message), level)


def debug(settings, message):
    if settings.debug_logging:
        log(message, xbmc.LOGDEBUG)
