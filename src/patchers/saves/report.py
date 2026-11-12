"""
Report command: shows what a Stellaris save contains and which fixes would change it, without changing anything.

Run from the `src` folder:

    uv run python -m patchers.saves path/to/save.sav

Uses the achievements list bundled with the app, so it works offline and without starting the app.
"""

import sys
from pathlib import Path

from patchers.saves import open_save
from patchers.saves.stellaris import (
    ACHIEVEMENTS_DISTRIBUTED_FILE,
    STELLARIS,
    parse_stellaris_save,
)


def report(path: Path) -> int:
    save = open_save(path)
    parsed = parse_stellaris_save(save, latest=ACHIEVEMENTS_DISTRIBUTED_FILE.read_text(encoding="utf-8"))

    print(f"File:  {path}")
    print()
    print("Findings")
    for finding in parsed.findings:
        print(f"  {finding.label:15} {finding.value:25} {finding.status.value}")
        if finding.detail:
            print(f"  {'':15} {finding.detail}")

    print()
    print("Fixes")
    for fix in STELLARIS.fixes:
        needed = "needed" if fix.is_needed(parsed) else "-"
        print(f"  {fix.label:28} {needed}")

    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m patchers.saves <save file>")
        sys.exit(2)
    sys.exit(report(Path(sys.argv[1])))
