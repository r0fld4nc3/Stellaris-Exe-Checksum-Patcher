# Stellaris Checksum Patcher

An easy and painless way to patch the game's executable so that mods are compatible with Ironman mode and anything that is prevented from a checkusm check.

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
