"""Credits: Lectorium team 2018-2019"""


import os
import logging
import subprocess
import datetime
import json
from collections import namedtuple
from typing import List


class VideoFile(namedtuple("VideoFile", "path start duration modification_time".split())):
    @staticmethod
    def from_path(path):
        format_info: dict = get_video_format_info(path)

        if not all(key in format_info for key in ["start_time", "duration", "format_name"]):
            raise RuntimeError(f"failed to get video metadata of {path!r}")

        if format_info["format_name"] != "mpegts":
            raise RuntimeError(f"unexpected format {format_info['format_name']!r} of {path!r}")

        return VideoFile(
            path=path,
            start=float(format_info["start_time"]),
            duration=float(format_info["duration"]),
            modification_time=datetime.datetime.fromtimestamp(os.stat(path).st_mtime)
        )

    @property
    def end(self) -> float:
        return self.start + self.duration

    @property
    def start_date(self) -> datetime.datetime:
        return (self.modification_time - datetime.timedelta(seconds=self.duration))
    
    @property
    def end_date(self) -> datetime.datetime:
        return self.modification_time

    def is_prev_to(self, next_, epsilon=1):
        return next_.start - epsilon <= self.end <= next_.start + epsilon

    TIME_INFO_HEADER = f"[{'Local start':>11} - {'Local end':>11}) {'Duration':>11}   [{'Start':>8} - {'End':>8})"
    def time_info_str(self):
        return f"[{self.start:11.2f} - {self.end:11.2f}) {self.duration:11.2f}   [{self.start_date.time():%H:%M:%S} - {self.end_date.time():%H:%M:%S})"


def get_video_format_info(path) -> dict:
    """
        Probably avaliable and interesting keys:
            "format_name", "start_time", "duration"
    """
    ffprobe_cmd = [
        "ffprobe",
        "-hide_banner", "-loglevel", "fatal",
        "-print_format", "json",
        "-show_format",
        "-i", path,
    ]
    video_info = json.loads(subprocess.check_output(ffprobe_cmd))
    return video_info["format"]


def listdir_videos(path) -> List[VideoFile]:
    names = sorted(filter(
        lambda name: name.endswith(".MTS"),
        os.listdir(path)
    ))
    return [
        VideoFile.from_path(os.path.join(path, name))
        for name in names
    ]


def extract_groups(videos: List[VideoFile]) -> List[List[VideoFile]]:
    groups = []
    for vid in videos:
        if groups and groups[-1][-1].is_prev_to(vid):
            groups[-1].append(vid)
        else:
            groups.append([vid])

    for group in groups:
        first = group[0]
        if first.start >= 0.5:
            logging.info(f"Warning: first group element ({first.path!r}) has large start ({first.start:.2f}), maybe change grouping strategy?")

    return groups
