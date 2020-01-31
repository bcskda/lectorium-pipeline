import socketserver
import threading


class BaseDaemon:
    def __init__(self):
        self.servers = []
        self._threads = []

    def add_server(self, server):
        """Sets server.daemon property to access daemon instance"""
        server.daemon = self
        self.servers.append(server)

    def start(self):
        if not self.servers:
            raise RuntimeError("No servers registered")
        if self._threads:
            raise RuntimeError("Already started")
        
        self._threads = []
        for srv in self.servers:
            srv_thread = threading.Thread(target=srv.serve_forever)
            srv_thread.start()
            self._threads.append(srv_thread)

    def shutdown(self):
        if not self._threads:
            raise RuntimeError("Not started")
        
        for srv in self.servers:
            srv.shutdown()
        for srv_thread in self._threads:
            srv_thread.join()
        self._threads = []
