"""Dialogs and notifications. Only ever called from the service thread."""

import xbmcaddon
import xbmcgui

from resources.lib.settings import ADDON_ID, DISPLAY_NOTIFICATION

# Localised button/prompt labels, ids match resources/language/*/strings.po.
MSG_OK = 30020
MSG_ENTER_PIN = 30021
MSG_PIN_PROMPT = 30022
MSG_PIN_WRONG = 30023
MSG_UNLOCKED = 30024


def _(string_id):
    return xbmcaddon.Addon(ADDON_ID).getLocalizedString(string_id)


def show_block(settings):
    """Show the configured message.

    Returns True when the user asked to unlock with a PIN. Notification mode
    has nowhere to put that choice, so it never offers one.
    """
    dialog = xbmcgui.Dialog()
    if settings.display_mode == DISPLAY_NOTIFICATION:
        dialog.notification(
            settings.heading,
            settings.message,
            xbmcgui.NOTIFICATION_WARNING,
            max(1, settings.notification_seconds) * 1000,
        )
        return False

    if settings.pin:
        return bool(
            dialog.yesno(
                settings.heading,
                settings.message,
                nolabel=_(MSG_OK),
                yeslabel=_(MSG_ENTER_PIN),
            )
        )

    dialog.ok(settings.heading, settings.message)
    return False


def prompt_pin():
    """Ask for the PIN. Returns the entered digits, or "" if cancelled."""
    return xbmcgui.Dialog().input(
        _(MSG_PIN_PROMPT),
        type=xbmcgui.INPUT_NUMERIC,
        option=xbmcgui.ALPHANUM_HIDE_INPUT,
    )


def notify_wrong_pin(settings):
    xbmcgui.Dialog().notification(
        settings.heading, _(MSG_PIN_WRONG), xbmcgui.NOTIFICATION_ERROR, 4000
    )


def notify_unlocked(settings, minutes):
    if minutes <= 0:
        return
    xbmcgui.Dialog().notification(
        settings.heading,
        _(MSG_UNLOCKED).format(minutes),
        xbmcgui.NOTIFICATION_INFO,
        3000,
    )
