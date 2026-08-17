"""Omni Message service entry point.

Runs for as long as Kodi does: waits for the player thread to flag a blocked
item, then shows the message and offers the PIN unlock.
"""

import xbmc

from resources.lib import settings as settings_module
from resources.lib import state
from resources.lib import ui
from resources.lib.blocker import OmniMonitor, OmniPlayer
from resources.lib.policy import Policy

POLL_SECONDS = 0.1


def handle_block(policy, player):
    """Show the message for one blocked item and replay it if unlocked."""
    if not policy.begin_handling():
        return
    try:
        path = player.take_blocked_path()
        current = policy.settings
        wants_pin = ui.show_block(current)
        if not wants_pin:
            return

        entered = ui.prompt_pin()
        if not entered:
            return
        if not policy.check_pin(entered):
            ui.notify_wrong_pin(current)
            settings_module.log("incorrect PIN entered")
            return

        policy.grant()
        ui.notify_unlocked(current, current.unlock_minutes)
        settings_module.debug(current, "unlocked, replaying {}".format(path))
        if path:
            player.play(path)
    finally:
        policy.end_handling()


def run():
    current = settings_module.load()
    policy = Policy(current)
    player = OmniPlayer(policy)
    monitor = OmniMonitor(policy)
    settings_module.log("service started")

    published = state.publish(policy)
    while not monitor.abortRequested():
        if player.blocked.is_set():
            player.blocked.clear()
            handle_block(policy, player)

        # Only writes when something moved: at most once a second while an
        # unlock counts down, and not at all while idle.
        if state.snapshot(policy) != published:
            published = state.publish(policy)

        if monitor.waitForAbort(POLL_SECONDS):
            break

    settings_module.log("service stopped")
    state.clear()
    del player
    del monitor


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # pragma: no cover - Kodi runtime only
        settings_module.log("service crashed: {}".format(exc), xbmc.LOGERROR)
        raise
