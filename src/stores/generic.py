"""
Generic store: the game didn't come from a supported store, or is started by another app.

The user picks the game executable themselves, and the game is launched with the Generic runner set in General Utilities (Wine, Heroic, Lutris, Bottles...), with the arguments the user typed there.

Each runner receives different arguments, the Patcher simply passes them along.
"""

# built-ins
import logging
import shlex
from pathlib import Path
from typing import Optional

from core import services
from core.paths import FILE_EXTENSION, os_darwin, os_windows

from .base import StoreHelperBase

log = logging.getLogger("Generic Runner")

# Filled in each runner argument
BINARY_PLACEHOLDER = "{binary}"  # The game executable, full path
FOLDER_PLACEHOLDER = "{folder}"  # The folder the game executable is in

# Arguments used when the user typed none. Only the game executable
DEFAULT_RUNNER_ARGS = BINARY_PLACEHOLDER

# Quote characters a Windows argument may be wrapped in
QUOTE_CHARACTERS = "\"'"


class GenericHelper(StoreHelperBase):
    def get_game_install_path(self, game_name: str) -> Optional[Path]:
        # No store to ask. User picks the executable themselves
        log.info(f"Generic store: no automatic search for {game_name}.")
        return None

    def launch_game(self, game_name: str, binary_path: Optional[Path]) -> None:
        if not binary_path or not binary_path.exists():
            log.error(f"No {game_name} executable to launch: '{binary_path}'")
            return

        app_settings = services().settings.app_settings
        if not app_settings.generic_runner_path:
            log.warning(
                f"No Generic runner set, so {game_name} can't be launched from here. "
                "Set one in the options, under General Utilities > Launchers, or start the game from your launcher."
            )
            return

        runner_path = Path(app_settings.generic_runner_path)
        if not runner_path.exists():
            log.error(f"Generic runner not found: {runner_path}")
            return

        try:
            command = build_runner_command(runner_path, app_settings.generic_runner_args, binary_path)
        except ValueError as e:
            log.error(f"Unable to read the Generic runner arguments '{app_settings.generic_runner_args}': {e}")
            return

        log.info(f"Launching {game_name} with the Generic runner: {command}")

        try:
            self.run_detached(command, cwd=binary_path.parent)
        except Exception as e:
            log.error(f"Error launching game with the Generic runner: {e}")

    def validate_game_files(self, game_name: str, binary_path: Optional[Path]) -> bool:
        log.warning(
            f"The Generic store can't validate {game_name}'s files. Use your launcher's own verify or repair option."
        )
        return False


def build_runner_command(runner_path: Path, runner_args: str, binary_path: Path) -> list[str]:
    """
    The Generic runner and its arguments as a list, to run without a shell.

    `runner_args` is split into arguments first, then `{binary}` and `{folder}` are filled in each one, so paths with spaces stay a single argument.

    Empty `runner_args` means `{binary}`.

    Raises ValueError when `runner_args` has an unclosed quote.
    """
    arguments_text = runner_args.strip()
    if not arguments_text:
        arguments_text = DEFAULT_RUNNER_ARGS

    command = _runner_start_command(runner_path)
    for argument in _split_arguments(arguments_text):
        argument = argument.replace(BINARY_PLACEHOLDER, str(binary_path))
        argument = argument.replace(FOLDER_PLACEHOLDER, str(binary_path.parent))
        command.append(argument)

    return command


def _runner_start_command(runner_path: Path) -> list[str]:
    """
    What starts the runner, before its arguments.
    macOS .app is a folder, so it's opened with `open`, which passes the arguments to the app after `--args`.
    """
    if os_darwin() and runner_path.suffix.lower() == FILE_EXTENSION.APP:
        return ["open", "-a", str(runner_path), "--args"]

    return [str(runner_path)]


def _split_arguments(arguments_text: str) -> list[str]:
    """Split typed arguments like a shell would, without running one. Quotes group words with spaces."""
    if not os_windows():
        return shlex.split(arguments_text)

    # Windows paths use backslashes, which POSIX splitting reads as escapes.
    # Split without it, then remove the quotes it keeps around quoted arguments.
    arguments = []
    for argument in shlex.split(arguments_text, posix=False):
        arguments.append(_strip_quotes(argument))

    return arguments


def _strip_quotes(argument: str) -> str:
    """`argument` without one pair of matching quotes around it."""
    # Too short to have an opening and closing quote
    if len(argument) < 2:
        return argument

    first_char = argument[0]
    last_char = argument[-1]

    if first_char not in QUOTE_CHARACTERS:
        return argument

    # Opened with one kind of quote, only same kind can close it.
    if last_char != first_char:
        return argument

    return argument[1:-1]
