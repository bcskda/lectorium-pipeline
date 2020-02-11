import argparse
import logging
import os
import signal
import socketserver
from config import Config
from daemons.abc import JobQueueDaemon
from .transcoder import TranscodeExecutor, TranscodeRequestHandler, ResultReporter


def parse_args():
    parser = argparse.ArgumentParser(description="Transcode worker")
    parser.add_argument("--importer", required=True, help="Importer daemon address")
    parser.add_argument("--bind", required=False, default="127.0.0.1:1337", help="Bind address")
    parser.add_argument("--config", required=False, default="config.json", help="Path to configuration")
    parser.add_argument("--logfile", required=False, help="Path to log file (default - stderr)")
    return parser.parse_args()

def to_addr(url):
    host, port = tuple(url.split(":"))
    return host, int(port)

def main(args):
    bind_addr = to_addr(args.bind)
    importer_addr = to_addr(args.importer)
    
    daemon = JobQueueDaemon(["q_transcode_accept", "q_transcode_finished"])
    report_queue = daemon.job_queues["q_transcode_finished"]
    daemon.add_executor("q_transcode_accept", TranscodeExecutor, report_queue)
    daemon.add_executor("q_transcode_finished", ResultReporter, importer_addr)
    daemon.add_server(socketserver.TCPServer(bind_addr, TranscodeRequestHandler))
    
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

if __name__ == '__main__':
    args  = parse_args()
    logfile = args.logfile or os.getenv("TRANSCODER_LOGFILE")
    if logfile:
        logging.basicConfig(filename=logfile)
    logging.basicConfig(level=logging.INFO)
    Config.update(args.config)
    main(args)
