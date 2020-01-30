from .discovery import discovery_loop


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
    pass

def main():
    discovery_loop(check_match, on_match)

if __name__ == "__main__":
    main()
