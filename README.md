# Stellaris Checksum Patcher (Enable Achievements w/ Mods!)

[![Latest Release](https://img.shields.io/github/v/release/r0fld4nc3/stellaris-exe-checksum-patcher?style=for-the-badge&label=Latest%20Release)](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases/latest)
[![All-Time Downloads](https://img.shields.io/github/downloads/r0fld4nc3/stellaris-exe-checksum-patcher/total?style=for-the-badge&label=Total%20Downloads)](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases)

If you'd like to support me:

[![Ko-fi](https://img.shields.io/badge/Ko--fi-FF5E5B?logo=ko-fi&logoColor=white)](https://www.ko-fi.com/r0fld4nc3)

An easy and painless way to patch the game's executable to enable Achievements being earnable with mods that change the game's Checksum.

## ⤵️ Usage
* Download the executable by clicking the above **``Badges``** or in [Releases](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases).

| Platform                                                                                                                             | Version              |
|--------------------------------------------------------------------------------------------------------------------------------------|----------------------|
| [Windows](https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/releases/download/v2.1.0/Stellaris-Checksum-Patcher-win.exe)   | v2.1.0               |
| [Linux](https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/releases/download/v2.1.0/Stellaris-Checksum-Patcher-linux)       | v2.1.0               |
| macOS                                                                                                                                | Currently None       |

Please refer to the below **Build & Run From Source** section if you don't wish to run the binary file.

## ⚙️ Compile Source

The following describes the steps needed to compile the source code to a one-file distributable binary/executable. The result should be a single file that is the packaged application into a runnable binary.

> [!NOTE]
> Compiling to a target platform requires the process to be started from that same platform, i.e.: Compiling to Windows must be done in Windows, to Linux in Lunux, etc.

### Requirements:

* [Python 3.13](https://www.python.org/downloads/release/python-3139/) (Can be managed by UV)
* [UV](https://docs.astral.sh/uv/) (Very recommended)

### Pull

#### git clone
For a more in-depth explanation, look into _[How To](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository?platform=linux&tool=webui)_

* In a terminal, navigate to the desired location in the filesystem.
* Run:
```shell
git clone https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher
cd Stellaris-Exe-Checksum-Patcher
```

#### Without git clone
* Go to the [Code Section](https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher) and download the [source code](https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/archive/refs/heads/main.zip) from the target branch.
* Optionally, choose a specific branch first and then download the source code through the green button at the top (`<> Code`).

### Compile

* In the project's main directory.
* Run:
```shell
uv run ./builds/build-nuitka.py
```

## ⚙️ Sync & Run From Source

The following describes the steps needed to run the source code without the need to compile a binary/executable. This is useful for fast development iteration as it offsets the burden to each user.

As a side-effect, each user must meet the configuration requirements.

This will sync the project's requirements, create a virtual environment and run the project via the System/Venv python.

### Requirements: 
* [Python 3.13](https://www.python.org/downloads/release/python-3139/) (Can be managed by UV)
* [UV](https://docs.astral.sh/uv/) (Very recommended)

#### git clone
For a more in-depth explanation, look into _[How To](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository?platform=linux&tool=webui)_

* In a terminal, navigate to the desired location in the filesystem.
* Run:
```shell
git clone https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher
cd Stellaris-Exe-Checksum-Patcher
```

#### Without git clone
* Go to the [Code Section](https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher) and download the [source code](https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher/archive/refs/heads/main.zip) from the target branch.
* Optionally, choose a specific branch first and then download the source code through the green button at the top (`<> Code`).

### Windows

  * Uncompress the zip file.

  * #### Method 1 - Non-terminal
    * Enter `Stellaris-Exe-Checksum-Patcher/scripts` directory.
    * Double-click `dev-run.bat` to launch.
    * It should spawn a terminal window, update the required dependencies and launch.

  * #### Method 2 - Terminal
    * Open a terminal and `cd` into the `Stellaris-Exe-Checksum-Patcher/scripts` directory.
    * Run `&"dev-run.bat"`, `dev-run.bat` or `.\dev-run.bat`, whichever works.
    * It should update the required dependencies and launch.

### Linux
  * Uncompress the archive.

  * #### Method 1 - Non-terminal
    * Enter `Stellaris-Exe-Checksum-Patcher/scripts` directory.
    * Right click `dev-run.sh` > Properties > **Executable as Program** (if it isn't already set).
    * Double-click to launch.

  * #### Method 2 - Terminal
    * Open a terminal and `cd` into the `Stellaris-Exe-Checksum-Patcher/scripts` directory.
    * Run `chmod +x dev-run.sh; ./dev-run.sh`

## ❗ Disclaimer ❗
* Remember to **NOT** upload the modified Stellaris executable to download or distribution sites.
* Use at your own risk. By using this software, you agree that I, the developer, take no responsibility for your actions, what you choose to do with the modified file and any and all damages that may present themselves by using this software.
* The goal of this is to simply offer a faster and more automated way to enable mod compatibility with Achievements for a better personal experience.
* Clarification of my stance on this further down.

<p align="center">
<img src="https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/blob/main/media/stellaris-checksum-patcher-07-01.png" width="762">
</p>

<p align="center">
<img src="https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/blob/main/media/stellaris-checksum-patcher-07-02.png" width="762">
</p>

## 🟢 Patches
* **Patch Executable**
  * This method will automatically check for a Steam installation and patch the executable.
  * If it cannot find the installation, will prompt via dialog for the installation folder.
  * It will create a versioned backup of the current game binary.
  * Applies selected (or default) patches. Select patches from the **Configuration Window**
  * Will remember the installation location for next time.

* **Fix Save**
  * Select desired fixes/changes to apply to the save file.
  * Prompt for a save file to work on.
  * A backup is created in the Application's configuration directory under "save games".
  * Attempts to apply the selected fixes.

# 🗒️ Notes
* **This tool is currently only hosted on this GitHub project. In doubt, please compare your file and version/date to the SHA256 and MD5 table. I will try to keep it as up to date as possible with the current release**

* ### "Windows protected your PC" Warning
  * This is a common issue with unsigned or newly signed certificates. There isn't much I can do about it unless I generate a signature/certificate, pay and upload it to Microsoft. I can assure you this is nothing to be concerned about, it is simply Windows notifying that it might not recognise the signature from the common signatures pool.


# 🔐 SHA256

| File                               | SHA256                                                                                 | MD5                                                    |
|------------------------------------|----------------------------------------------------------------------------------------|--------------------------------------------------------|
| Stellaris-Checksum-Patcher-linux   | <sub><sup>791631b8ad432d69507d66e3f4b237c8ddfdb70e3c3383fc051de74a1b980f04</sup></sub> | <sub><sup>d306274ee77020541227722f0a1a9496</sup></sub> |
| Stellaris-Checksum-Patcher-win.exe | <sub><sup>509ce651e8e34a5efaf1ec1ea29041a2c5fec6602a85ea985eff78944c90ef73</sup></sub> | <sub><sup>7c2d9e0bce51bb78d692047cafe26d24</sup></sub> |


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
