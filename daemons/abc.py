import functools
import io
import json
import queue
import socketserver
import time
from threading import Thread
from typing import List


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
    def __init__(self, queues: List[str]):
        """Constructs executor instance with (self.job_queue, *args, **kwargs)
        
        executor_cls.shutdown method should block until executor_cls.run finishes
        """
        super(JobQueueDaemon, self).__init__()
        self.job_queues = {key: queue.Queue() for key in queues}
        self.executors = []
        self._executor_threads = []

    def add_executor(self, queue_key: str, executor_cls, *args, **kwargs):
        executor = executor_cls(self.job_queues[queue_key], *args, **kwargs)
        self.executors.append(executor)

    def shutdown(self):
        super(JobQueueDaemon, self).shutdown()
        for executor in self.executors:
            executor.shutdown()
        for thread in self._executor_threads:
            thread.join()
        self._executor_threads = []
        print("JobQueueDaemon shutdown finished")

    def start(self):
        if self._executor_threads:
            raise RuntimeError("Already started")

        for executor in self.executors:
            thread = Thread(target=executor.run)
            self._executor_threads.append(thread)
            thread.start()
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
            # TODO process remaining queue
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

class JsonRequestHandler(socketserver.StreamRequestHandler):
    """RequestHandler helper for json-based services.
    A concrete handler should define handle() method. Defines additional
    properties: self.request_obj and self.response_obj to use inside handle().
    self.request_obj will be None in case request was not valid JSON."""

    def setup(self):
        super(JsonRequestHandler, self).setup()
        self.response_obj = {}
        try:
            self.request_obj = json.load(self.rfile) # Client should send SHUT_WR
        except json.JSONDecodeError:
            self.request_obj = None

    def finish(self):
        json.dump(self.response_obj, io.TextIOWrapper(self.wfile))
        super(JsonRequestHandler, self).finish()

class HandlerDispatcher:
    """RequestHandler helper to dispatch requests."""
    def __init__(self):
        self._handlers = {}

    def add_handler(self, key):
        """
        Example:
        >>> dispatcher = HandlerDispatcher
        >>> dispatcher.add_handler("create")
        ... def on_create():
        ...     pass
        """
        if key in self._handlers:
            raise KeyError(f"Handler exists: f{key}")

        def wrapper(func):
            self._handlers[key] = func
            return func
        return wrapper
    
    def get_handler(self, key):
        return self._handlers[key]
