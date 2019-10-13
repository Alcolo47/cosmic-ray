"""Implementation of the 'execute' command.
"""
import os
import logging

log = logging.getLogger(__name__)

_progress_messages = {}  # pylint: disable=invalid-name


def update_progress(work_db):
    num_work_items = work_db.num_work_items
    pending = num_work_items - work_db.num_results
    total = num_work_items
    remaining = total - pending
    message = "{} out of {} completed".format(remaining, total)
    _progress_messages[work_db.name] = message


def report_progress(stream):
    for db_name, progress_message in _progress_messages.items():
        session = os.path.splitext(db_name)[0]
        print("{session} : {progress_message}".format(session=session, progress_message=progress_message),
              file=stream)
