import asyncio
import os
from asyncio import Queue, Task
from functools import partial
from itertools import count
from logging import getLogger
from typing import List, Union, Type

import mitogen.core
from cosmic_ray.utils.system_stat import get_cpu_usage
from mitogen.core import Sender
from mitogen.parent import Context
from mitogen.master import Broker, Router

from cosmic_ray.db.work_item import WorkResult
from cosmic_ray.execution_engines import ExecutionEngine
from cosmic_ray.execution_engines.execution_engine import ExecutionData, \
    execution_engine_config
from cosmic_ray.execution_engines.remote_environment import RemoteEnvironment
from cosmic_ray.execution_engines.ssh_remote_environment import \
    SshRemoteEnvironment
from cosmic_ray.utils.config import Config


log = getLogger(__name__)


execution_engine_ssh_config = Config(
    execution_engine_config,
    'ssh',
    valid_entries={
        'hosts': [
            {'hostname': 'localhost', 'username': os.environ.get('USER', ''), 'nice': 10},
        ],

    },
)


async def mito_get(receiver: mitogen.core.Receiver):
    """asyncio version of receiver.get(block=False)
    """
    while True:
        try:
            await asyncio.sleep(1)
            return receiver.get(block=False).unpickle()
        except mitogen.core.TimeoutError:
            pass


async def mito_call(context: Context, func, *args, **kwargs):
    """asyncio version of receiver.call()
    """
    return await mito_get(context.call_async(func, *args, **kwargs))


