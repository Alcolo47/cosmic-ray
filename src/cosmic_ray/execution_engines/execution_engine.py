"Base execution-engine implementation details."

import abc
from typing import Union

from pathlib import Path


class ExecutionData:
    def __init__(self, job_id, filename, new_code):
        self.job_id = job_id
        self.filename = filename  # type: Path
        self.new_code = new_code

    def __str__(self):
        return self.job_id


class ExecutionEngine(metaclass=abc.ABCMeta):
    "Base class for execution engine plugins."

    @abc.abstractmethod
    async def execute(self, data: Union[ExecutionData, None]):
        pass

    def close(self):
        pass
