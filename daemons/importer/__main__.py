import argparse
import logging
import os
import signal
import socketserver
from config import Config
from daemons.abc import JobQueueDaemon
from gdrive_client import GDriveClient
from .importer import ImportExecutor, UploadExecutor, ImportRequestHandler


def parse_args():
    parser = argparse.ArgumentParser(description="Search directories for sources, distribute preprocessing, upload result")
    parser.add_argument("--output-dir", required=True, help="Path to output directory")
    parser.add_argument("--transcoder", required=True, help="Transcoder daemon address")
    parser.add_argument("--devwatch", required=True, help="Devwatch daemon address")
    parser.add_argument("--bind", required=False, default="127.0.0.1:1338", help="Bind address")
    parser.add_argument("--config", required=False, default="config.json", help="Path to configuration")
    parser.add_argument("--gdrive-root", required=False, default="root", help="Root directory for uploads")
    parser.add_argument("--logfile", required=False, help="Path to log file (default - stderr)")
    return parser.parse_args()

def to_addr(url):
    host, port = tuple(url.split(":"))
    return host, int(port)

def main(args, gdrive_client):
    bind_addr = to_addr(args.bind)
    transcoder_addr = to_addr(args.transcoder)
    devwatch_addr = to_addr(args.devwatch)
    
    daemon = JobQueueDaemon(["q_import", "q_upload"])
    daemon.active_imports = {}
    daemon.active_transcodes = {}
    daemon.add_executor("q_import", ImportExecutor, args.output_dir,
                        transcoder_addr, daemon)
    daemon.add_executor("q_upload", UploadExecutor, gdrive_client,
                        args.gdrive_root, args.output_dir, devwatch_addr,
                        daemon)
    daemon.add_server(socketserver.TCPServer(bind_addr, ImportRequestHandler))
    
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
    logfile = args.logfile or os.getenv("IMPORTER_LOGFILE")
    if logfile:
        logging.basicConfig(filename=logfile)
    logging.basicConfig(level=logging.INFO)
    Config.update(args.config)
    main(args, GDriveClient(Config))
