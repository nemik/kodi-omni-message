"""Decision logic tests. No Kodi involved, not even the stubs."""

import pytest

from resources.lib.policy import ONE_SHOT_SECONDS, Policy
from resources.lib.settings import Settings


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


def make_policy(clock, **overrides):
    return Policy(Settings(**overrides), clock=clock)


def test_blocks_by_default(clock):
    assert make_policy(clock).should_block() is True


def test_disabled_addon_never_blocks(clock):
    assert make_policy(clock, enabled=False).should_block() is False


def test_timed_unlock_expires(clock):
    policy = make_policy(clock, pin="1234", unlock_minutes=30)
    policy.grant()

    assert policy.should_block() is False
    clock.advance(29 * 60)
    assert policy.should_block() is False
    clock.advance(2 * 60)
    assert policy.should_block() is True


def test_one_shot_unlock_survives_repeated_callbacks(clock):
    """Kodi fires onPlayBackStarted and onAVStarted for the same item."""
    policy = make_policy(clock, pin="1234", unlock_minutes=0)
    policy.grant()

    assert policy.should_block() is False
    assert policy.should_block() is False


def test_one_shot_unlock_closes_again_shortly(clock):
    policy = make_policy(clock, pin="1234", unlock_minutes=0)
    policy.grant()

    clock.advance(ONE_SHOT_SECONDS + 1)
    assert policy.should_block() is True


def test_revoke_clears_an_active_unlock(clock):
    policy = make_policy(clock, pin="1234", unlock_minutes=30)
    policy.grant()
    policy.revoke()

    assert policy.should_block() is True


def test_unlocked_seconds_left(clock):
    policy = make_policy(clock, pin="1234", unlock_minutes=10)
    policy.grant()
    clock.advance(60)

    assert policy.unlocked_seconds_left() == pytest.approx(540)


def test_correct_pin(clock):
    assert make_policy(clock, pin="4242").check_pin("4242") is True


@pytest.mark.parametrize("entered", ["4243", "424", "42422", "", None])
def test_wrong_pin(clock, entered):
    assert make_policy(clock, pin="4242").check_pin(entered) is False


@pytest.mark.parametrize("entered", ["", "0000", None])
def test_unset_pin_never_matches(clock, entered):
    policy = make_policy(clock, pin="")

    assert policy.has_pin() is False
    assert policy.check_pin(entered) is False


def test_settings_update_takes_effect(clock):
    policy = make_policy(clock)
    assert policy.should_block() is True

    policy.update_settings(Settings(enabled=False))
    assert policy.should_block() is False


def test_handling_guard_is_exclusive(clock):
    policy = make_policy(clock)

    assert policy.begin_handling() is True
    assert policy.begin_handling() is False, "a second dialog must not stack"

    policy.end_handling()
    assert policy.begin_handling() is True