class SshExecutionEngine(ExecutionEngine):
    """From a list of ssh account, try to launch remote workers.
    Remote workers are bootstrapped by using mitogen module.

    Under each remote host, "local" workers are created until remote cpu reached 90%.
    """
    def __init__(self, hosts=None):
        self.broker = Broker()
        self.broker.shutdown_timeout = 30
        self.host_datas = hosts or execution_engine_ssh_config['hosts']  # type: List

        # List of initializer asyncio tasks.
        self.initializer_tasks = []  # type: List[Task]

        # List of available workers (mutagen contexts)
        self.available_contexts = None  # type: Union[Queue, None]

    async def init(self):
        self.available_contexts = Queue()
        loop = asyncio.get_running_loop()
        router = Router(self.broker)

        # Prepare data to send on remote worker to initialize workspaces. (see Cloner classes).
        prepared_data = SshRemoteEnvironment.prepare_local_side()

        # Initialize each remote host with parallel coroutines.
        log.debug("Initialising %s hosts", len(self.host_datas))
        for host_data in self.host_datas:
            try:
                coro = self._do_init_ssh(router, host_data, prepared_data)
                self.initializer_tasks.append(loop.create_task(coro))
            except Exception:
                log.exception("During initialisation of %s", host_data)

    async def no_more_jobs(self):
        for task in self.initializer_tasks:
            task.cancel()

    def close(self):
        if self.broker:
            self.broker.shutdown()
            self.broker = None

    async def _do_init_ssh(self, router: Router, host_data, prepared_data):
        """Initialize host
            - Create a mitogen context on the remote host
            - Initialize a remote environment (class SshRemoteEnvironment)
                - copy sources but don't load environment (mitogen don't like this!)
            - Create local workers (mitogen context) until cpu reach 90%
                - Create "local" environment (class RemoteEnvironment with CopyCloner)
                - load environment
                - Add this mitogen context to self.available_contexts

            Try this for ever.
        """

        loop = asyncio.get_running_loop()
        hostname = host_data['hostname']
        nice = host_data.pop('nice', None)

        # Retry for ever loop
        while True:
            try:
                if host_data.get('identity_file'):
                    # Some ssh client can tell you: "Permissions 0666 for 'identity_file' are too open."
                    os.chmod(host_data['identity_file'], mode=0o600)

                log.info("Try to initialize host %s", hostname)
                ssh_context = await loop.run_in_executor(None, partial(router.ssh,
                                                                       **host_data, name="ssh %s" % hostname, python_path='python3'))

                host_config = execution_engine_config.get_config().copy()
                worker_config = host_config.copy()

                # Alter ssh config: Don't load environment: (mitogen don't like this)
                cloning_config = host_config['cloning'] = host_config['cloning'].copy()
                cloning_config['python-load'] = None

                clone_dir = await self._do_init_new_context(ssh_context,
                                                            _remote_host_initialize,
                                                            host_config,
                                                            nice,
                                                            prepared_data)

                # Alter worker config:
                cloning_config = worker_config['cloning'] = worker_config['cloning'].copy()
                # - Don't build environment: already done in ssh context
                cloning_config['init-commands'] = []
                # - Always copy from local copy (ssh context)
                cloning_config['src-dir'] = clone_dir
                cloning_config['method'] = 'copy'
                # - Load virtualenv from initial clone
                if cloning_config['python-load']:
                    cloning_config['python-load'] = os.path.join(clone_dir, cloning_config['python-load'])

                # Create local workers for ever
                for i in count(start=1):
                    sub_context = await loop.run_in_executor(None, partial(router.local,
                                                                           via=ssh_context, name=str(i), python_path='python3'))
                    await self._do_init_new_context(sub_context,
                                                    _remote_worker_initialize,
                                                    worker_config,
                                                    nice,
                                                    None)

                    # This new context is available for jobs
                    await self.available_contexts.put(sub_context)
                    log.info("Host instance %s READY", sub_context.name)

                    # Wait until cpu usage will be under 90%, with low disk usage
                    while True:
                        cpu_usage, load_avg = await mito_call(ssh_context, _get_system_stat)
                        if load_avg > 10:
                            log.warning('Localhost over-burn: loaf avg/cpu: %2.1f  cpu: %2.f%%', load_avg, cpu_usage*100)
                        else:
                            cpu_usage, load_avg = await mito_call(ssh_context, _get_system_stat)
                            log.info('Host %s: loaf avg/cpu: %2.1f  cpu: %2.f%%', ssh_context.name, load_avg, cpu_usage*100)
                            if cpu_usage < .9 and load_avg < 10:
                                break
                        await asyncio.sleep(5)

            except mitogen.core.Error as ex:
                log.warning("ssh connection to %s failed: %s", hostname, ex)
                # Retry for ever
                await asyncio.sleep(30)

    @staticmethod
    async def _do_init_new_context(context: Context,
                                   initializer,
                                   config,
                                   nice,
                                   prepared_data):
        log.info("Initializing host instance %s", context.name)
        with mitogen.core.Receiver(context.router) as receiver:
            p = context.call_async(initializer, config, nice, receiver.to_sender())
            sender = receiver.get().unpickle()
            sender.send(prepared_data)
            clone_dir = await mito_get(p)
        return clone_dir

    async def execute(self, data: Union[ExecutionData, None]):
        context: Context = await self.available_contexts.get()
        log.debug("Running test on %s", context.name)
        if data:
            # Convert data with native type to prepare transfer
            data = data.to_dict()
        try:
            job_id, result = await mito_call(context, _execute, data)

        except mitogen.core.Error as ex:
            log.warning("We lost connection on %s: %s", context.name, ex)
            # Re-inject job
            return await self.execute(data)

        else:
            # Convert from native type to class
            result = WorkResult.from_dict(result)
            await self.available_contexts.put(context)
            return job_id, result


# Functions called no remote host

def _on_shutdown():
    RemoteEnvironment.cleanup()


@mitogen.core.takes_router
def _remote_host_initialize(config, nice, sender: Sender, router: Router):
    return _remote_initialize(config, nice, sender, SshRemoteEnvironment, router)


@mitogen.core.takes_router
def _remote_worker_initialize(config, nice, sender: Sender, router: Router):
    return _remote_initialize(config, nice, sender, RemoteEnvironment, router)


def _remote_initialize(config,
                       nice,
                       sender: Sender,
                       remote_environment_class: Type[RemoteEnvironment],
                       router: Router):
    mitogen.core.listen(router.broker, 'shutdown', _on_shutdown)
    with mitogen.core.Receiver(router) as receiver:
        sender.send(receiver.to_sender())
        prepared_data = receiver.get().unpickle()
    env = remote_environment_class(config, prepared_data)
    if nice:
        os.nice(nice)
    return env.clone_dir


def _get_system_stat():
    cpu_usage = get_cpu_usage()
    # io_load = get_disk_time_in_queue()
    cpu_count = os.cpu_count()
    load_avg1, load_avg5, load_avg15 = os.getloadavg()
    return cpu_usage, load_avg1 / cpu_count


def _execute(data):
    if data:
        data = ExecutionData.from_dict(data)
    job_id, result = RemoteEnvironment.execute(data)
    result = result.to_dict()
    return job_id, result
