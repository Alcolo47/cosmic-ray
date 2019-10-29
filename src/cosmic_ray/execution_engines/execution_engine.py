"""Base execution-engine implementation details.
"""

import abc
import gzip
from typing import Union

from cosmic_ray.utils.config import Config, root_config, Entry
from cosmic_ray.utils.serializable import Serializable

execution_engine_config = Config(
    root_config,
    'execution-engine',
    valid_entries={
        'type': 'local',
        'run-with-no-mutation': Entry(default=False),
        'nice': 0,
    },
)


class ExecutionData(Serializable):
    def __init__(self, job_id, filename: str, new_code: str = None, zipped_code: bytes = None):
        self.job_id = job_id
        self.filename = filename
        self.zipped_code = zipped_code
        if new_code is not None:
            self.new_code = new_code

    @property
    def new_code(self):
        return gzip.decompress(self.zipped_code).decode()

    @new_code.setter
    def new_code(self, c: str):
        self.zipped_code = gzip.compress(c.encode())

    def __str__(self):
        return self.job_id


class ExecutionEngine(metaclass=abc.ABCMeta):
    """Base class for execution engine plugins.
    """

    @abc.abstractmethod
    async def execute(self, data: Union[ExecutionData, None]):
        pass

    async def init(self):
        """Launch initialization of workers
        """
        pass

    async def no_more_jobs(self):
        """Indicate that all jobs are done.
        """
        pass

    def close(self):
        """Destroy all workers.
        This function is always called.
        """
        pass

    def __del__(self):
        self.close()
