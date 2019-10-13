"""An interceptor that uses spor metadata to determine when specific mutations
should be skipped.
"""
import logging

from spor.repository import open_repository

from cosmic_ray.interceptors.interceptor import Interceptor
from cosmic_ray.db.work_db import WorkDB
from cosmic_ray.db.work_item import WorkerOutcome, WorkItem

log = logging.getLogger()


class SporInterceptor(Interceptor):

    def pre_scan_module_path(self, module_path) -> bool:
        with module_path.open(mode="rt") as handle:
            self.lines = handle.readlines()
        return True

    def new_work_item(self,
                      work_db: WorkDB,
                      operator,
                      node,
                      work_item: WorkItem):

        """Look for WorkItems in `work_db` that should not be mutated due to spor metadata.

        For each WorkItem, find anchors for the item's file/line/columns. If an
        anchor exists with metadata containing `{mutate: False}` then the WorkItem
        is marked as SKIPPED.
        """

        try:
            repo = open_repository(work_item.module_path)
        except ValueError:
            log.info("No spor repository for %s", work_item.module_path)
            return True

        for _, anchor in repo.items():
            if anchor.file_path != work_item.module_path.absolute():
                continue

            metadata = anchor.metadata

            if _item_in_context(self.lines, work_item,
                                anchor.context) and not metadata.get("mutate", True):
                log.info(
                    "spor skipping %s %s %s %s %s %s",
                    work_item.job_id,
                    work_item.operator_name,
                    work_item.occurrence,
                    work_item.module_path,
                    work_item.start_pos,
                    work_item.end_pos,
                )

                self._add_work_result(
                    work_db,
                    work_item,
                    output="filtered by spor",
                    worker_outcome=WorkerOutcome.SKIPPED,
                )


def _line_and_col_to_offset(lines, line, col):
    """Figure out the offset into a file for a particular line and col.

    This can return offsets that don't actually exist in the file. If you
    specify a line that exists and a col that is past the end of that line, this
    will return a "fake" offset. This is to account for the fact that a
    WorkItem's end_pos is one-past the end of a mutation, and hence potentially
    one-past the end of a file.

    Args:
        lines: A sequence of the lines in a file.
        line: A one-based index indicating the line in the file.
        col: A zero-based index indicating the column on `line`.

    Raises: ValueError: If the specified line found in the file.
    """

    offset = 0
    for index, contents in enumerate(lines, 1):
        if index == line:
            return offset + col

        offset += len(contents)

    raise ValueError("Offset {}:{} not found".format(line, col))


def _item_in_context(lines, item, context):
    """Determines if a WorkItem falls within an anchor.

    This only returns True if a WorkItems start-/stop-pos range is *completely*
    within an anchor, not just if it overalaps.
    """
    start_offset = _line_and_col_to_offset(lines, item.start_pos[0],
                                           item.start_pos[1])
    stop_offset = _line_and_col_to_offset(lines, item.end_pos[0],
                                          item.end_pos[1])
    width = stop_offset - start_offset

    return start_offset >= context.offset and width <= len(context.topic)
