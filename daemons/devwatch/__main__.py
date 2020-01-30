from . import logger
from .discovery import discovery_loop, test_directory
from .mount import mount, umount

def check_match(device):
    try:
        match = all([
            device["DEVTYPE"] == "partition"
            # TODO check properties of Reader(SD1, ..., SDn)
        ])
    except KeyError:
        match = False
    return match

def on_match(device):
    try:
        mount_path = mount(device)
        logger.info("mounted {} at {}".format(device, mount_path))
    except Exception as e:
        logger.error("mount() failed for {}".format(device))
        return
    
    content = None
    try:
        content = test_directory(mount_path)
        logger.info("{} content is {}".format(device, content))
        if content:
            # TODO send import task
    except Exception as e:
        logger.exception(e)
    finally:
        if content is None:
            umount(mount_path)
            logger.info("unmounted {}".format(device))

def main():
    # TODO check mount privilege
    try:
        discovery_loop(check_match, on_match)
    except KeyboardInterrupt:
        return 1

if __name__ == "__main__":
    main()
