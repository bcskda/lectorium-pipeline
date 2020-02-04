import functools
from typing import List


protocols = dict()

def register_proto(title):
    @functools.wraps(register_proto)
    def wrapper(func):
        if title in protocols:
            raise KeyError(f"Protocol exists: {title}")
        protocols[title] = func
        return func
    
    return wrapper

@register_proto("concat")
def proto_concat(urls: List[str]) -> str:
    for url in urls:
        if "|" in url:
            raise RuntimeError(f"Bad symbols (pipe) in url {url!r}, i'm afraid to pass them to ffmpeg")
    return "concat:{}".format("|".join(urls))

def apply_protocol(proto, source):
    return protocols[proto](source)
