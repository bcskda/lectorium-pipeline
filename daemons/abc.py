import functools
import io
import json
import queue
import socketserver
import time
from threading import Thread
from typing import Callable, List


class BaseDaemon:
    def __init__(self):
        self.servers = []
        self._threads = []
        self._started = False

    def add_server(self, server):
        """Sets server.daemon property to access daemon instance"""
        server.daemon = self
        self.servers.append(server)

    def start(self):
        if self._started:
            raise RuntimeError("Already started")
        
        self._threads = []
        for srv in self.servers:
            srv_thread = Thread(target=srv.serve_forever)
            srv_thread.start()
            self._threads.append(srv_thread)
        self._started = True

    def shutdown(self):
        if not self._started:
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
        """if executor_cls is not a BaseQueueExecutor, queue_key is ignored"""
        if issubclass(executor_cls, BaseQueueExecutor):
            args = (self.job_queues[queue_key], *args)
        executor = executor_cls(*args, **kwargs)
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


class BaseLoopExecutor:
    DEFAULT_TIMEOUT = 0.5
    
    def __init__(self, event_poll: Callable, etimeout_cls=Exception, poll_interval=DEFAULT_TIMEOUT):
        self.event_poll = event_poll
        self.etimeout_cls = etimeout_cls
        self._running = False
        self._shutdown_requested = False
        self._poll_interval = poll_interval

    def handle_event(self, event):
        raise NotImplementedError()

    def run(self):
        self._running = True # thread-safety left
        while not self._shutdown_requested:
            # TODO after shutdown request, poll until etimeout (= empty event queue)
            try:
                event = self.event_poll(timeout=self._poll_interval)
            except self.etimeout_cls:
                continue
            except Exception as e:
                print(f"[BaseLoopExecutor] Unhandled exception at event_poll: {e}")
            else:
                try:
                    self.handle_event(event)
                except Exception as e:
                    print(f"[BaseLoopExecutor] Unhandled exception at handle_event: {e}")
        self._running = False

    def shutdown(self):
        self._shutdown_requested = True
        while self._running:
            time.sleep(self._poll_interval)
        self._shutdown_requested = False
        print("BaseLoopExecutor shutdown finished")

class BaseQueueExecutor(BaseLoopExecutor):
    def __init__(self, job_queue: queue.Queue, poll_interval=BaseLoopExecutor.DEFAULT_TIMEOUT):
        self.job_queue = job_queue
        super(BaseQueueExecutor, self).__init__(self.job_queue.get, queue.Empty, poll_interval)

    def handle_event(self, event):
        self.handle_job(event)

    def handle_job(self, job):
        raise NotImplementedError()

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
        >>> @dispatcher.add_handler("create")
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

class DispatchedRequestHandler(JsonRequestHandler):
    """Unifies message_type-based dispatch and error handling.
    Defines additional property self.mesg_dispatcher: HandlerDispatcher.
    Defines additional methods error() and select_handler().
    A concrete handler should define decorated per-message-type handler
    methods."""
    mesg_dispatcher = HandlerDispatcher()

    def error(self, desc):
        self.response_obj["error"] = 1
        self.response_obj["error_desc"] = desc

    def handle(self):
        handler_method = self.select_handler()
        if handler_method:
            try:
                handler_method(self)
                self.response_obj["error"] = 0
            except Exception as e:
                print(f"Unhandled exception in handler {handler_method}: {type(e)}: {e}")
                self.error("Unhandled exception")

    def select_handler(self):
        if self.request_obj is None:
            self.error("Invalid JSON")
        else:
            try:
                mesg_type = self.request_obj["message_type"]
                return self.mesg_type_dispatcher.get_handler(mesg_type)
            except KeyError:
                self.error("Invalid message type")
