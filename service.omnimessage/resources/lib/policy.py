"""Decision logic for Omni Message.

Deliberately free of any ``xbmc*`` imports so it can be unit tested off-device.
Every "should this play?" question is answered here; the Kodi glue in
``blocker.py`` and ``service.py`` only feeds it events.
"""

import hmac
import threading
import time

# ``unlock_minutes == 0`` means "let this one item through, then lock again".
ONE_SHOT = 0

# How long a one-shot unlock stays open. Kodi fires several callbacks for a
# single item (onPlayBackStarted, then onAVStarted) and a plugin:// path can
# resolve to a different URL on the way in, so an allowance that is consumed by
# the first check would block the very item it just unlocked. A short window
# covers the replay instead.
ONE_SHOT_SECONDS = 60


class Policy:
    """Tracks whether playback is currently allowed.

    The instance is shared between Kodi's player callback thread and the
    service loop, so all mutable state sits behind a lock.
    """

    def __init__(self, settings, clock=time.monotonic):
        self._settings = settings
        self._clock = clock
        self._lock = threading.RLock()
        self._unlock_until = 0.0
        self._handling = False

    def update_settings(self, settings):
        with self._lock:
            self._settings = settings

    @property
    def settings(self):
        with self._lock:
            return self._settings

    def should_block(self):
        """True when the item that just started playing must be stopped."""
        with self._lock:
            if not self._settings.enabled:
                return False
            return self._clock() >= self._unlock_until

    def grant(self, minutes=None):
        """Allow playback for ``minutes``, or just the blocked item when 0."""
        with self._lock:
            if minutes is None:
                minutes = self._settings.unlock_minutes
            window = ONE_SHOT_SECONDS if minutes <= ONE_SHOT else minutes * 60
            self._unlock_until = self._clock() + window

    def revoke(self):
        with self._lock:
            self._unlock_until = 0.0

    def unlocked_seconds_left(self):
        with self._lock:
            return max(0.0, self._unlock_until - self._clock())

    def has_pin(self):
        with self._lock:
            return bool(self._settings.pin)

    def check_pin(self, entered):
        """Constant-time PIN comparison. No configured PIN never matches."""
        with self._lock:
            configured = self._settings.pin
        if not configured or not entered:
            return False
        return hmac.compare_digest(str(entered), str(configured))

    def begin_handling(self):
        """Claim the right to show the block dialog.

        Returns False when a block is already being handled, which stops the
        stop -> dialog -> replay cycle from stacking dialogs on itself.
        """
        with self._lock:
            if self._handling:
                return False
            self._handling = True
            return True

    def end_handling(self):
        with self._lock:
            self._handling = False
