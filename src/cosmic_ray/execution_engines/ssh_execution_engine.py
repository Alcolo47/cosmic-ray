import asyncio
import os
from asyncio import Queue
from concurrent.futures.thread import ThreadPoolExecutor
from typing import List, Type, Union

from mitogen.core import Receiver, takes_router, Router
from mitogen.parent import Context
from mitogen.master import Broker, Router
from mitogen.select import Select

from cosmic_ray.db.work_item import WorkResult
from cosmic_ray.execution_engines import ExecutionEngine, \
    execution_engine_config
from cosmic_ray.execution_engines.execution_engine import ExecutionData
from cosmic_ray.execution_engines.ssh_remote_environment import \
    SshRemoteEnvironment
from cosmic_ray.utils.config import Config
from cosmic_ray.workspaces import workspaces, \
    execution_engines_workspace_config
from cosmic_ray.workspaces.workspace import Workspace

execution_engine_ssh_config = Config(
    execution_engine_config,
    'ssh',
    valid_entries={
        'hosts': [
            {'hostname': 'localhost', 'username': os.getlogin()},
        ],

    },
)


class SshExecutionEngine(ExecutionEngine):
    def __init__(self, hosts=None):
        self.broker = Broker()
        self.hosts = hosts or execution_engine_ssh_config['hosts']  # type: List
        self.available_contexts = Queue()

    async def init(self):
        executor = ThreadPoolExecutor()
        loop = asyncio.get_running_loop()
        router = Router(self.broker)

        workspace_class = workspaces[execution_engines_workspace_config['type']]  # type: Type[Workspace]
        workspace_class_name = (workspace_class.__module__, workspace_class.__name__)

        prepared_data = SshRemoteEnvironment.prepare_local_side()

        tasks = [await loop.run_in_executor(executor, self._do_init,
                                            router,
                                            router.ssh(**host, python_path='python3'),
                                            workspace_class_name,
                                            prepared_data)
                 for host in self.hosts]
        await asyncio.gather(*tasks)

    def close(self):
        if self.broker:
            self.broker.shutdown()
            self.broker = None

    async def _do_init(self, router: Router, context: Context, workspace_class_name, prepared_data):
        with Receiver(router) as receiver:
            p = context.call_async(_worker_initialize, execution_engine_config.get_config(), workspace_class_name,
                                   receiver.to_sender())
            sender = receiver.get().unpickle()
            sender.send(prepared_data)
            Select([p])
        await self.available_contexts.put(context)

    async def execute(self, data: Union[ExecutionData, None]):
        context: Context = await self.available_contexts.get()
        if data:
            data = data.__dict__
        job_id, result = context.call(_execute, data)
        result = WorkResult.from_dict(result)
        await self.available_contexts.put(context)
        return job_id, result


@takes_router
def _worker_initialize(config, workspace_class_name, control_sender, router: Router):
    with Receiver(router) as receiver:
        control_sender.send(receiver.to_sender())
        prepared_data = receiver.get().unpickle()
        SshRemoteEnvironment(config, prepared_data, workspace_class_name)


def _execute(data):
    return SshRemoteEnvironment.execute(data)
