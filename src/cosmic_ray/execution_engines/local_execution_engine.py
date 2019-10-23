"""Cosmic Ray execution engine that runs mutations locally on git clones.

This engine creates a pool of subprocesses, each of which execute some portion
of work items in a session. Each of these processes creates a shallow clone of
the git repository containing the code to be mutated/tested in a temporary
directory. This way each process can work independently.

## Enabling the engine

To use the local-git execution engine, set `cosmic-ray.execution-engine.name =
"local-git"` in your Cosmic Ray configuration::

    [cosmic-ray.execution-engine]
    name = "local-git"

## Specifying the source repository

Each subprocess creates its own clone of a source git repository. By default,
the engine determines which repo to use by looking for the repo dominating the
directory in which `cosmic-ray` is executed. However, you can specify a
different repository (e.g. a repo hosted on github) by setting the
`cosmic-ray.execution-engine.local-git.repo-uri`::

    [cosmic-ray.execution-engine.local-git]
    repo-uri = "https://github.com/me/difference-engine-emulator"

## Subprocess environment

The local-git engine launches its subprocesses using the `multiprocessing`
library. As such, the subprocesses run in an environment that is largely
identical to that of the main `cosmic-ray` process.

One major difference is the directory in which the subprocesses run. They run
the root of the cloned repository, so you need to take this into account when
creating the configuration.
"""
import asyncio
import concurrent.futures
import logging
import os
from typing import Union

from cosmic_ray.execution_engines.remote_environment import RemoteEnvironment
from cosmic_ray.utils.config import Config, root_config, Entry
from cosmic_ray.execution_engines import execution_engine_config
from cosmic_ray.execution_engines.execution_engine import ExecutionEngine, \
    ExecutionData


log = logging.getLogger(__name__)


execution_engines_cloning_config = Config(
    execution_engine_config,
    'cloning',
    valid_entries={
        'method': Entry(default='copy', choices=('copy', 'git')),
        'commands': Entry(required=True),
        'repo-uri': None,
        'ignore-files': []
    },
)


class LocalExecutionEngine(ExecutionEngine):
    """The local-git execution engine."""

    def __init__(self):
        ignore_file = root_config['session-file']
        if os.path.abspath(ignore_file).startswith(os.path.abspath(os.getcwd())):
            ignore_file = os.path.basename(ignore_file)
            ignore_file = ''.join('[%s]' % c for c in ignore_file) + '.*'
            execution_engines_cloning_config['ignore-files'].append(ignore_file)

        prepared_data = RemoteEnvironment.prepare_local_side()

        self.executor = concurrent.futures.ProcessPoolExecutor(
            initializer=RemoteEnvironment,
            initargs=(execution_engine_config.get_config(), prepared_data)
        )

    async def execute(self, data: Union[ExecutionData, None]):
        log.debug("Execute %s", data)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, RemoteEnvironment.execute, data)
