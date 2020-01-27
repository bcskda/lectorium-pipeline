"""Credits: Lectorium team 2018-2019"""

import datetime
import os
from collections import namedtuple
from typing import List, Callable
from concat_ng.probe import VideoFile, extract_groups, listdir_videos


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

        print(f"=== Group for {destination!r} ===")
        print(f"{'Name':10} {VideoFile.TIME_INFO_HEADER}")
        for vid in group:
            print(f"{os.path.basename(vid.path):10} {vid.time_info_str()}")

        if not all(date == vid.start_date.date() for vid in group):
            print(f"Warning: not all videos in group have same record date ({date})")
    
    return concat_tasks

def execute_from(args, transcode: Callable) -> List[str]:
    """Return value: list of output files"""
    if not os.path.exists(args.output):
        raise RuntimeError(f"Output directory {args.output!r} does not exist")

    concat_tasks = into_tasks(args.input, args.output)

    input("Concatenate? (or KeyboardInterrupt)")
    
    outputs = []
    for sources, destination in concat_tasks:
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        transcode([vid.path for vid in sources], destination)
        print(f"Finished {destination} ({datetime.datetime.now()})")
        outputs.append(destination)

    print("All done, new files:")
    for destination in outputs:
        print(destination)

    return outputs
