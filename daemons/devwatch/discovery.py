import pyudev
from typing import Callable
from . import logger


def discovery_loop(check_match: Callable[[pyudev.Device], bool], on_match: Callable[[pyudev.Device], None]):
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by("block")
    for device in filter(check_match, iter(monitor.poll, None)):
        logger.info("Discovered: %s %s", device.action, device)
        on_match(device)
