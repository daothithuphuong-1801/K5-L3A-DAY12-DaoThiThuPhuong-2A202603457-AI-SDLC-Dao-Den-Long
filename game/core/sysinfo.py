"""Process memory / start time helpers (psutil when available, OS fallbacks otherwise)."""
import os
import sys
import time

_IMPORT_TIME = time.time()


def rss_mb():
    """Current resident set size of this process in MB."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:  # noqa: BLE001
        pass
    try:  # Linux
        with open("/proc/self/statm") as f:
            return int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / (1024 * 1024)
    except Exception:  # noqa: BLE001
        pass
    try:  # macOS/BSD: peak RSS is the best we have without psutil
        import resource
        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return r / (1024 * 1024) if sys.platform == "darwin" else r / 1024
    except Exception:  # noqa: BLE001
        return None


def process_start_time():
    """Wall-clock time the process started (epoch seconds)."""
    try:
        import psutil
        return psutil.Process(os.getpid()).create_time()
    except Exception:  # noqa: BLE001
        return _IMPORT_TIME
