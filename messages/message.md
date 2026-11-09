# Welcome to the Patcher v3!

Thanks for sticking around! v3 marks yet another milestone in updates and functionality the Patcher has received to date. It's now more organised and with more functionality exposed, as well as much less error prone.

It comes with the flagship feature of a complete rewrite of how patching works, which hopefully should rely less on manually acquired patterns and instead relying on automatically determining what it needs based off of an initial analysis of the binary file.

## What's new

- **Patching should keep up with updates.** The Patcher now finds what it needs inside the binary by itself. Game updates should no longer break it, or leave you waiting for a fix.
- **GOG support.** Can now find and launch the executable through GOG Galaxy on Windows and macOS.
- **Launch it your way.** The first time you patch, you'll be asked where your game comes from: **Steam**, **GOG** or **Generic**. Generic covers everything else, including apps like Heroic, Lutris or Bottles, which you can set up to launch the game from the Patcher.
- **One simple patch.** The old separate patches are now a single one that keeps achievements on, tidies away the yellow version text and keeps the crash reporter quiet.
- **Patch from any OS.** The Patcher works out whether your game is the Windows or Linux version, so you can even patch it from a different system. macOS application support has been increased, though patching the macOS binary is still not reliable.
- **Easier cleanup.** Clear out old game backups with **Delete Backups**, and old save backups with **Manage Save Backups**. These were generated files from the given operations, available if something were to go wrong.

## Better all round

- A progress bar shows what the Patcher is doing while it works.
- The options window is tidier, with **General Utilities** for the Patcher itself and **Game Utilities** for the respective game. **Cancel** to undoes all the changes.
- **Fix Save** is more reliable, and a new **Quick Tips & FAQs** window (the **?** button) answers the most common questions.
- Plenty of fixes under the hood, so things should feel smoother and crash less.

## Good to know

- After a game update, patch again. For extra reliability, verify/validate game files and patch. It is also recommended to check your save status for achievements, so running the **Fix Save** again on your active save game can restore propertires removed by the game update.
- Launching from the Patcher is optional. You can always start the game from Steam, GOG Galaxy or your preferred launcher.
- You can see this message again any time from **Show Information Message**, in the options under **General Utilities**.

If something doesn't work as expected, please let me know on GitHub.
Happy Hunting!
