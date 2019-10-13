from logging import getLogger
from pathlib import Path
import virtualenv

from cosmic_ray.utils.exceptions import CosmicRayTestingException
from cosmic_ray.workspaces.cloned_workspace import ClonedWorkspace


log = getLogger(__name__)


class ClonedWithVirtualenvWorkspace(ClonedWorkspace):
    """Clone a project and install it into a temporary virtual environment.

    Note that this actually *activates* the virtual environment, so don't construct one
    of these unless you want that to happen in your process.
    """

    def _prepare_directory(self):
        # pylint: disable=fixme
        # TODO: We should allow user to specify which version of Python to use.
        # How? The EnvBuilder could be passed a path to a python interpreter
        # which is used in the call to pip. This path would need to come from
        # the config.

        # Install into venv
        super()._prepare_directory()
        self._venv_path = Path(self._tempdir.name) / 'venv'
        log.info('Creating virtual environment in %s', self._venv_path)
        virtualenv.create_environment(str(self._venv_path))

    def _load_environment(self):
        _activate(self._venv_path)
        _install_sitecustomize(self._venv_path)


def _activate(venv_path):
    """Activate a virtual environment in the current process.

    This assumes a virtual environment that has a "activate_this.py" script, e.g.
    one created with `virtualenv` and *not* `venv`.

    Args:
        venv_path: Path of virtual environment to activate.
    """
    _home_dir, _lib_dir, _inc_dir, bin_dir = virtualenv.path_locations(str(venv_path))
    activate_script = str(Path(bin_dir) / 'activate_this.py')

    # This is the recommended way of activating venvs in a program:
    # https://virtualenv.pypa.io/en/stable/userguide/#using-virtualenv-without-bin-python
    exec(open(activate_script).read(), {'__file__': activate_script})  # pylint: disable=exec-used


_SITE_CUSTOMIZE = """
class {0}(Exception):
    pass

__builtins__['{0}'] = {0}
""".format(CosmicRayTestingException.__name__)


def _install_sitecustomize(venv_path):
    _home_dir, lib_dir, _inc_dir, _bin_dir = virtualenv.path_locations(str(venv_path))
    with open(str(Path(lib_dir) / 'site-packages' / 'sitecustomize.py'), mode='wt', encoding='utf-8') as sc:
        sc.write(_SITE_CUSTOMIZE)
