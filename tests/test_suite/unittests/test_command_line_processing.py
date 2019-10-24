"""Tests for the command line interface and return codes.
"""
import os
from exit_codes import ExitCode
import pytest

import cosmic_ray.cli
import cosmic_ray.utils.config
import cosmic_ray.utils.modules
import cosmic_ray.utils.plugins
import cosmic_ray.commands.new_config
import cosmic_ray.execution_engines.worker


@pytest.fixture
def config_file(tmpdir):
    return os.path.join(tmpdir, 'config.toml')


def _make_config(test_command='python -m unittest discover tests',
                 timeout=100,
                 engine='local'):
    return {
        'module-path': 'foo.py',
        'timeout': timeout,
        'test-command': test_command,
        'execution-engine': {'name': engine},
        'exclude-modules': [],
        'cloning': {'method': 'copy'}
    }


@pytest.fixture
def local_unittest_config(config_file: str):
    """Creates a valid config file for local, unittest-based execution, returning
    the path to the config.
    """
    with open(config_file, mode='wt') as handle:
        config = _make_config()
        config_str = cosmic_ray.utils.config.serialize_config(config)
        handle.write(config_str)
    return config_file


@pytest.fixture
def lobotomize(monkeypatch):
    """Short-circuit some of CR's core functionality to make testing simpler.
    """
    # This effectively prevent init from actually trying to scan the module in the config.
    monkeypatch.setattr(cosmic_ray.utils.modules, 'find_modules', lambda *args: [])

    # Make cosmic_ray.worker.worker just return a simple empty dict.
    monkeypatch.setattr(cosmic_ray.execution_engines.worker, 'worker', lambda *args: {})


def test_invalid_command_line_returns_EX_USAGE():
    assert cosmic_ray.cli.main(['run', 'foo', 'bar']) == ExitCode.USAGE


def test_non_existent_file_returns_EX_NOINPUT():
    assert cosmic_ray.cli.main(['run', 'dont_exists']) == ExitCode.NO_INPUT


def test_new_config_success_returns_EX_OK(monkeypatch, config_file):
    monkeypatch.setattr(cosmic_ray.commands.new_config, 'new_config', lambda *args: '')
    errcode = cosmic_ray.cli.main(['new-config', config_file])
    assert errcode == ExitCode.OK


# NOTE: We have integration tests for the happy-path for many commands, so we don't cover them explicitly here.


def test_operators_success_returns_EX_OK():
    assert cosmic_ray.cli.main(['operators']) == ExitCode.OK
