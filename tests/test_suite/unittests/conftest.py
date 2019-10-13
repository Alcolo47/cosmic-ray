import contextlib
import os
from pathlib import Path
from typing import Union

import pytest

from cosmic_ray.execution_engines import ExecutionEngine
from cosmic_ray.execution_engines.execution_engine import ExecutionData

_THIS_DIR = Path(os.path.dirname(os.path.realpath(__file__)))


@pytest.fixture
def data_dir():
    "Directory containing test data"
    return _THIS_DIR / 'data'


class PathUtils:
    "Path utilities for testing."
    @staticmethod
    @contextlib.contextmanager
    def excursion(directory):
        """Context manager for temporarily setting `directory` as the current working
        directory.
        """
        old_dir = os.getcwd()
        os.chdir(str(directory))
        try:
            yield
        finally:
            os.chdir(old_dir)


@pytest.fixture
def path_utils():
    "Path utilities for testing."
    return PathUtils


class DummyExecutionEngine(ExecutionEngine):
    def __init__(self):
        self.new_codes = []

    async def execute(self, data: Union[ExecutionData, None]):
        self.new_codes.append(data and data.new_code)


@pytest.fixture
def dummy_execution_engine():
    return DummyExecutionEngine()

