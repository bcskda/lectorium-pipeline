import pyudev
import signal
from daemons.abc import JobQueueDaemon
from .devwatch import DevwatchExecutor

def check_match(device):
    try:
        match = all([
            device["DEVTYPE"] == "partition"
            # TODO check properties of Reader(SD1, ..., SDn)
        ])
    except KeyError:
        match = False
    return match

def main():
    # TODO check mount privilege
    daemon = JobQueueDaemon([])
    udev_context = pyudev.Context()
    daemon.add_executor(None, DevwatchExecutor, udev_context, udev_filter="block", event_filter=check_match)
    daemon.start()
    
    try:
        sig = signal.sigwaitinfo({signal.SIGINT}) # TODO handle sigterm
    except KeyboardInterrupt:
        sig = signal.SIGINT
    finally:
        sig = signal.Signals(sig.si_signo)
        print(f"Shutting down after {sig.name}")
        daemon.shutdown()

if __name__ == "__main__":
    main()
