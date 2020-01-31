import socketserver
import queue
from threading import Thread


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
            srv_thread = Thread(target=srv.serve_forever)
            srv_thread.start()
            self._threads.append(srv_thread)
    def shutdown(self):
        if not self._threads:
            raise RuntimeError("Not started")
        
        for srv, srv_thread in zip(self.servers, self._threads):
            srv.shutdown()
            srv_thread.join()
            srv.server_close()
        self._threads = []
        print("BaseDaemon shutdown finished")

class JobQueueDaemon(BaseDaemon):
    def __init__(self, executor_cls, *args, **kwargs):
        """Constructs executor instance with (self.job_queue, *args, **kwargs)
        
        executor_cls.shutdown method should block until executor_cls.run finishes
        """
        super(JobQueueDaemon, self).__init__()
        self.job_queue = queue.Queue()
        self.executor = executor_cls(self.job_queue, *args, **kwargs)
        self._executor_thread = None
    
    def shutdown(self):
        super(JobQueueDaemon, self).shutdown()
        self.executor.shutdown()
        self._executor_thread.join()
        self._executor_thread = None
        print("JobQueueDaemon shutdown finished")

    def start(self):
        if self._executor_thread:
            raise RuntimeError("Already started")

        self._executor_thread = Thread(target=self.executor.run)
        self._executor_thread.start()
        super(JobQueueDaemon, self).start()

class BaseQueueExecutor:
    def __init__(self, job_queue: queue.Queue, poll_interval=0.5):
        self._running = False
        self._shutdown_requested = False
        self._poll_interval = poll_interval
        self.job_queue = job_queue

    def handle_job(self, job):
        raise NotImplementedError()

    def run(self):
        self._running = True # thread-safety left
        while not self._shutdown_requested:
            try:
                job = self.job_queue.get(timeout=self._poll_interval)
            except queue.Empty:
                continue
            try:
                self.handle_job(job)
            except Exception as e:
                print(f"[BaseQueueExecutor] Unhandled exception: {e}")
        self._running = False

    def shutdown(self):
        self._shutdown_requested = True
        while self._running:
            time.sleep(self._poll_interval)
        self._shutdown_requested = False
        print("BaseQueueExecutor shutdown finished")
