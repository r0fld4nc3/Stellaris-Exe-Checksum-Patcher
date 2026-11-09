# Patching

## Patching failed after a game update

The Patcher finds the game's checksum checks by itself, so after most updates you only need to press **Patch** again.

If it still fails, get a clean copy of the game: open the options with the **cogwheel**, go to **Game Utilities** and click **Validate Integrity of Game Files**. On Steam this repairs the game by itself; on GOG it opens the game in GOG Galaxy, where you click **Verify / Repair**. Once the repair has finished, patch again.

If that doesn't help, the update may have changed something the Patcher doesn't recognise yet. Check GitHub for an existing Issue, or open a new one and include the text from the information screen.

## Is my game already patched?

Just press **Patch**. If the game is already patched, the Patcher says so and leaves the file alone, so patching twice is safe.

The patch stays in place until the game is updated or its files are verified or repaired (by Steam, GOG Galaxy or your launcher). After that, patch again.

## The Patcher can't find my game

If the game isn't found automatically, you'll be asked to select its executable (for example **stellaris.exe** on Windows or **stellaris** on Linux). The Patcher remembers it for next time.

## "Unsupported executable format" or "No patches available"

The Patcher can patch the Windows and Linux versions of the game. Make sure you selected the game's executable, not a shortcut or launcher.

Patching the macOS version of the game isn't supported yet. The macOS app can still patch the Windows or Linux version.

## Playing through Proton

If you run the Windows version of the game on Linux or macOS, select **Proton** next to the game in **Game Utilities** before patching. Otherwise keep **Native**.

# Achievements

## Still no achievements after patching

Patching the game and fixing a save are two separate steps. An existing save also has to allow achievements: use **Fix Save** next to the **Patch** button and pick your save.

Remember that the game only awards achievements in Ironman games.

# Backups

## Where do backups go?

Before patching, the Patcher keeps a copy of the game executable next to it, ending in **.orig**. **Delete Backups** in **Game Utilities** removes them.

Saves fixed with **Fix Save** are backed up too. Clean those up with **Manage Save Backups** in **General Utilities**.

# Still stuck?

Search the Issues on GitHub first, as your problem may already be solved. If not, open a new Issue and include the text from the information screen.
