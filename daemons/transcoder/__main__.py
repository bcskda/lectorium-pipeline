import signal
import socketserver
from config import Config
from daemons.abc import JobQueueDaemon
from .transcoder import TranscodeExecutor, TranscodeRequestHandler


def main(server_address):
    daemon = JobQueueDaemon(TranscodeExecutor)
    daemon.add_server(socketserver.TCPServer(server_address, TranscodeRequestHandler))
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
    main(('127.0.0.1', 1337))
