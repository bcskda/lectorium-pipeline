import argparse
import logging
import os
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

def parse_args():
    parser = argparse.ArgumentParser(description="Watch block devices to search and import sources")
    parser.add_argument("--importer", required=True, help="Importer daemon address")
    parser.add_argument("--bind", required=False, default="127.0.0.1:1339", help="Bind address")
    parser.add_argument("--logfile", required=False, help="Path to log file (default - stderr)")
    return parser.parse_args()

def to_addr(url):
    host, port = tuple(url.split(":"))
    return host, int(port)

def main(args):
    bind_addr = to_addr(args.bind)
    importer_addr = to_addr(args.importer)
    # TODO check mount privilege
    
    daemon = JobQueueDaemon(["q_import"])
    udev_context = pyudev.Context()
    daemon.add_executor(None, DevwatchExecutor, udev_context,
                        daemon, daemon.job_queues["q_import"],
                        udev_filter="block", event_filter=check_match)
    daemon.add_executor("q_import", ImportExecutor, importer_addr)
    daemon.add_server(socketserver.TCPServer(bind_addr, DevwatchRequestHandler))
    
    daemon.start()
    logging.info("Started")
    try:
        sig = signal.sigwaitinfo({signal.SIGINT}) # TODO handle sigterm
    except KeyboardInterrupt:
        sig = signal.SIGINT
    finally:
        sig = signal.Signals(sig.si_signo)
        logging.info("Shutting down after %s", sig.name)
        daemon.shutdown()

if __name__ == "__main__":
    args  = parse_args()
    logfile = args.logfile or os.getenv("DEVWATCH_LOGFILE")
    if logfile:
        logging.basicConfig(filename=logfile)
    logging.basicConfig(level=logging.INFO)
    main(args)
