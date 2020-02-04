import hashlib
import os.path
import subprocess
from . import logger


MOUNTPOINT_BASE = "/mnt"
MOUNTPOINT_DIRNAME_FMT = "lectorium-devwatch-mountpoint_{}"

def mount(device, path=None) -> str:
    """Return value: path, generated path, or None if error"""
    if not path:
        dirname = hashlib.md5(device.sys_path.encode()).hexdigest()
        basename = MOUNTPOINT_DIRNAME_FMT.format(dirname)
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
        return None
    else:
        return path

def umount(path):
    cmdline = ["umount", path]
    logger.debug("umount cmdline: {}".format(cmdline))
    try:
        subprocess.check_call(cmdline)
    except subprocess.CalledProcessError as e:
        logger.exception(e)
        raise RuntimeError("umount(8) failed") from e
