# Stellaris Checksum Patcher (Enable Achievements)

[![Downloads@latest](https://img.shields.io/github/downloads/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/StellarisChecksumPatcher.exe?style=for-the-badge&logo=square&logoColor=blue&label=Windows)](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases/latest/download/StellarisChecksumPatcher.exe)
[![Downloads@latest](https://img.shields.io/github/downloads/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/StellarisChecksumPatcher-linux?style=for-the-badge&logo=linux&label=Linux)](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases/latest/download/StellarisChecksumPatcher-linux)
[![Release Version Badge](https://img.shields.io/github/v/release/r0fld4nc3/stellaris-exe-checksum-patcher?style=for-the-badge)](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases)

> [!IMPORTANT] Please see [the updated guide and README on the 2.0 branch!](github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/tree/road-to-2.0.0)

# ❗ Note ❗

The cause of the issue where after an update achievements were no longer being triggered has been identified. The issue is not that anything has changed from Paradox's side or that the Patcher needed adjusting to any potential new changes. The issue is with game updates and save games where sometimes saves can lose their trait of being elligible for achievements across patches. I will be working on a "Fix Save Game" patch option as well to include in the Patcher in the future, to fix this issue.

## 📣 Summary

❗ Patching currently only supported on Windows.

❗ Patching testing on MacOS and Linux.

❗ Save fixing not yet done for Windows, MacOS and Linux.

An easy and painless way to patch the game's executable so that mods are compatible with Ironman mode therefore also enabling the pursuit of Achievements with a modded game.

Download the executable by clicking the above **``Badges``** or in [Releases](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases).

## ❗ Disclaimer ❗
* Remember to **not** upload the modified Stellaris executable to download or distribution sites.
* My stance on this further down.
* Use at your own risk. I take no responsibility for your actions or what you choose to do with the modified file.
* The goal of this is to simply offer a faster and more automated way to enable mod compatibility with Ironman and Achievements for a better personal experience.
* Check notes at the end of this file on how to verify authenticity of the tool.

<p align="center">
<img src="https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/blob/main/media/stellaris-checksum-patcher-06.png" width="762">
</p>

## 🟢 Patches
* **Patch Executable**
  * This method will automatically check for a Steam installation and patch the executable.
  * It will create a backup of the original adding a _.orig_ to the end of the file name.
  * If it cannot find the installation, will prompt via dialog for the install folder.
  * Will remember the installation location for next time.

* **Fix Save Achievements**
  * Will ask for the save file to work on
  * Attempts to fix achievements not being present.
  * Sets Ironman flag(s) to "yes".

# 🗒️ Notes
## "Windows protected your PC" Warning
This is a common issue with unsigned or newly signed certificates.
  
There isn't much I can do about it apart from generating a signature and letting it be evaluated over time. I can assure you this is nothing to be concerned of, it is simply Windows notifying that it might not recognise the signature from the common signatures pool.

**This tool is currently only hosted on this GitHub project. I included the official signing timestamp of each file in each release so check against those if you must.**
  
The provided software is completely safe.

# 🔎 My Stance
The sole reason for this patch comes mostly for the fact that we are barred from amazing Quality of Life and Visual mods if we wish to hunt for those Achievements, which can only be obtained by playing Ironman. 

I don't wish to make it so that it becomes easier or _cheesier_ or _cheatier_ to acquire those Achievements as personally that would also completely devalue the effort made. I do support there being no access to the console or any other way to circumvent certain aspects that deter from the challenge, and I understand how difficult or nearly impossible it is to dynamically regulate which mods would be valid for Ironman and which ones would not.

**Therefore, I do not condone and do not support bypassing this restriction by the developers with the aim of installing content that would enable cheating or unfairly facilitate the acquisition of Achievements, nor was this application made with that belief in mind.**

I understand I cannot regulate this either and therefore ask for sensibility and fairness when playing Ironman with the patch in place. These achievements and everything surrounding them were done with great care and passion by fellow people and it is our responsibility to care for and respect their creations which they poured their hearts and hours into.

## Sources
This method was a side project mainly for learning purposes and honing skills. _(Also because I don't have MSWord lol)_

It was based on the original guide here: https://steamcommunity.com/sharedfiles/filedetails/?id=2719382752
