import os


def guess_content(path: str) -> str or None:
    print(f'Guessing for {path}')
    if os.path.isdir(os.path.join(path, "PRIVATE", "AVCHD", "BDMV", "STREAM")):
        return "video_sony"
    return None
