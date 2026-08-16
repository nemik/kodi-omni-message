"""The block -> message -> PIN -> replay flow, end to end against the stubs."""

import xbmcgui
import service
from resources.lib.blocker import OmniPlayer
from resources.lib.policy import Policy
from resources.lib.settings import Settings


def blocked_player(**overrides):
    """A player that has just intercepted an item, ready for handle_block."""
    policy = Policy(Settings(**overrides))
    player = OmniPlayer(policy)
    player.playing_file = "/media/movie.mkv"
    player.onPlayBackStarted()
    player.blocked.clear()
    return policy, player


def dialog_calls(kind):
    return [call for call in xbmcgui.CALLS if call[0] == kind]


def test_message_is_shown_without_a_pin():
    policy, player = blocked_player(heading="Nope", message="Ask a parent")

    service.handle_block(policy, player)

    assert dialog_calls("ok") == [("ok", "Nope", "Ask a parent")]
    assert player.played == []
    assert policy.should_block() is True


def test_notification_mode_shows_a_toast_instead():
    policy, player = blocked_player(display_mode="notification", message="Ask a parent")

    service.handle_block(policy, player)

    assert dialog_calls("ok") == []
    notification = dialog_calls("notification")[0]
    assert notification[2] == "Ask a parent"
    assert notification[4] == 5000


def test_correct_pin_unlocks_and_replays():
    policy, player = blocked_player(pin="4242", unlock_minutes=30)
    xbmcgui.YESNO_ANSWERS.append(True)
    xbmcgui.INPUT_ANSWERS.append("4242")

    service.handle_block(policy, player)

    assert player.played == ["/media/movie.mkv"]
    assert policy.should_block() is False


def test_wrong_pin_keeps_blocking():
    policy, player = blocked_player(pin="4242", unlock_minutes=30)
    xbmcgui.YESNO_ANSWERS.append(True)
    xbmcgui.INPUT_ANSWERS.append("1111")

    service.handle_block(policy, player)

    assert player.played == []
    assert policy.should_block() is True
    assert dialog_calls("notification")[0][3] == xbmcgui.NOTIFICATION_ERROR


def test_cancelled_pin_prompt_keeps_blocking():
    policy, player = blocked_player(pin="4242", unlock_minutes=30)
    xbmcgui.YESNO_ANSWERS.append(True)
    xbmcgui.INPUT_ANSWERS.append("")

    service.handle_block(policy, player)

    assert player.played == []
    assert policy.should_block() is True


def test_dismissing_the_dialog_keeps_blocking():
    policy, player = blocked_player(pin="4242", unlock_minutes=30)
    xbmcgui.YESNO_ANSWERS.append(False)

    service.handle_block(policy, player)

    assert dialog_calls("input") == []
    assert player.played == []
    assert policy.should_block() is True


def test_pin_entry_is_hidden_and_numeric():
    policy, player = blocked_player(pin="4242")
    xbmcgui.YESNO_ANSWERS.append(True)
    xbmcgui.INPUT_ANSWERS.append("4242")

    service.handle_block(policy, player)

    _, _, input_type, option = dialog_calls("input")[0]
    assert input_type == xbmcgui.INPUT_NUMERIC
    assert option == xbmcgui.ALPHANUM_HIDE_INPUT


def test_replayed_item_is_not_blocked_again():
    """The full cycle: block, unlock, replay, and Kodi's callbacks fire again."""
    policy, player = blocked_player(pin="4242", unlock_minutes=0)
    xbmcgui.YESNO_ANSWERS.append(True)
    xbmcgui.INPUT_ANSWERS.append("4242")

    service.handle_block(policy, player)
    player.onPlayBackStarted()
    player.onAVStarted()

    assert player.stop_calls == 1, "only the original interception stopped playback"
    assert not player.blocked.is_set()


def test_a_second_block_while_the_dialog_is_open_is_ignored():
    policy, player = blocked_player()
    policy.begin_handling()

    service.handle_block(policy, player)

    assert dialog_calls("ok") == []


def test_handling_guard_is_released_after_each_block():
    policy, player = blocked_player()

    service.handle_block(policy, player)
    service.handle_block(policy, player)

    assert len(dialog_calls("ok")) == 2
