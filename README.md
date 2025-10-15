# Stellaris Checksum Patcher (Enable Achievements)

[![Downloads@latest](https://img.shields.io/github/downloads/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/StellarisChecksumPatcher.exe?style=for-the-badge&logo=square&logoColor=blue&label=Windows)](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases/latest/download/StellarisChecksumPatcher.exe)
[![Downloads@latest](https://img.shields.io/github/downloads/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/StellarisChecksumPatcher-linux?style=for-the-badge&logo=linux&label=Linux)](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases/latest/download/StellarisChecksumPatcher-linux)
[![Release Version Badge](https://img.shields.io/github/v/release/r0fld4nc3/stellaris-exe-checksum-patcher?style=for-the-badge)](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases)

## ❗ Note - I stopped receiving achivements!!11! ❗

If you've stopped receiving achievements on a save where you should or previously have, it is because the save file itself was altered to remove a line that allows that playthrough to be elligible for achievements. I am working on a fix for this as well.

## 📣 Summary

❗ Still working on save fixing.

An easy and painless way to patch the game's executable to enable Achievements being earnable with mods that change the game's Checksum.

## ⤵️ Usage
* Download the executable by clicking the above **``Badges``** or in [Releases](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases).

| Platform                                                                                                                         | Version              |
|----------------------------------------------------------------------------------------------------------------------------------|----------------------|
| [Windows]()   | v2.0.0 (pre-release) |
| [Linux]()   | v2.0.0 (pre-release) |
| macOS                                                                                                                            | Currently none       |

Please refer to the below **Build & Run From Source** section if you don't wish to run the binary file.

## ⚙️ Build & Run From Source
* Go to [Releases](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases) and download the appropriate archive file for your system:

| OS       | Format                                                                                                                            |
|----------|-----------------------------------------------------------------------------------------------------------------------------------|
| Windows  | [.zip](https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/releases/download/v2.0.0/Stellaris-Checksum-Patcher_road-to-2.0.0_01.zip)   |
| Linux    | [.tar.xz](https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/releases/download/v2.0.0/Stellaris-Checksum-Patcher_road-to-2.0.0_01.tar.xz) |
| macOS    |                                                                                                                            |

* Uncompress the archive and inside the extracted folder you will see a build-run script file.

* ### Windows

Requirements: [Python 3.13](https://www.python.org/downloads/release/python-3139/)

  * Uncompress the zip file.

  * #### Method 1 - Non-terminal
    * Double-click `build-run.bat` to launch.
    * It should spawn a terminal window, update the required dependencies and launch.

  * #### Method 2 - Terminal
    * Open `Terminal` or `Console` and `cd` into the directory where `build-run.bat` is.
    * Run `&"build-run.bat` or `build-run.bat`, whichever works.
    * It should update the required dependencies and launch.

* ### Linux
  * Uncompress the archive.

  * #### Method 1 - Non-terminal
    * Right click `build-run.sh` > Properties > Executable as Program (if it isn't already set)
    * Double-click to launch

  * #### Method 2 - Terminal
    * Open a terminal on the folder where there script is located or navigate your terminal to there.
    * Run `chmod +x build-run.sh; ./build-run.sh`

## ❗ Disclaimer ❗
* Remember to **NOT** upload the modified Stellaris executable to download or distribution sites.
* Use at your own risk. By using this software, you agree that I, the developer, take no responsibility for your actions, what you choose to do with the modified file and any and all damages that may present themselves by using this software.
* The goal of this is to simply offer a faster and more automated way to enable mod compatibility with Achievements for a better personal experience.
* Clarification of my stance on this further down.

<p align="center">
<img src="https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/blob/main/media/stellaris-checksum-patcher-06.png" width="762">
</p>

## 🟢 Patches
* **Patch Executable**
  * This method will automatically check for a Steam installation and patch the executable.
  * It will create a backup of the original adding a `.orig` to the end of the file name.
  * If it cannot find the installation, will prompt via dialog for the installation folder.
  * Will remember the installation location for next time.

* **Fix Save Achievements**
  * Will ask for the save file to work on
  * Attempts to fix achievements not being present.
  * Sets Ironman flag(s) to "yes".

# 🗒️ Notes
* **This tool is currently only hosted on this GitHub project. In doubt, please compare your file and version/date to the SHA256 and MD5 table. I will try to keep it as up to date as possible with the current release**

* ### "Windows protected your PC" Warning
  * This is a common issue with unsigned or newly signed certificates. There isn't much I can do about it unless I generate a signature/certificate, pay and upload it to Microsoft. I can assure you this is nothing to be concerned about, it is simply Windows notifying that it might not recognise the signature from the common signatures pool.


# 🔐 SHA256
| File                               | SHA256                                                                                 | MD5                                                    |
|------------------------------------|----------------------------------------------------------------------------------------|--------------------------------------------------------|
| Stellaris-Checksum-Patcher-linux   | <sub><sup>a9f26f9b4e86c3533b83e7e16af48dc79e8eac45a45c5752e9cb0b365a15d6de</sup></sub> | <sub><sup>eca776501d4c0e634f95b438e6e8b8d6</sup></sub> |
| Stellaris-Checksum-Patcher-win.zip | <sub><sup>afbf04f0db8a070fb35653af6e2ffeb3c1609e4dd6fac73be82a644328420073</sup></sub> | <sub><sup>522e021fec263ea048ef9bd1be6d8909</sup></sub> |
| Stellaris-Checksum-Patcher.exe     | <sub><sup>5218e49db31812583386f4c944d7744e799b9344c813670a5d04b4c2166c8d16</sup></sub> | <sub><sup>a3dfaea91f0a4206fd9b5b7978b125f6</sup></sub> |
| Stellaris-Checksum-Patcher.tar.xz  | <sub><sup>1e539c0a132bf9faa58521199b4ca45aedcfb41246ec60dd72a14a74c0995b2c</sup></sub> | <sub><sup>6163a03894cec4165608ed86326445fd</sup></sub> |


# 🔎 My Stance
The sole reason for this patch comes mostly for the fact that we are barred from amazing Quality of Life and Visual mods if we wish to hunt for those Achievements, which can only be obtained by playing Ironman. 

I don't wish to make it so that it becomes easier or _cheesier_ or _cheatier_ to acquire those Achievements as personally that would also completely devalue the effort made. I do support there being no access to the console or any other way to circumvent certain aspects that deter from the challenge, and I understand how difficult or nearly impossible it is to dynamically regulate which mods would be valid for Ironman and which ones would not.

**Therefore, I do not condone and do not support bypassing this restriction by the developers with the aim of installing content that would enable cheating or unfairly facilitate the acquisition of Achievements, nor was this application made with that belief in mind.**

I understand I cannot regulate this either and therefore ask for sensibility and fairness when playing Ironman with the patch in place. These achievements and everything surrounding them were done with great care and passion by fellow people, and it is our responsibility to care for and respect their creations which they poured their hearts and hours into.

## Sources
This method was a side project mainly for learning purposes and honing skills.

This method is based off of these following guides:

- [Enabling Achievements in Stellaris With Mods (All game versions) [SRE] by class101](https://steamcommunity.com/sharedfiles/filedetails/?id=2460079052)

- [How to enable Achievements with ANY mod by Chillsmeit](https://steamcommunity.com/sharedfiles/filedetails/?id=2719382752)
