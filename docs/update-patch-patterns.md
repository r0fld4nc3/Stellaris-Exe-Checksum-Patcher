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
When most checks are already patched (adding a patch later), the calls left can't be compared with each
other any more. They are then accepted only if the code after them reads the result, as it does after `strcmp`.

Each check controls something different, so the patches can be picked separately:

| Patch | What it changes | Recognised by strings nearby |
|---|---|---|
| Checksum (required) | Achievements, crash reporter, tutorial | `common/achievements.txt`, `tutorial_step_completed` |
| Warning | Yellow version text in the main menu | `version_text_box`, `MATCHMAKING_SERVER_VERSION` |
| Tooltip | Checksum tooltip on the version text | `ACHIEVEMENT_TOOLTIP_CHECKSUM` |

Each check is given to the patch whose strings are loaded in the same function, closest first. The executable lists
where every function starts and ends, so strings of a neighbouring function are never used. On Windows the tooltip
check sits in a small helper function with no strings, so the patcher also looks at the functions calling it.
Checks that match no patch go to the required Checksum patch, so a check that moved in a game update still gets
patched.

## After a game update: check the new executable

From the `src` folder:

```bash
uv run python -m app.report "/path/to/stellaris.exe"
```

It uses the bundled `patterns-v2.json`. To try changes to another patterns file, pass it as a second argument.

Example output (4.5.4):

```
Target string (Checksum):     4394a9a4797b27029182f9dba4431b4f
Compare function:  0x1420463d0
Sites:             4 (4 unpatched)

 call offset       address  status     patch              matched by                                nearby strings
    0x1ad54e   0x1401ae14e  original   tooltip_patch      caller near 'ACHIEVEMENT_TOOLTIP_CHECKSUM'
    0x1b8af9   0x1401b96f9  original   checksum_patch     near 'common/achievements.txt'            File '%s' does not exist : %s, ...
    0xea7832   0x140ea8432  original   checksum_warning   near 'MATCHMAKING_SERVER_VERSION'         Cygnus v4.5.4, MATCHMAKING_SERVER_VERSION, version_text_box
   0x177cae7   0x14177d6e7  original   checksum_patch     near 'tutorial_step_completed'            invalid, tutorial_step_completed, ...

Checksum          2 site(s)
Warning           1 site(s)
Tooltip           1 site(s)
```

Things to look for:

- **It finds a target string and some sites.** If so, patching works.
- **Every patch has at least one site.** If so, the update needs nothing.
- **`matched by` says `unmatched`**: that check matched none of the patches' strings and went to Checksum.
  Look at its nearby strings and see the next section.
- If you have Ghidra open anyway, the `address` column is what you'd jump to.

### When a patch's strings stop matching

1. In the report, find the site that went `unmatched` and pick one of its nearby strings that names what it is
   (a GUI name, localisation key or file path, not a version number).
2. Add it to that patch's `near_strings` in `patterns-v2.json`, for both `windows` and `linux`.
3. Run the report again with the edited file, then push it. Users get it without an app release.

In a hurry, add a `site_overrides` entry instead (see below), and replace it with a string later.

## patterns-v2.json

Settings the app downloads from GitHub, so they can change without an app release:

| Field | Meaning |
|---|---|
| `target_string` | Regex for the string whose comparisons are patched: the official checksum string in the executable. Default `[0-9a-f]{32}` (an MD5). |
| `replace_call_with` | Hex bytes written over each `CALL strcmp`. Must be exactly 5 bytes. |
| `required` / `enabled` | Whether the patch is forced on / on by default in the UI. |
| `near_strings` | Game strings loaded in the same function as this patch's checks. Used to tell the checks apart. |
| `takes_unmatched_sites` | Also patch checks no other patch matches. Set on the required Checksum patch. |
| `site_overrides` | `{"<build checksum>": ["0x1ad54e"]}`: call offsets (from the report) to use for that exact build. For emergencies, strings are preferred. |

Every patch uses its own `target_string` and `replace_call_with`, so one patch can be changed without touching
the others. Patches with the same `target_string` are found in one scan, and its checks are shared out between
them. A patch with a different `target_string` gets its own scan: if that one fails, the other patches still apply.

A check counts as patched when it holds its own patch's `replace_call_with`. If you change a patch's
`replace_call_with`, executables patched with the old bytes are no longer recognised: restore the original first.
A patch with no `near_strings` and no `site_overrides` applies to every check, like in older patterns files.

Patching never restores original code. To remove a patch, restore the original executable (a backup or verifying
the game files in Steam) and patch again. Adding a patch to an executable that's already patched works.
After writing, the executable is scanned again to confirm every patch is in it.

Add a new version key (next to `latest`) only if a specific game version needs different settings.

## If it stops working

- **"No target string found"**: the game changed how it stores the checksum. Open the exe in Ghidra, look for
  the `checksum_manifest.txt` string, follow it to the checksum code, and see what the official checksum looks like
  now. Update `target_string` if it's just a different format.
- **"More than one possible target string"**: make `target_string` more specific.
- **Sites are missing or skipped**: the code between the string and the `CALL` changed. See `MAX_CALL_DISTANCE`
  in [auto_patch.py](../src/patchers/auto_patch.py), or compare in Ghidra.
- **Background**: https://steamcommunity.com/sharedfiles/filedetails/?id=2460079052
