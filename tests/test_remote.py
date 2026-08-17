"""Remote control over JSON-RPC: JSONRPC.NotifyAll in, window properties out.

The remote API is the master switch, not the timed PIN unlock: "disable" allows
playback until something turns blocking back on.
"""

import json

import pytest
import xbmcaddon
import xbmcgui
from resources.lib import state
from resources.lib.blocker import OmniMonitor, decode_notification_data
from resources.lib.policy import Policy
from resources.lib.settings import Settings


def make_monitor(clock=None, **overrides):
    policy = Policy(Settings(**overrides), **({"clock": clock} if clock else {}))
    return policy, OmniMonitor(policy)


def notify(monitor, message, payload=None, sender="homebridge"):
    """Deliver a notification the way Kodi does: data as a JSON string."""
    data = json.dumps(payload) if payload is not None else ""
    monitor.onNotification(sender, "Other." + message, data)


def test_disable_allows_playback():
    policy, monitor = make_monitor(pin="4242")

    notify(monitor, "disable", {"pin": "4242"})

    assert policy.should_block() is False


def test_disable_does_not_expire():
    """Unlike the PIN unlock, it stays off until something turns it back on."""
    now = [1000.0]
    policy, monitor = make_monitor(clock=lambda: now[0], pin="4242", unlock_minutes=30)

    notify(monitor, "disable", {"pin": "4242"})
    now[0] += 30 * 24 * 3600  # a month later

    assert policy.should_block() is False


def test_disable_is_persisted_to_the_addon_settings():
    policy, monitor = make_monitor(pin="4242")

    notify(monitor, "disable", {"pin": "4242"})

    assert xbmcaddon.SETTINGS["enabled"] is False, "must survive a Kodi restart"


def test_enable_blocks_again():
    policy, monitor = make_monitor(pin="4242", enabled=False)

    notify(monitor, "enable")

    assert policy.should_block() is True
    assert xbmcaddon.SETTINGS["enabled"] is True


def test_enable_cancels_a_running_pin_unlock():
    policy, monitor = make_monitor(pin="4242", unlock_minutes=30)
    policy.grant()

    notify(monitor, "enable")

    assert policy.should_block() is True, "on means blocked now, not later"


def test_enable_needs_no_pin():
    """Turning blocking on only ever removes access."""
    policy, monitor = make_monitor(pin="4242", enabled=False)

    notify(monitor, "enable", {"pin": "wrong"})

    assert policy.should_block() is True


def test_disable_with_the_wrong_pin_is_refused():
    policy, monitor = make_monitor(pin="4242")

    notify(monitor, "disable", {"pin": "1111"})

    assert policy.should_block() is True
    assert xbmcaddon.SETTINGS["enabled"] is True


def test_disable_without_a_pin_is_refused_when_one_is_set():
    policy, monitor = make_monitor(pin="4242")

    notify(monitor, "disable", {})

    assert policy.should_block() is True


def test_disable_works_when_no_pin_is_configured():
    policy, monitor = make_monitor(pin="")

    notify(monitor, "disable")

    assert policy.should_block() is False


@pytest.mark.parametrize(
    "method",
    ["Player.OnPlay", "System.OnWake", "Other.something_else", "VideoLibrary.OnUpdate"],
)
def test_unrelated_notifications_are_ignored(method):
    policy, monitor = make_monitor(pin="")

    monitor.onNotification("xbmc", method, "{}")

    assert policy.should_block() is True, "state must be left alone"


@pytest.mark.parametrize("data", ["", "not json", "[1,2,3]", '"text"', None])
def test_malformed_payloads_do_not_crash_the_monitor(data):
    policy, monitor = make_monitor(pin="4242")

    monitor.onNotification("homebridge", "Other.disable", data)

    assert policy.should_block() is True


def test_data_may_arrive_base64_encoded():
    """Older Kodi builds base64 the data payload."""
    import base64

    policy, monitor = make_monitor(pin="4242")
    encoded = base64.b64encode(json.dumps({"pin": "4242"}).encode()).decode()

    monitor.onNotification("homebridge", "Other.disable", encoded)

    assert policy.should_block() is False


def test_decode_handles_a_dict_directly():
    assert decode_notification_data({"pin": "1"}) == {"pin": "1"}


def test_published_state_while_blocking():
    policy, _ = make_monitor(pin="4242")

    state.publish(policy)

    assert xbmcgui.WINDOW_PROPERTIES[state.PROP_ENABLED] == "1"
    assert xbmcgui.WINDOW_PROPERTIES[state.PROP_BLOCKING] == "1"
    assert xbmcgui.WINDOW_PROPERTIES[state.PROP_UNLOCKED] == "0"
    assert xbmcgui.WINDOW_PROPERTIES[state.PROP_SECONDS] == "0"


def test_published_state_after_a_remote_disable():
    policy, monitor = make_monitor(pin="4242")
    notify(monitor, "disable", {"pin": "4242"})

    state.publish(policy)

    assert xbmcgui.WINDOW_PROPERTIES[state.PROP_ENABLED] == "0"
    assert xbmcgui.WINDOW_PROPERTIES[state.PROP_BLOCKING] == "0"


def test_published_state_during_a_pin_unlock():
    """The switch stays on: blocking is still enabled, just not right now."""
    policy, _ = make_monitor(pin="4242", unlock_minutes=30)
    policy.grant()

    state.publish(policy)

    assert xbmcgui.WINDOW_PROPERTIES[state.PROP_ENABLED] == "1"
    assert xbmcgui.WINDOW_PROPERTIES[state.PROP_UNLOCKED] == "1"
    assert xbmcgui.WINDOW_PROPERTIES[state.PROP_BLOCKING] == "0"
    assert int(xbmcgui.WINDOW_PROPERTIES[state.PROP_SECONDS]) > 1700


def test_clear_removes_the_properties():
    policy, _ = make_monitor()
    state.publish(policy)

    state.clear()

    assert xbmcgui.WINDOW_PROPERTIES == {}
