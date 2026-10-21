# Updating patches for a new game version

The patcher finds what to patch automatically, so a new game version usually needs **no changes at all**.
No Ghidra or byte patterns required. The logic lives in [auto_patch.py](../src/patchers/auto_patch.py).

## How it works

The game stores the official checksum as a plain MD5 string (e.g. `32709cf254181b032b1b309a6ea09776`).
Every checksum check loads that string and calls `strcmp`, which returns `0` when the checksums are equal.

The patcher:

1. Finds the official checksum string in the executable
2. Finds every instruction that loads that string
3. Takes the `CALL strcmp` right after each one
4. Replaces each call with `XOR EAX,EAX` + a 3-byte NOP (`31 C0 0F 1F 00`), so `strcmp` always "returns" 0

As a safety check, all of those calls must go to the same function. Anything else is skipped.

## After a game update: check the new executable

From the `src` folder:

```bash
uv run python -m patchers.report "/path/to/stellaris.exe"
```

Example output:

```
Checksum string:   32709cf254181b032b1b309a6ea09776
Compare function:  0x14203f120
Sites:             4 (4 unpatched)

 call offset       address  status     next bytes                           nearby strings
    0x1ad60e   0x1401ae20e  original   85 C0 0F 94 C0 48 83 C4 28 C3 CC CC
    0x1b8bd9   0x1401b97d9  original   8B F0 85 C0 41 0F 94 C6 E8 15 53 3F  common/achievements.txt, ...
    0xea0662   0x140ea1262  original   85 C0 0F 84 67 01 00 00 48 8D 5D 90  Cygnus v4.5.2, ..., version_text_box
   0x1776787   0x141777387  original   8B D8 48 8B CE E8 2A 3E FC FE 8B C8  tutorial_step_completed, ...
```

Things to look for:

- **It finds a checksum string and some sites.** If so, the update needs nothing.
- **Next bytes** usually start with `85 C0` (`TEST EAX,EAX`) or `8B xx` (saving the result), i.e. the code checks the `strcmp` result.
- **Nearby strings** hint at what each site is for (achievements, the version text warning, the tooltip, tutorials).
- If you have Ghidra open anyway, the `address` column is what you'd jump to.

## patterns.json

Settings the app downloads from GitHub, so they can change without an app release:

| Field | Meaning |
|---|---|
| `checksum_string` | Regex for the official checksum string in the executable. Default `[0-9a-f]{32}` (an MD5). |
| `replace_call_with` | Hex bytes written over each `CALL strcmp`. Must be exactly 5 bytes. |
| `required` / `enabled` | Whether the patch is forced on / on by default in the UI. |

Add a new version key (next to `latest`) only if a specific game version needs different settings.

## If it stops working

- **"No checksum string found"**: the game changed how it stores the checksum. Open the exe in Ghidra, look for
  the `checksum_manifest.txt` string, follow it to the checksum code, and see what the official checksum looks like
  now. Update `checksum_string` if it's just a different format.
- **"More than one possible checksum string"**: make `checksum_string` more specific.
- **Sites are missing or skipped**: the code between the string and the `CALL` changed. See `MAX_CALL_DISTANCE`
  in [auto_patch.py](../src/patchers/auto_patch.py), or compare in Ghidra.
- **Background**: https://steamcommunity.com/sharedfiles/filedetails/?id=2460079052
