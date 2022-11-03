from . import *

logger = Logger(dev=True)

DEV = True
STELLARIS_STEAM_APP_REGISTRY_PATH = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 281990'
INSTALL_LOCATION_KEY = 'InstallLocation'

def __connect_to_registry() -> winreg.HKEYType:
    logger.log_debug('Connecting to Local Machine registry')
    logger.log_debug(f'Registry Path Key: {STELLARIS_STEAM_APP_REGISTRY_PATH}')
    
    return winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)

def reg_get_stellaris_install_path():
    reg = __connect_to_registry()
    
    key = winreg.OpenKey(reg, STELLARIS_STEAM_APP_REGISTRY_PATH, 0, winreg.KEY_READ)
    path_name, regtype = winreg.QueryValueEx(key, INSTALL_LOCATION_KEY)
    
    logger.log_debug(f'Retrieved {path_name} | {regtype}')
    
    winreg.CloseKey(key)
    
    return path_name