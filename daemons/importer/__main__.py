import signal
import socketserver
from config import Config
from daemons.abc import JobQueueDaemon
from .importer import ImportExecutor, ImportRequestHandler


def main(server_address, output_dir):
    daemon = JobQueueDaemon(["q_import"])
    daemon.add_executor("q_import", ImportExecutor, output_dir, ("127.0.0.1", 1337))
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
    main(("127.0.0.1", 1338), "./output_dir/")
