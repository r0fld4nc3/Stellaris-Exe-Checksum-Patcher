import atexit
import logging
import time
from enum import Enum
from typing import Callable

from PySide6.QtCore import Qt, QThread, Signal, SignalInstance

from .runtime import AppConfig
from .settings import SettingsManager

log = logging.getLogger("Cooldowns")

_LOOP_EVERY_MS: int = 1000
_EXIT_WAIT_MS: int = 1000


class Cooldown(str, Enum):
    REMOTE_MESSAGE = "remote_message"
    PATCH_PATTERNS = "patch_patterns"


class CooldownWatcher(QThread):
    """
    Notifies subscribers when a cooldown starts or ends.

    Started from bootstrap with `start_watching()`, and stopped when Python exits.
    Subscribe with `subscribe()`, which also gives the current state straight away.

    Each cooldown's signal is found with `changed_signal()`.
    """

    remote_message_changed = Signal(bool)
    patch_patterns_changed = Signal(bool)

    def __init__(self, config: AppConfig, settings: SettingsManager):
        super().__init__()
        self.config = config
        self.settings = settings

        log.info("Cooldown Watcher initialised")

    def changed_signal(self, cooldown: Cooldown) -> SignalInstance:
        """Signal to fire when `cooldown` starts or ends. New cooldowns added here."""

        match cooldown:
            case Cooldown.REMOTE_MESSAGE:
                return self.remote_message_changed
            case Cooldown.PATCH_PATTERNS:
                return self.patch_patterns_changed
            case _:
                log.error(f"No signal for cooldown: {cooldown}")
                raise ValueError(f"No signal for cooldown: {cooldown}")

    def is_ready(self, cooldown: Cooldown) -> bool:
        """Whether `cooldown` has ended."""
        seconds_since_check = int(time.time()) - self._last_checked(cooldown)
        ready = seconds_since_check >= self.config.update_check_cooldown
        log.debug(f"Seconds since {cooldown} check: {seconds_since_check}; Ready: {ready}")
        return ready

    def start_watching(self):
        """
        Start the checks, and stop them when Python exits.
        Called on bootstrap.
        """

        atexit.register(self.stop_watching)
        self.start()  # By nature will also call `run()`
        log.info(f"Cooldown Watcher started")

    def stop_watching(self):
        self.requestInterruption()
        # Loop checks every _LOOP_EVERY_MS, short wait is enough
        self.wait(_EXIT_WAIT_MS)

    def subscribe(self, cooldown: Cooldown, callback: Callable[[bool], None]):
        """
        Call `callback(ready)` with current state (now), then whenever `cooldown` starts or ends.
        Later calls run on the main thread, supports updating widgets.
        """
        log.info(f"Subscribe Cooldown '{cooldown.value}' <- '{callback.__name__}'")
        self.changed_signal(cooldown).connect(callback, Qt.QueuedConnection)
        callback(self.is_ready(cooldown.value))

    def run(self):
        """
        Runs on this thread until asked to stop. Started by `start_watching()`.
        Emits a cooldown's signal whenever it starts or ends.
        """
        # Empty so the first pass emits every cooldown
        last_ready: dict[Cooldown, bool] = {}

        while not self.isInterruptionRequested():
            for cooldown in Cooldown:
                ready = self.is_ready(cooldown)
                last_ready_for_cooldown = last_ready.get(cooldown)

                if last_ready_for_cooldown != ready:
                    if ready and last_ready_for_cooldown is False:
                        log.info(f"Cooldown ended: {cooldown.value}")

                    self.changed_signal(cooldown).emit(ready)
                    last_ready[cooldown] = ready

            # Short sleeps so a stop request is noticed quickly
            QThread.msleep(_LOOP_EVERY_MS)

    def _last_checked(self, cooldown: Cooldown) -> int:
        """When `cooldown` last started. Add new cooldowns here."""
        app_settings = self.settings.app_settings

        match cooldown:
            case Cooldown.REMOTE_MESSAGE:
                return app_settings.remote_message_update_last_checked
            case Cooldown.PATCH_PATTERNS:
                return app_settings.patch_patterns_update_last_checked
            case _:
                raise ValueError(f"No timestamp for cooldown: {cooldown}")
