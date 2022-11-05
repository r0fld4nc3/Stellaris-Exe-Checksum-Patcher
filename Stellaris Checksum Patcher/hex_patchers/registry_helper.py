from . import *

logger = Logger(dev=False, exe=True)

WINREG_KEY_READ = winreg.KEY_READ

def __connect_to_registry() -> winreg.HKEYType:
    logger.log_debug('Connecting to Local Machine registry.')

    try:
        connection = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    except Exception:
        logger.log_error('Unable to connect to Registry.')
        connection = None

    return connection

def read_key(key_path, query_value):
    logger.log_debug(f'Reading Registry Key {key_path}')
    
    reg = __connect_to_registry()
    if not reg:
        return False
    
    try:
        key = winreg.OpenKey(reg, key_path, 0, WINREG_KEY_READ)
        
        path_name, regtype = winreg.QueryValueEx(key, query_value)
        logger.log_debug(f'Retrieved {path_name}')
    
        winreg.CloseKey(key)
    except Exception as e:
        path_name = None
        logger.log_error(f'Unable to read key.')
        
    return path_name
