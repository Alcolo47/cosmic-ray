import os
import signal
from logging import getLogger
from typing import Union, Tuple, Type

from cosmic_ray.db.work_item import WorkResult
from cosmic_ray.execution_engines import execution_engine_config
from cosmic_ray.execution_engines.execution_engine import ExecutionData
from cosmic_ray.execution_engines.worker import Worker
from cosmic_ray.workspaces import workspaces, \
    execution_engines_workspace_config
from cosmic_ray.workspaces.cloner import Cloner
from cosmic_ray.workspaces.cloner.copy_cloner import CopyCloner
from cosmic_ray.workspaces.cloner.git_cloner import GitCloner
from cosmic_ray.workspaces.workspace import Workspace


log = getLogger(__name__)


class RemoteEnvironment:
    _instance = None  # type: RemoteEnvironment

    def __init__(self, config, prepared_data):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        type(self)._instance = self
        execution_engine_config.set_config(config)

        log.info('Initialize local-git worker in PID %s', os.getpid())

        cloner = self._get_cloner_class()()
        cloner.load_prepared_data(prepared_data)
        self._workspace = self._build_workspace(cloner)  # type: Workspace
        self._worker = Worker(self._workspace.clone_dir)

        # # Register a finalizer
        # multiprocessing.util.Finalize(self._workspace,
        #                               self._workspace.cleanup, exitpriority=16)

    @classmethod
    def prepare_local_side(cls):
        return cls._get_cloner_class().prepare_local_side()

    def _build_workspace(self, cloner: Cloner) -> Workspace:
        workspace_class = workspaces[execution_engines_workspace_config['type']]
        return workspace_class(cloner)

    @classmethod
    def _get_cloner_class(cls) -> Type[Cloner]:
        from cosmic_ray.execution_engines.local_execution_engine import execution_engines_cloning_config

        method = execution_engines_cloning_config['method']
        if method == 'copy':
            return CopyCloner
        if method == 'git':
            return GitCloner
        raise Exception("Clone method '%s' unknown" % method)

    @classmethod
    def execute(cls, data):
        if data:
            data = ExecutionData(**data)
        job_id, result = cls._instance._execute(data)
        result = result.to_dict()
        return job_id, result

    def _execute(self, data: Union[ExecutionData, None]) -> Tuple[str, WorkResult]:
        log.debug('execute_work_item (%s): %s', os.getpid(), data)
        result = self._worker.worker(data)
        return (data and data.job_id), result
