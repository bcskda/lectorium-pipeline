"""Credits: Lectorium team 2018-2019"""

import datetime
import os
import logging
from collections import namedtuple
from typing import List, Dict, Callable
from concat_ng.probe import VideoFile, extract_groups, listdir_videos


ConcatTask = namedtuple("ConcatTask", ["sources", "destination"])

# TODO by-date task indices
g_task_index = 0

def into_tasks(sd_root, storage_root) -> List[ConcatTask]:
    raw_sources_path = os.path.join(sd_root, "PRIVATE", "AVCHD", "BDMV", "STREAM")
    groups = extract_groups(listdir_videos(raw_sources_path))
    
    month_names_ru = "января февраля марта апреля мая июня июля августа сентября октября ноября декабря".split()
    dow_names_ru = "понедельник вторник среда четверг пятница суббота воскресенье".split()
    
    concat_tasks = []
    
    for idx, group in enumerate(groups):
        date = group[0].start_date.date()

        global g_task_index
        mon = month_names_ru[date.month - 1]
        dow = dow_names_ru[date.weekday()]  # weekday 0~6
        destination = os.path.join(
            storage_root,
            f"{date:%Y.%m.%d} - {date.day} {mon} - {dow}",
            f"#{g_task_index:02}-{group[0].start_date.time():%H_%M_%S}",
            f"source"
        )
        g_task_index += 1
        concat_tasks.append(ConcatTask(group, destination))

        logging.info(f"=== Group #{idx} for {destination!r} ===")
        logging.info(f"{'Name':10} {VideoFile.TIME_INFO_HEADER}")
        for vid in group:
            logging.info(f"{os.path.basename(vid.path):10} {vid.time_info_str()}")

        if not all(date == vid.start_date.date() for vid in group):
            logging.info(f"Warning: not all videos in group have same record date ({date})")
    
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
        exitcode, sinks = transcode([[vid.path for vid in sources]], destination)
        logging.info(f"Finished {destination} ({datetime.datetime.now()})")
        outputs.extend(sinks)

    logging.info("All done, new files:")
    for sinks in outputs:
        logging.info(sinks)

    return outputs

def execute_from_v2(args, transcode: Callable) -> Dict[str, List[str]]:
    """
    Return value: 'directory' -> ['children']
    Also selects groups to process by index
    """
    if not os.path.exists(args.output):
        raise RuntimeError(f"Output directory {args.output!r} does not exist")

    concat_tasks = into_tasks(args.input, args.output)

    selected_tasks = input("Select groups (empty = all, KeyboardInterrupt = none): ")
    selected_tasks = list(map(int, selected_tasks.split()))
    if len(selected_tasks) == 0:
        selected_tasks = list(range(len(concat_tasks)))
    
    outputs = {}
    for task_idx in selected_tasks:
        sources, destination = concat_tasks[task_idx]
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        exitcode, sinks = transcode([[vid.path for vid in sources]], destination)
        logging.info(f"Finished {destination} ({datetime.datetime.now()})")
        outputs[destination] = sinks

    logging.info("All done, new files:")
    for sinks in outputs.keys():
        logging.info(sinks)

    return outputs
