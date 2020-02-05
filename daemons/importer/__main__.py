import signal
import socketserver
from config import Config
from daemons.abc import JobQueueDaemon
from gdrive_client import GDriveClient
from .importer import ImportExecutor, UploadExecutor, ImportRequestHandler


def main(server_address, output_dir, drive_client, remote_root_id):
    daemon = JobQueueDaemon(["q_import", "q_upload"])
    daemon.active_imports = {}
    daemon.active_transcodes = {}
    daemon.add_executor("q_import", ImportExecutor, output_dir, ("127.0.0.1", 1337), daemon)
    daemon.add_executor("q_upload", UploadExecutor, drive_client, remote_root_id, output_dir, ("127.0.0.1", 1339), daemon)
    daemon.add_server(socketserver.TCPServer(server_address, ImportRequestHandler))
    daemon.start()
    
    try:
        sig = signal.sigwaitinfo({signal.SIGINT}) # TODO handle sigterm
    except KeyboardInterrupt:
        sig = signal.SIGINT
    finally:
        sig = signal.Signals(sig.si_signo)
        print(f"Shutting down after {sig.name}")
        daemon.shutdown()

if __name__ == '__main__':
    Config.update("config.json")
    drive_client = GDriveClient(Config)
    main(("127.0.0.1", 1338), "./output_dir/", drive_client, Config.root_id)
