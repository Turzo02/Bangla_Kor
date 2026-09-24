"""Windows startup registry helpers."""
import os
import sys
import winreg

from config import STARTUP_REG_PATH, STARTUP_VALUE_NAME


def get_startup_command():
    """Command Windows should run at user logon."""
    if getattr(sys, "frozen", False):
        return f'"{os.path.abspath(sys.executable)}" --startup'
    return f'"{sys.executable}" "{os.path.abspath(__file__)}" --startup'


def is_startup_enabled():
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, STARTUP_REG_PATH, 0, winreg.KEY_READ,
        ) as key:
            value, _ = winreg.QueryValueEx(key, STARTUP_VALUE_NAME)
            return bool(value)
    except (FileNotFoundError, OSError, PermissionError):
        return False


def set_startup_enabled(enabled):
    try:
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, STARTUP_REG_PATH, 0, winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(
                    key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ,
                    get_startup_command(),
                )
            else:
                try:
                    winreg.DeleteValue(key, STARTUP_VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except (OSError, PermissionError) as exc:
        print(f"Startup setting error: {exc}")
        return False