import sys
import os
import shutil
import requests
import base64
import pathlib
import zipfile
import tempfile

# 3rd Party
from utils.global_defines import logger

def get_current_dir():
    if getattr(sys, "frozen", False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(__file__)

    return application_path


def repair_save(save_file):
    # .sav
    save_directory = pathlib.Path(save_file).parent
    save_file_name = pathlib.Path(save_file).name
    save_file_times = (os.stat(save_file).st_atime, os.stat(save_file).st_mtime)

    logger.info(f"Save Directory: {save_directory}")
    logger.info(f"Save Name: {save_file_name}")

    # Repair directory
    repair_directory = save_directory / "save_repair"
    pathlib.Path(repair_directory).mkdir(parents=True, exist_ok=True)
    logger.debug(f"Repair Directory: {repair_directory}")

    # Backup directory
    backup_directory = pathlib.Path(get_current_dir()) / "saves_backup" / save_directory.name
    backup_save_file = pathlib.Path(backup_directory) / save_file_name
    pathlib.Path(backup_directory).mkdir(parents=True, exist_ok=True)

    # Create Backup of the save
    try:
        logger.info(f"Backup Directory: {backup_directory}")
        shutil.copy2(save_file, backup_save_file)
        logger.info(f"Backed up {save_file_name} to {backup_save_file}")
    except Exception as e:
        logger.error(e)

    # Try to unzip the save file
    try:
        with zipfile.ZipFile(save_file, 'r') as zip_file:
            zip_file.extractall(repair_directory)
    except Exception as e:
        logger.error(e)

    # Store files and their access times
    files_access_times = {}
    for file in pathlib.Path(repair_directory).iterdir():
        files_access_times[file.name] = (os.stat(file).st_atime, os.stat(file).st_mtime)

    # gamestate
    gamestate_file = pathlib.Path(repair_directory) / "gamestate"

    with open(gamestate_file, 'r') as f:
        file = f.read()

    file_contents = file.splitlines()
    new_file_contents = file_contents.copy()

    # Pull up to date achievements
    achievements = pull_latest_achivements_file()

    if not achievements or achievements == '':
        logger.error("Unable to fix save as achievements could not be retrieved.")
        return False

    achievements_line_start = -1
    achievements_line_end = -1
    existing_achievements = False
    clusters_found = False
    is_proper_file = False

    for i, line in enumerate(file_contents):
        if achievements_line_start == -1 and "achievement={" in line:
            existing_achievements = True
            achievements_line_start = i
            logger.info(f"Achievements line found: {i}")

        # If existing achievements line, the next } will be the closing bracket
        if existing_achievements and achievements_line_end == -1:
            if "}" in line:
                achievements_line_end = i
                logger.info(f"Achievements line close found: {i}")
                break

        # Deal with new contents directly.
        if not existing_achievements and "clusters={" in line:
            clusters_found = True
            new_file_contents.insert(i, achievements)
            break

    # Double check conditions are met to be able to write the proper file
    if existing_achievements or clusters_found:
        is_proper_file = True

    if not is_proper_file:
        logger.error(f"The file {save_file_name} is not a proper file.")
        return False

    # Overwrite achievements line with updated contents
    if existing_achievements:
        offset = achievements_line_end - achievements_line_start
        logger.debug(f"Line Offset: {offset}")
        if offset > 1:
            for i in range(offset+1): # offset +1 to include the ending line
                # Popping achievement line start means that once the line is popped,
                # the remaining lines will fill that spot, therefore the index is the same
                logger.debug(f"Pop {new_file_contents[achievements_line_start]}")
                new_file_contents.pop(achievements_line_start)

            logger.debug(f"Inserting achievements at {new_file_contents[achievements_line_start]}")
            new_file_contents.insert(achievements_line_start, achievements)
        else:
            new_file_contents[achievements_line_start] = achievements

    temp_file = pathlib.Path(tempfile.gettempdir()) / "gamestate"
    with open(temp_file, 'w') as new_file:
        new_file.write('\n'.join(new_file_contents))

    # Replace temp gamestate with the extracted gamestate
    shutil.copy(temp_file, gamestate_file)

    # Rebuild .sav file
    with zipfile.ZipFile(save_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in pathlib.Path(repair_directory).iterdir():
            # Fix files access times to their originals
            fname = file.name
            if fname in files_access_times.keys():
                os.utime(file, files_access_times.get(fname, None))
            with open(file, 'r') as fread:
                zf.writestr(pathlib.Path(file).name, fread.read())

    # Set access times from original
    os.utime(save_file, save_file_times)

    shutil.rmtree(repair_directory)

    logger.info("Finished repairing save.")
    return True

def pull_latest_achivements_file():
    logger.info("Pulling latest Achievements file from GitHub repository.")

    owner = "r0fld4nc3"
    repo_name = "Stellaris-Exe-Checksum-Patcher"
    download_cancelled = False

    repo = f"{owner}/{repo_name}"
    url = f"https://api.github.com/repos/{repo}/contents/StellarisChecksumPatcher/achievements/achievements.txt"
    logger.debug(url)

    try:
        response = requests.get(url, timeout=60)
    except requests.ConnectionError as con_err:
        logger.error(f"Unable to establish connection to update repo.")
        logger.debug_error(con_err)
        return False

    if not response.status_code == 200:
        logger.error("Not a valid repository.")

    achievements_file = pathlib.Path(os.path.dirname(__file__)).parent / "achievements" / "achievements.txt"
    try:
        pulled_release = response.json()["content"]
        achievements = base64.b64decode(pulled_release).decode("utf-8")
        logger.debug(f"Decoded: {achievements}")
        # Update local achievements file
        logger.info("Updating achievements file with repo content.")
        try:
            with open(achievements_file, 'w') as ach_f:
                ach_f.write(achievements)
        except Exception as e:
            logger.error(f"Error writing to achievements file.\nError: {e}")
    except Exception as e:
        logger.info(f"Error in pulling achievements from repo. Falling back to physical file.\nError: {e}")
        logger.debug(response.json())
        # Fallback to physical file
        logger.debug(f"Achievements file: {achievements_file}")

        try:
            with open(achievements_file, 'r') as ach_f:
                achievements = ach_f.read()
        except Exception as e:
            logger.error(f"Error in accessing achievements file.\nError: {e}")
            achievements = ''

    return achievements


