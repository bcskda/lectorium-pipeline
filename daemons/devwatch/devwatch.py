import pyudev
import os.path
from typing import Callable
import daemons.abc
from .mount import mount, umount
from . import logger

class DevwatchExecutor(daemons.abc.BaseLoopExecutor):
    action_dispatcher = daemons.abc.HandlerDispatcher()

    def __init__(self, context: pyudev.Context, udev_filter=None,
                 event_filter: Callable[[pyudev.Device], bool] = None):
        self.monitor = pyudev.Monitor.from_netlink(context)
        if udev_filter:
            self.monitor.filter_by(udev_filter)
        self.event_filter = event_filter
        self.active_devices = {}
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
                self.active_devices[event.sys_path] = mountpoint
            else:
                umount(mountpoint)

    @action_dispatcher.add_handler("remove")
    def on_remove(self, event):
        mountpoint = self.active_devices.get(event.sys_path)
        if mountpoint:
            logger.warning(f"active device removed: device={event.sys_path} mountpoint={mountpoint}")
            umount(mountpoint)
            del self.active_devices[event.sys_path]

    def _guess_content(self, path: str) -> str or None:
        if os.path.isdir(os.path.join(path, "PRIVATE", "AVCHD", "BDMV", "STREAM")):
            return "video_sony"
        return None
