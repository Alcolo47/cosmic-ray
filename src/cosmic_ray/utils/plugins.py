"""Query and retrieve the various plugins in Cosmic Ray.
"""

import logging

from stevedore import ExtensionManager


log = logging.getLogger(__name__)


def _log_extension_loading_failure(_mgr, ep, err):
    # We have to log at the `error` level here as opposed to, say, `info`
    # because logging isn't configure when we reach here. We need this infor to
    # print with the default logging settings.
    log.error('Operator provider load failure: extension-point="%s", err="%s"',
              ep, err)


def _get_extensions(name):
    for extension in ExtensionManager(name, on_load_failure_callback=_log_extension_loading_failure):
        yield extension.name, extension.plugin


def get_operators_providers():
    yield from _get_extensions('cosmic_ray.operator_providers')


def get_interceptors():
    yield from _get_extensions('cosmic_ray.interceptors')


def get_execution_engines():
    yield from _get_extensions('cosmic_ray.execution_engines')


def get_execution_workspace():
    yield from _get_extensions('cosmic_ray.workspaces')
