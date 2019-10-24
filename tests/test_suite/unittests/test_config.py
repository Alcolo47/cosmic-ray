"""Tests for config loading functions.
"""
import io
import os

import pytest

from cosmic_ray.utils.config import ConfigError, load_config, serialize_config


def test_load_invalid_stdin_raises_ConfigError(mocker):
    temp_stdin = io.StringIO()
    temp_stdin.name = 'stringio'
    temp_stdin.write('{invalid')
    temp_stdin.seek(0)
    mocker.patch('sys.stdin', temp_stdin)

    with pytest.raises(ConfigError):
        load_config()


def test_load_non_existent_file_raises_ConfigError():
    with pytest.raises(ConfigError):
        load_config('/foo/bar/this/does/no-exist/I/hope')


def test_load_from_invalid_config_file_raises_ConfigError(tmpdir: str):
    config_path = os.path.join(tmpdir, 'config.yml')
    with open(config_path, mode='wt', encoding='utf-8') as handle:
        handle.write('{asdf')
    with pytest.raises(ConfigError):
        load_config(config_path)


def test_load_from_non_utf8_file_raises_ConfigError(tmpdir: str):
    config_path = os.path.join(tmpdir, 'config.conf')
    config = {'key': 'value'}
    with open(config_path, mode='wb') as handle:
        handle.write(serialize_config(config).encode('utf-16'))
    with pytest.raises(ConfigError):
        load_config(config_path)
