"""Functions related to finding modules for testing.
"""
import glob
import logging
import os
from collections import defaultdict
from logging import getLogger
from typing import Iterable


log = getLogger(__name__)


def find_modules(module_path: str):
    """Find all modules in the module (possibly package) represented by `module_path`.

    Args:
        module_path: Python package or module.

    Returns: An iterable of paths Python modules (i.e. *py files).
    """
    if os.path.isfile(module_path):
        if os.path.splitext(module_path)[1] == '.py':
            yield module_path
    elif os.path.isdir(module_path):
        yield from glob.iglob('{}/**/*.py'.format(module_path), recursive=True)


def filter_paths(paths: Iterable[str], excluded_paths: Iterable[str]):
    """Filter out path matching one of excluded_paths glob

    Args:
        paths: path to filter.
        excluded_paths: globs of modules to exclude.

    Returns: An iterable of paths Python modules (i.e. *py files).
    """
    excluded = set(f for excluded_path in excluded_paths
                   for f in glob.glob(excluded_path, recursive=True))
    return set(paths) - excluded


def get_module_list(exclude_modules: Iterable[str], module_path: str):
    modules = find_modules(module_path)
    modules = filter_paths(modules, exclude_modules)
    if log.isEnabledFor(logging.INFO):
        log.info('Modules discovered:')
        per_dir = defaultdict(list)
        for module in modules:
            module_dir, module_name = os.path.split(module)
            per_dir[module_dir].append(module_name)
        for dir, files in per_dir.items():
            log.info(' - %s: %s', dir, ', '.join(sorted(files)))
    return modules
