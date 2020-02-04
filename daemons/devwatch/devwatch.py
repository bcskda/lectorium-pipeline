import json
import pyudev
import os.path
import socket
from typing import Callable, Dict
import daemons.abc
from .mount import mount, umount
from . import logger


class DevwatchRequestHandler(daemons.abc.DispatchedRequestHandler):
    _mesg_dispatcher = daemons.abc.DispatchedRequestHandler.mesg_dispatcher

    @_mesg_dispatcher.add_handler("import_result")
    def on_import_result(self):
        req = self.request_obj["message"]
        mountpoint = req["path"]
        by_mountpoint = {v: k for k, v in self.server.daemon.active_devices}
        device = by_mountpoint.get(mountpoint)
        if device:
            logger.info(f"import finished: device={device} mountpoint={mountpoint}")
            del self.server.daemon.active_devices[device]
            umount(mountpoint)
        else:
            self.error("Device not active")

class DevwatchExecutor(daemons.abc.BaseLoopExecutor):
    action_dispatcher = daemons.abc.HandlerDispatcher()

    def __init__(self, context: pyudev.Context,
                 daemon, import_queue,
                 udev_filter=None,
                 event_filter: Callable[[pyudev.Device], bool] = None):
        self.monitor = pyudev.Monitor.from_netlink(context)
        if udev_filter:
            self.monitor.filter_by(udev_filter)
        self.event_filter = event_filter
        self.daemon = daemon
        self.daemon.active_devices = {}
        self.import_queue = import_queue
        super(DevwatchExecutor, self).__init__(self.event_poll, BlockingIOError)

    def handle_event(self, event):
        logger.info(f"event: device={event.sys_path} action={event.action}")
        if self.event_filter and self.event_filter(event):
            try:
                handler = self.action_dispatcher.get_handler(event.action)
            except KeyError:
                pass
            else:
                handler(self, event)

    def event_poll(self, timeout):
        event = self.monitor.poll(timeout=timeout)
        if event is None:
            raise BlockingIOError()
        else:
            return event

    @action_dispatcher.add_handler("add")
    def on_add(self, event):
        mountpoint = mount(event)
        if mountpoint:
            content = self._guess_content(mountpoint)
            logger.info(f"device={event.sys_path} mountpoint={mountpoint} content={content}")
            if content:
                self.daemon.active_devices[event.sys_path] = mountpoint
                self.import_queue.put({"path": mountpoint, "content": content})
            else:
                umount(mountpoint)

    @action_dispatcher.add_handler("remove")
    def on_remove(self, event):
        mountpoint = self.daemon.active_devices.get(event.sys_path)
        if mountpoint:
            logger.warning(f"active device removed: device={event.sys_path} mountpoint={mountpoint}")
            umount(mountpoint)
            del self.daemon.active_devices[event.sys_path]

    def _guess_content(self, path: str) -> str or None:
        if os.path.isdir(os.path.join(path, "PRIVATE", "AVCHD", "BDMV", "STREAM")):
            return "video_sony"
        return None

class ImportExecutor(daemons.abc.BaseQueueExecutor):
    def __init__(self, job_queue, importer_address):
        super(ImportExecutor, self).__init__(job_queue)
        self.importer_address = importer_address

    def handle_job(self, job: Dict):
        request = {
            "message_type": "import_request",
            "message": {
                "path": job["path"],
                "content": job["content"]
            }
        }
        with socket.create_connection(self.importer_address) as sock:
            with sock.makefile(mode="w") as sock_w:
                json.dump(request, sock_w)
            sock.shutdown(socket.SHUT_WR)
            with sock.makefile(mode="r") as sock_r:
                try:
                    response = json.load(sock_r)
                    logger.info(f"transcoder response: {response}")
                except Exception as e:
                    logger.exception(e)
