# Stellaris Checksum Patcher

An easy and painless way to patch the game's executable so that mods are compatible with Ironman mode and anything that is prevented from a checkusm check.

Download the executable in [Releases](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases).

[![Downloads@latest](https://img.shields.io/github/downloads/r0fld4nc3/stellaris-exe-checksum-patcher/total?style=for-the-badge)](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases/latest/download/StellarisChecksumPatcher.exe)
[![Release Version Badge](https://img.shields.io/github/v/release/r0fld4nc3/stellaris-exe-checksum-patcher?style=for-the-badge)](https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/releases)

<p align="center">
<img src="https://github.com/r0fld4nc3/stellaris-exe-checksum-patcher/blob/main/media/stellaris-checksum-patcher-01.png" width="762">
</p>

## Ways To Patch
- **From Game Installation**
  - This method will automatically check for a Steam installation and patch the executable.
  - It will create a backup of the original adding a _.orig_ to the end of the file name.

- **From Directory**
  - This will first attempt to look in the current directory where the Patcher is located for the game's executable and will patch and move it to the installation folder.
  - If the game's executable isn't in the current directory, it will prompt for the game's install path and acquire the file from there.
  - It will create a backup of the original adding a _.orig_ to the end of the file name.

# Notes
## Windows protected your PC
This is a common issue with unsigned or newly signed certificates.
There isn't much I can do about it apart from generating a signature and letting it be evaluated over time. I can assure you this is nothing to be concerned of, it is simply Windows notifying that it might not recognise the signature from the common signatures pool.
The software provided is completely safe.
