"""Player interception, driven through the Kodi stubs."""

import xbmc
import xbmcaddon
from resources.lib import settings as settings_module
from resources.lib.blocker import OmniMonitor, OmniPlayer
from resources.lib.policy import Policy
from resources.lib.settings import Settings


def make_player(**overrides):
    policy = Policy(Settings(**overrides))
    return policy, OmniPlayer(policy)


def test_playback_is_stopped_and_flagged():
    policy, player = make_player()
    player.playing_file = "/media/movie.mkv"

    player.onPlayBackStarted()

    assert player.stop_calls == 1
    assert player.blocked.is_set()
    assert player.take_blocked_path() == "/media/movie.mkv"


def test_path_is_consumed_once():
    policy, player = make_player()
    player.playing_file = "/media/movie.mkv"
    player.onPlayBackStarted()

    assert player.take_blocked_path() == "/media/movie.mkv"
    assert player.take_blocked_path() is None


def test_unlocked_playback_is_left_alone():
    policy, player = make_player(pin="1234", unlock_minutes=30)
    policy.grant()
    player.playing_file = "/media/movie.mkv"

    player.onPlayBackStarted()

    assert player.stop_calls == 0
    assert not player.blocked.is_set()


def test_disabled_addon_leaves_playback_alone():
    policy, player = make_player(enabled=False)
    player.playing_file = "/media/movie.mkv"

    player.onPlayBackStarted()

    assert player.stop_calls == 0
    assert not player.blocked.is_set()


def test_av_started_is_a_safety_net():
    policy, player = make_player()
    player.playing_file = "plugin://plugin.video.example/play/1"

    player.onAVStarted()

    assert player.stop_calls == 1
    assert player.take_blocked_path() == "plugin://plugin.video.example/play/1"


def test_one_shot_unlock_survives_both_start_callbacks():
    """Kodi fires onPlayBackStarted and onAVStarted for one replayed item."""
    policy, player = make_player(pin="1234", unlock_minutes=0)
    policy.grant()
    player.playing_file = "/media/movie.mkv"

    player.onPlayBackStarted()
    player.onAVStarted()

    assert player.stop_calls == 0
    assert not player.blocked.is_set()


def test_falls_back_to_the_info_label_when_no_file_is_reported():
    policy, player = make_player()
    player.playing_file = ""
    xbmc.INFO_LABELS["Player.FilenameAndPath"] = "pvr://channels/tv/1.pvr"

    player.onPlayBackStarted()

    assert player.take_blocked_path() == "pvr://channels/tv/1.pvr"


def test_monitor_reloads_settings():
    policy = Policy(Settings(message="old"))
    monitor = OmniMonitor(policy)
    xbmcaddon.SETTINGS["message"] = "new"

    monitor.onSettingsChanged()

    assert policy.settings.message == "new"


def test_disabling_via_settings_clears_an_active_unlock():
    policy = Policy(Settings(pin="1234", unlock_minutes=30))
    monitor = OmniMonitor(policy)
    policy.grant()
    xbmcaddon.SETTINGS["enabled"] = False

    monitor.onSettingsChanged()
    xbmcaddon.SETTINGS["enabled"] = True
    monitor.onSettingsChanged()

    assert policy.should_block() is True


def test_settings_load_reads_every_field():
    xbmcaddon.SETTINGS.update(
        {"message": "Ask a parent", "pin": "9999", "unlock_minutes": 45}
    )

    current = settings_module.load()

    assert current.message == "Ask a parent"
    assert current.pin == "9999"
    assert current.unlock_minutes == 45
    assert current.enabled is True
