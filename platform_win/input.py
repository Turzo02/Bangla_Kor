"""Send keys / clipboard — uses PowerShell (kept for compatibility)."""
import subprocess
import time

import pyperclip


def run_powershell_command(command):
    return subprocess.run(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", command],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def send_keys(keys, delay=0.08):
    """Send keystrokes via WScript.Shell SendKeys."""
    safe_keys = str(keys).replace("'", "''")
    command = (
        "$wshell = New-Object -ComObject WScript.Shell; "
        f"$wshell.SendKeys('{safe_keys}');"
    )
    run_powershell_command(command)
    if delay:
        time.sleep(delay)


def select_all_and_copy():
    """Ctrl+A then Ctrl+C, return clipboard text."""
    pyperclip.copy("")
    time.sleep(0.05)

    command = (
        "$wshell = New-Object -ComObject WScript.Shell; "
        "$wshell.SendKeys('^a'); "
        "Start-Sleep -Milliseconds 100; "
        "$wshell.SendKeys('^c');"
    )
    run_powershell_command(command)
    time.sleep(0.18)
    return pyperclip.paste()


def replace_selected_text(converted_text, original_hwnd):
    """Copy converted text and paste into focused window."""
    pyperclip.copy(converted_text)
    time.sleep(0.12)

    if original_hwnd:
        try:
            from platform_win.api import user32
            user32.SetForegroundWindow(original_hwnd)
        except Exception:
            pass
        time.sleep(0.12)

    command = (
        "$wshell = New-Object -ComObject WScript.Shell; "
        "$wshell.SendKeys('^v');"
    )
    result = run_powershell_command(command)
    if result.returncode != 0:
        raise RuntimeError("Paste operation failed.")