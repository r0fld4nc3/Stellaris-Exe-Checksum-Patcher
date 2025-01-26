from conf_globals import OS, LOG_LEVEL
from logger import create_logger

log = create_logger("Registry Helper", LOG_LEVEL)

if OS.WINDOWS:
    import winreg

    WINREG_KEY_READ = winreg.KEY_READ

    def _connect_to_registry() -> winreg.HKEYType:
        log.debug('Connecting to Local Machine registry.')

        try:
            connection = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        except Exception:
            log.error('Unable to connect to Registry.')
            connection = None

        return connection


    def read_key(key_path, query_value):
        log.debug(f'Reading Registry Key {key_path}')

        reg = _connect_to_registry()
        if not reg:
            return False

        try:
            key = winreg.OpenKey(reg, key_path, 0, WINREG_KEY_READ)

            path_name, regtype = winreg.QueryValueEx(key, query_value)
            log.debug(f'Retrieved {path_name}')

            winreg.CloseKey(key)
        except Exception:
            path_name = None
            log.error(f'Unable to read key.')

        return path_name
