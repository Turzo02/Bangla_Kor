"""Single-instance mutex."""
import ctypes

from config import SINGLE_INSTANCE_NAME, ERROR_ALREADY_EXISTS
from platform_win.api import kernel32
from state import APP_MUTEX  # will mutate via globals()


def acquire_single_instance():
    """Prevent multiple instances. Returns True if first instance."""
    global APP_MUTEX
    import state

    try:
        mutex = kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_NAME)
        if not mutex:
            return True

        if int(kernel32.GetLastError()) == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(mutex)
            state.APP_MUTEX = None
            return False

        state.APP_MUTEX = mutex
        return True
    except Exception as exc:
        print(f"Single-instance check unavailable: {exc}")
        state.APP_MUTEX = None
        return True


def release_single_instance():
    global APP_MUTEX
    import state

    if state.APP_MUTEX:
        try:
            kernel32.CloseHandle(state.APP_MUTEX)
        except Exception:
            pass
        state.APP_MUTEX = None