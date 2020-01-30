import os.path
import subprocess
from . import logger


MOUNTPOINT_BASE = "/mnt"

def mount(device, path=None) -> str:
    """Return value: path or generated path"""
    if not path:
        basename = "lectorium-devwatch-{}".format(hash(device))
        path = os.path.join(MOUNTPOINT_BASE, basename)
        try:
            os.mkdir(path)
        except FileExistsError:
            pass
    
    cmdline = ["mount", device.device_node, path]
    logger.debug("mount cmdline: {}".format(cmdline))
    try:
        subprocess.check_call(cmdline)
    except subprocess.CalledProcessError as e:
        logger.exception(e)
        raise RuntimeError("mount(8) failed") from e
    
    return path

def umount(path):
    cmdline = ["umount", path]
    logger.debug("umount cmdline: {}".format(cmdline))
    try:
        subprocess.check_call(cmdline)
    except subprocess.CalledProcessError as e:
        logger.exception(e)
        raise RuntimeError("umount(8) failed") from e
