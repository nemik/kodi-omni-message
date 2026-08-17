"""Publish the current lock state where JSON-RPC clients can read it.

Kodi has no way for an add-on to answer a JSON-RPC call, but home window
properties are readable over JSON-RPC via ``XBMC.GetInfoLabels``, e.g.

    Window(Home).Property(omnimessage.unlocked)

which is enough for a Homebridge switch to show the real state.
"""

import xbmcgui

HOME_WINDOW = 10000

PROP_ENABLED = "omnimessage.enabled"
PROP_UNLOCKED = "omnimessage.unlocked"
PROP_SECONDS = "omnimessage.unlocked_seconds"
PROP_BLOCKING = "omnimessage.blocking"


def snapshot(policy):
    seconds = int(policy.unlocked_seconds_left())
    return {
        # The master switch: what a Homebridge on/off switch tracks.
        PROP_ENABLED: "1" if policy.settings.enabled else "0",
        # A PIN unlock running underneath it, which expires on its own.
        PROP_UNLOCKED: "1" if seconds > 0 else "0",
        PROP_SECONDS: str(seconds),
        PROP_BLOCKING: "1" if policy.should_block() else "0",
    }


def publish(policy):
    """Mirror the policy onto the home window. Returns what was written."""
    values = snapshot(policy)
    window = xbmcgui.Window(HOME_WINDOW)
    for key, value in values.items():
        window.setProperty(key, value)
    return values


def clear():
    window = xbmcgui.Window(HOME_WINDOW)
    for key in (PROP_ENABLED, PROP_UNLOCKED, PROP_SECONDS, PROP_BLOCKING):
        window.clearProperty(key)
