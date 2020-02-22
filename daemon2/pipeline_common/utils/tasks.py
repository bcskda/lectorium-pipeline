"""Credits: Lectorium team 2018-2019"""

import datetime
import os
import logging
from collections import namedtuple
from typing import List, Callable
from .probe import VideoFile, extract_groups, listdir_videos

ConcatTask = namedtuple("ConcatTask", ["sources", "destination"])


def into_tasks(sd_root, storage_root) -> List[ConcatTask]:
    raw_sources_path = os.path.join(sd_root, "PRIVATE", "AVCHD", "BDMV", "STREAM")
    groups = extract_groups(listdir_videos(raw_sources_path))

    month_names_ru = "января февраля марта апреля мая июня июля августа сентября октября ноября декабря".split()

    concat_tasks = []

    for i, group in enumerate(groups):
        date = group[0].start_date.date()

        destination = os.path.join(
            storage_root,
            f"{date:%Y.%m.%d} - {date.day} {month_names_ru[date.month - 1]}",
            f"source_{group[0].start_date.time():%H_%M_%S}.mp4"
        )
        concat_tasks.append(ConcatTask(group, destination))

        logging.info(f"=== Group for {destination!r} ===")
        logging.info(f"{'Name':10} {VideoFile.TIME_INFO_HEADER}")
        for vid in group:
            logging.info(f"{os.path.basename(vid.path):10} {vid.time_info_str()}")

        if not all(date == vid.start_date.date() for vid in group):
            logging.info(f"Warning: not all videos in group have same record date ({date})")

    return concat_tasks


def execute_tasks(tasks, output_dir, transcode: Callable) -> List[str]:
    """Return value: list of output files"""
    if not os.path.exists(output_dir):
        raise RuntimeError(f"Output directory {output_dir!r} does not exist")

    input("Concatenate? (or KeyboardInterrupt)")

    outputs = []
    for sources, destination in tasks:
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        transcode([vid.path for vid in sources], destination)
        logging.info(f"Finished {destination} ({datetime.datetime.now()})")
        outputs.append(destination)

    logging.info("All done, new files:")
    for destination in outputs:
        logging.info(destination)

    return outputs


def execute_from_args(args, transcode: Callable) -> List[str]:
    concat_tasks = into_tasks(args.input, args.output)
    return execute_tasks(concat_tasks, args.output, transcode)
