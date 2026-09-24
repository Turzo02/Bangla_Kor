"""Shared runtime state — queues, locks, globals."""
import queue
import threading

busy_lock = threading.Lock()
status_queue = queue.Queue()
ui_queue = queue.Queue()
stop_event = threading.Event()

root = None
LOCAL_MODEL = None
SRC_VOCAB = None
TGT_VOCAB = None
MODEL_CFG = None
MODEL_READY = False
TRAY = None
APP_MUTEX = None


def set_status(message, duration_ms=2500, anchor=None, kind="working"):
    """Push a status update onto the queue. Consumed by StatusToast."""
    status_queue.put((message, duration_ms, anchor, kind))