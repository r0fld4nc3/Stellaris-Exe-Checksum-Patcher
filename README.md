# Stellaris Checksum Patcher (Enable Achievements)

[![Downloads@latest](https://img.shields.io/github/downloads/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/StellarisChecksumPatcher.exe?style=for-the-badge&logo=square&logoColor=blue&label=Windows)](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases/latest/download/StellarisChecksumPatcher.exe)
[![Downloads@latest](https://img.shields.io/github/downloads/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/StellarisChecksumPatcher-linux?style=for-the-badge&logo=linux&label=Linux)](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases/latest/download/StellarisChecksumPatcher-linux)
[![Release Version Badge](https://img.shields.io/github/v/release/r0fld4nc3/stellaris-exe-checksum-patcher?style=for-the-badge)](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases)

## ❗ Note - I stopped receiving achivements!!11! ❗

If you've stopped receiving achievements on a save where you should or previously have, it is because the save file itself was altered to remove a line that allows that playthrough to be elligible for achievements. I am working on a fix for this as well.

## 📣 Summary

❗ Still working on save fixing.

An easy and painless way to patch the game's executable so that mods are compatible with Ironman mode therefore also enabling the pursuit of Achievements with a modded game.

## ⤵️ Usage
* Download the executable by clicking the above **``Badges``** or in [Releases](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases).

| Platform                                                                                                                         | Version              |
|----------------------------------------------------------------------------------------------------------------------------------|----------------------|
| [Windows](https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/releases/download/v2.0.0/Stellaris-Checksum-Patcher.exe)   | v2.0.0 (pre-release) |
| [Linux](https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/releases/download/v2.0.0/Stellaris-Checksum-Patcher-linux)   | v2.0.0 (pre-release) |
| macOS                                                                                                                            | Currently none       |

Please refer to the below **Build & Run From Source** section if you don't wish to run the binary file.

## ⚙️ Build & Run From Source
* Go to [Releases](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases) and download the appropriate archive file for your system:

| OS       | Format                                                                                                                            |
|----------|-----------------------------------------------------------------------------------------------------------------------------------|
| Windows  | [.zip](https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/releases/download/v2.0.0/Stellaris-Checksum-Patcher-win.zip)   |
| Linux    | [.tar.xz](https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/releases/download/v2.0.0/Stellaris-Checksum-Patcher.tar.xz) |
| macOS    | .tar.xz                                                                                                                           |

* Uncompress the archive and inside the extracted folder you will see a build-run script file.

* ### build-run on Windows
  * To add.

* ### build-run on Linux
    * #### Method 1 - Non-terminal
      * Right click `build-run.sh` > Properties > Executable as Program (if it isn't already set)
      * Double-click to launch

    * #### Method 2 - Terminal
      * Open a terminal on the folder where there script is located or navigate your terminal to there.
      * Run `chmod +x build-run.sh; ./build-run.sh`

## ❗ Disclaimer ❗
* Remember to **not** upload the modified Stellaris executable to download or distribution sites.
* Use at your own risk. I take no responsibility for your actions or what you choose to do with the modified file.
* The goal of this is to simply offer a faster and more automated way to enable mod compatibility with Ironman and Achievements for a better personal experience.
* My stance on this further down.

<p align="center">
<img src="https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/blob/main/media/stellaris-checksum-patcher-06.png" width="762">
</p>

## 🟢 Patches
* **Patch Executable**
  * This method will automatically check for a Steam installation and patch the executable.
  * It will create a backup of the original adding a _.orig_ to the end of the file name.
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
| Stellaris-Checksum-Patcher-linux   | <sub><sup>69370d9e925e0bd061d18c51cd8d808e6d258fa89752124be5947d09ca560897</sup></sub> | <sub><sup>b80a9490bae81dd4fe9dc06d86b1797c</sup></sub> |
| Stellaris-Checksum-Patcher-win.zip | <sub><sup>2746e2f32bb6ffa7d45679e8bc3249cc244f344b43a215ab2f68d0afef0af178</sup></sub> | <sub><sup>16c50b7161eee99fe6c3e46f600fde4e</sup></sub> |
| Stellaris-Checksum-Patcher.exe     | <sub><sup>5ffc80544361b8aa82634ef1755bc368f879e2617c35bb032ab4d23ee284e4e9</sup></sub> | <sub><sup>8a3bc81b1a9abaf6e4b36ba634ade2bd</sup></sub> |
| Stellaris-Checksum-Patcher.tar.xz  | <sub><sup>5be2e9fb1bef476e75aefecfae069f3808e3d86868d84583ac181c0daff77979</sup></sub> | <sub><sup>f8f78a6fa0b99fb17ae7951d6f95f193</sup></sub> |


# 🔎 My Stance
The sole reason for this patch comes mostly for the fact that we are barred from amazing Quality of Life and Visual mods if we wish to hunt for those Achievements, which can only be obtained by playing Ironman. 

I don't wish to make it so that it becomes easier or _cheesier_ or _cheatier_ to acquire those Achievements as personally that would also completely devalue the effort made. I do support there being no access to the console or any other way to circumvent certain aspects that deter from the challenge, and I understand how difficult or nearly impossible it is to dynamically regulate which mods would be valid for Ironman and which ones would not.

**Therefore, I do not condone and do not support bypassing this restriction by the developers with the aim of installing content that would enable cheating or unfairly facilitate the acquisition of Achievements, nor was this application made with that belief in mind.**

I understand I cannot regulate this either and therefore ask for sensibility and fairness when playing Ironman with the patch in place. These achievements and everything surrounding them were done with great care and passion by fellow people, and it is our responsibility to care for and respect their creations which they poured their hearts and hours into.

## Sources
This method was a side project mainly for learning purposes and honing skills.

It was based on the original guide here: https://steamcommunity.com/sharedfiles/filedetails/?id=2719382752
