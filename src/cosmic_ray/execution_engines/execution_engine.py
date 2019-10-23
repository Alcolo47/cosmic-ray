"""Base execution-engine implementation details.
"""

import abc
from typing import Union


class ExecutionData:
    def __init__(self, job_id, filename, new_code):
        self.job_id = job_id
        self.filename = str(filename)
        self.new_code = new_code

    def __str__(self):
        return self.job_id


class ExecutionEngine(metaclass=abc.ABCMeta):
    """Base class for execution engine plugins.
    """

    @abc.abstractmethod
    async def execute(self, data: Union[ExecutionData, None]):
        pass

    async def init(self):
        pass

    def close(self):
        pass

    def __del__(self):
        self.close()
