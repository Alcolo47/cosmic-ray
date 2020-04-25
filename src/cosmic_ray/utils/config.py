"""Configuration module."""
from contextlib import contextmanager
import logging
import sys
from typing import Dict

import toml
import yaml

log = logging.getLogger()


class Entry:
    def __init__(self, _=None, default=None, required=False, choices=None):
        if _ is not None:
            raise Exception("Use named parameters")
        self.default = default
        self.required = required
        self._choices = choices

    @classmethod
    def from_data(cls, data):
        if isinstance(data, Entry):
            return data
        else:
            return cls(required=False, default=data)

    @property
    def choices(self):
        if callable(self._choices):
            self._choices = self._choices()
        return self._choices

    def explain(self):
        if self.required or self.choices:
            r = []
            if self.default is not None:
                r.append(str(self.default))
            if self.required:
                r.append("<REQUIRED>")
            if self.choices:
                r.append("Choices: (%s)" % ', '.join(self.choices))
            return '  '.join(r)
        else:
            return self.default


class ConfigRoot:
    valid_entries = {
        # key: default_value
    }

    def __init__(self, valid_entries=None):
        if valid_entries is None:
            valid_entries = self.valid_entries
        self._children = {}  # type: Dict[str, Config]
        self._local_conf = {}
        self.valid_entries = {k: Entry.from_data(d) for k, d in valid_entries.items()}

    def _add_child(self, key, conf):
        assert key not in self._children
        assert key not in self.valid_entries
        self._children[key] = conf
        conf.set_config(self._local_conf.get(key, {}))

    def set_config(self, local_conf):
        if local_conf is None:
            local_conf = {}
        self._local_conf = local_conf
        for key, child in self._children.items():
            child.set_config(local_conf.get(key, {}))

    def get_config(self):
        conf = {key: child.get_config() for key, child in self._children.items()}
        conf.update(self._local_conf)
        return conf

    def get_config_with_default(self):
        conf = {key: child.get_config_with_default() for key, child in self._children.items()}
        default = ((key, e.explain()) for key, e in self.valid_entries.items())
        conf.update(default)
        conf.update(self._local_conf)
        return conf

    def __getitem__(self, key):
        assert key in self.valid_entries
        value = self._local_conf.get(key, self)
        if value is self:
            value = self.valid_entries[key].default
        return value

    def __setitem__(self, key, value):
        assert key in self.valid_entries
        self._local_conf[key] = value


class Config(ConfigRoot):
    def __init__(self, base_conf, key, valid_entries=None):
        super(Config, self).__init__(valid_entries)
        self._key = key
        self._base_conf = base_conf
        base_conf._add_child(key, self)


class RootConfig(ConfigRoot):
    valid_entries = {
        'session-file': 'cosmic-ray.sqlite',
        'module-path': Entry(required=True),
        'exclude-modules': [],
        'python-version': None,
    }

    def set_config(self, local_conf):
        super().set_config(local_conf)
        if not self['python-version']:
            python_version = "{}.{}".format(sys.version_info.major,
                                            sys.version_info.minor)
            self['python-version'] = python_version


root_config = RootConfig()


def load_config(filename=None):
    """Load a configuration from a file or stdin.

    If `filename` is `None` or "-", then configuration gets read from stdin.

    Returns: A `ConfigDict`.

    Raises: ConfigError: If there is an error loading the config.
    """
    try:
        with _config_stream(filename) as handle:
            filename = handle.name
            config = deserialize_config(handle)
            root_config.set_config(config)

    except (toml.TomlDecodeError, UnicodeDecodeError) as exc:
        raise ConfigError('Error loading configuration from {}'.format(filename)) from exc

    except FileNotFoundError as exc:
        raise ConfigFileNotFoundError('Error loading configuration from {}'.format(filename)) from exc


def deserialize_config(handle):
    """Parse a serialized config into a ConfigDict.
    """
    try:
        return yaml.safe_load(handle)['cosmic-ray']
    except yaml.error.YAMLError:
        handle.seek(0)
        return toml.loads(handle.read())['cosmic-ray']


def serialize_config(config):
    """Return the serialized form of `config`.
    """
    return yaml.dump({'cosmic-ray': config})
    # return toml.dumps({'cosmic-ray': config})


class ConfigError(Exception):
    """Base class for exceptions raised by ConfigDict.
    """


class ConfigKeyError(ConfigError, KeyError):
    """KeyError subclass raised by ConfigDict.
    """


class ConfigValueError(ConfigError, ValueError):
    """ValueError subclass raised by ConfigDict.
    """

class ConfigFileNotFoundError(ConfigError, FileNotFoundError):
    """ValueError subclass raised by ConfigDict.
    """


@contextmanager
def _config_stream(filename):
    """Given a configuration's filename, this returns a stream from which a configuration can be read.

    If `filename` is `None` or '-' then stream will be `sys.stdin`. Otherwise,
    it's the open file handle for the filename.
    """
    if filename is None or filename == '-':
        log.info('Reading config from stdin')
        yield sys.stdin
    else:
        with open(filename, mode='rt') as handle:
            log.info('Reading config from %r', filename)
            yield handle
