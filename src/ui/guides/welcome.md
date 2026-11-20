# Welcome to Checksum Patcher!

This quick guide aims to help you get started with the basic main features and functionalities.

You can open it again any time from the options (the **cogwheel** at the top right), under **General Utilities → Show Welcome Dialog**.

Before that, I would like to thank you for choosing to use this project. It is something I invest quite a bit of time in and I consider it one of my *babies*. 

Thank you for supporting and contributing with issues and suggestions, I am always eager to hear what can be improved and to fix what may be broken so that we all share in this *bounty*.

# Basic Overview

For basic usage, the Patcher provides a quick one-click solution to patch your game and start playing immediately.

Let's get started.

## The Information Screen

An information panel displays textual feedback as the Patcher operates. While primarily visual, it provides valuable information about progress, errors and warnings. Pay attention to these messages, especially when reporting issues.

While patching, a progress bar below it shows which step the Patcher is on, and whether it finished successfully.

## Main Action Buttons

Below the information screen are two main buttons:

- **Fix Save** asks you to pick a save, shows what it contains and lets you choose fixes, such as restoring achievement eligibility and converting saves to and from Ironman mode.
- **The Patch button**, with the achievement icon. Once the application has initialised successfully, just click this button to patch your game so achievements are earnable with mods.

At the top right, the **cogwheel** opens the options window and the **?** button opens quick tips and answers to common problems.

## Patching

Patching requires the application to know where the game's executable is, and it attempts to determine this automatically once the patching process starts.

This, however, *can* fail, and in such cases it should prompt you to point to the file path manually.

To choose the executable yourself anyway, for example when the Patcher found the wrong copy of the game, hold **Shift** while clicking the patch button.

To start the patch process, click the patch button indicated by the greyed-out image of an achievement.

Patching requires some base information to identify the correct sites to patch. The Patcher finds the game's checksum checks by itself from the game executable, and tells them apart by the surrounding game text found around each one. This should help make it more robust to game updates.

These rules are found in a patterns file that comes bundled with the application, however, the default behaviour is to always check online and update this local file with one from the remote repository. In case something needs to change, the patterns can be updated without requiring an update to the Patcher application itself.

Once patching is complete, the button turns into a **Launch** button, so **you can launch the game directly from the Patcher.** The button becomes coloured once patching finishes successfully.

*Launching from the Patcher is optional. You can always start the game from Steam, GOG Galaxy or your usual launcher.*

Patching an already patched executable should be safe, as the Patcher should recognise it is already patched and leave it alone.

**NOTE:** If patching ever fails after a game update, please check GitHub for any existing discussions about the current status before opening a new issue. A fix may already be on its way, and it can take some time depending on (my) availability.

## The Options Window

The **cogwheel** at the top right of the main application screen opens the options window. It has two tabs: **General Utilities** and **Game Utilities**.

Changes are applied as you make them. Press **OK** to keep them, or **Cancel** to undo them.

## General Utilities

This tab gathers tools for the Patcher itself, so you don't need to dig through folders by hand: **Update Patterns** to download the latest patterns file, **Show App Config Folder** to open the Patcher's own folder, and **Manage Save Backups**.

**Show Welcome Dialog** opens this guide again, and **Show Information Message** shows the latest news about the Patcher, which also opens by itself at startup when there's something new.

It also has a few settings: how many backups of the game executable to keep (**Maximum Backups**), **Force Local Patterns** to skip downloading the patterns file, and including pre-releases when checking for updates.

Under **Launchers**, you can point the Patcher to your Steam and GOG Galaxy folders (found automatically when left empty), and set up a **Generic Runner** with its arguments to launch games set to Generic.

## Game Utilities

Everything that applies to a specific game lives here, and acts on the game selected at the top of the tab.

Under **Patch Configuration** you can choose which game to patch, which version of the patch configuration to use and, on Linux and macOS, whether you're patching the native game or the Windows version running through **Proton**.

Below that, you can pick the patches to apply, each with a short description:

- **Checksum** is always applied. It lets you earn achievements with mods and stops the crash reporter from flagging the game as modified.
- **Warning** hides the yellow version text shown when the game is modified.
- **Tooltip** shows the normal checksum tooltip instead of the modified-checksum one.

All three are ticked by default. The defaults are all you need, so you technically don't *need* to change anything here, but I would rather give you options than restrict them.

To remove patches, restore the original executable (from a backup or with **Validate Integrity of Game Files** if available) and patch again.

This tab also has buttons to **Show Game Folder** and **Show Save Games Folder**, to **Validate Integrity of Game Files** through your game's store, and to **Delete Backups** of the game executable made when patching.

The save games folder you pick is remembered. Hold **Shift** while clicking **Show Save Games Folder** to choose a different one yourself, or click the **X** next to it to forget it so it's looked for again.

You can also choose where your game comes from: **Steam**, **GOG** or **Generic** (anywhere else, or started with another app). This doesn't change how the game is patched, only where the Patcher looks for it and how it launches and validates it.

# General Tips

## Handling Game Updates

A game update replaces the game executable, so you will need to patch again afterwards. Usually that's just one click on the Patch button.

If you believe you should be receiving achievements or notice that patching did not work correctly, go to the **Game Utilities** tab and click **Validate Integrity of Game Files**.

On **Steam**, this starts Steam's verification, which replaces the executable with a fresh copy. On **GOG**, it opens the game in GOG Galaxy, where you click **Verify / Repair**. For **Generic** games, use your launcher's own verify or repair option. Once finished, apply the patches again, and you should be good to go.

## Restoring Achievements

Patching the executable does **not** necessarily make an existing save eligible to receive achievements. These are two separate systems.

To restore the ability to gain achievements on an existing save game, use the **Fix Save** button next to the Patch button.

This prompts you to select a save game, then reads it and shows what it found: whether it's Ironman, whether it's flagged as cheated, and whether its achievements list is complete. Values that a fix can change are highlighted.

Tick the fixes you want and click **Apply Fixes**. **Update Achievements** is ticked for you when the list needs updating. The other fixes are always your choice. The save is only changed, and backed up first, when a fix actually changes something.

If all goes well, the save will have achievements enabled again, and loading it in-game should restore the ability to receive them.

## Save Backups

When fixing a save, a backup is created in the application's configuration directory.

It would be good practice to delete old and unused save backups from time to time. To do so, click **Manage Save Backups** in the **General Utilities** tab. It lists every backup by playthrough and lets you choose which ones to keep and which to delete.

# Closing Remarks

Well, that should cover most of it for now. I hope this was informative without being too technical or tiring to read.

Once again, thank you for choosing this project and I hope it works well for you and makes you happier to play a wonderful game!

For quick answers to common problems, press the **?** button at the top right of the main window.

In case you are faced with any issues, don't hesitate to open an Issue on GitHub, but before you press "Create", please search for existing issues or fixes that may have already been addressed in the past!

Happy Achievement Hunting!

\- r0fld4nc3
