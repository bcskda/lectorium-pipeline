import logging
import pyudev
import signal
import socketserver
from daemons.abc import JobQueueDaemon
from .devwatch import DevwatchExecutor, DevwatchRequestHandler, ImportExecutor

def check_match(device):
    try:
        match = all([
            device["DEVTYPE"] == "partition"
            # TODO check properties of Reader(SD1, ..., SDn)
        ])
    except KeyError:
        match = False
    return match

def main(server_address, importer_address):
    # TODO check mount privilege
    daemon = JobQueueDaemon(["q_import"])
    udev_context = pyudev.Context()
    daemon.add_executor(None, DevwatchExecutor, udev_context,
                        daemon, daemon.job_queues["q_import"],
                        udev_filter="block", event_filter=check_match)
    daemon.add_executor("q_import", ImportExecutor, importer_address)
    daemon.add_server(socketserver.TCPServer(server_address, DevwatchRequestHandler))
    daemon.start()
    
    try:
        sig = signal.sigwaitinfo({signal.SIGINT}) # TODO handle sigterm
    except KeyboardInterrupt:
        sig = signal.SIGINT
    finally:
        sig = signal.Signals(sig.si_signo)
        logging.info("Shutting down after {}", sig.name)
        daemon.shutdown()

if __name__ == "__main__":
    logging.getLogger("root").setLevel(logging.INFO)
    server_address = ("127.0.01", 1339)
    importer_address = ("127.0.0.1", 1338)
    main(server_address, importer_address)
