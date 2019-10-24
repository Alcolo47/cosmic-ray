import os
import subprocess
import sys

import pytest

from cosmic_ray.db.work_db import use_db, WorkDB
from cosmic_ray.utils.survival_rate import survival_rate


@pytest.fixture(scope="session")
def example_project_root(pytestconfig):
    return os.path.join(pytestconfig.rootdir, "..", "example_project")


@pytest.fixture
def config(tester, engine):
    """Get config file name.
    """
    return "cosmic-ray.{}.{}.conf".format(tester, engine)


def test_e2e(example_project_root: str, config, session):
    subprocess.check_call(
        [sys.executable, "-m", "cosmic_ray.cli", "run", "--session", session, config],
        cwd=example_project_root)

    session_path = os.path.join(example_project_root, session)
    with use_db(session_path, WorkDB.Mode.open) as work_db:
        rate = survival_rate(work_db)
        assert rate == 0.0


def test_importing(example_project_root: str, session):
    config = "cosmic-ray.import.conf"

    subprocess.check_call(
        [sys.executable, "-m", "cosmic_ray.cli", "run", "--session", session, config],
        cwd=example_project_root,
    )

    session_path = os.path.join(example_project_root, session)
    with use_db(session_path, WorkDB.Mode.open) as work_db:
        rate = survival_rate(work_db)
        assert rate == 0.0


def test_empty___init__(example_project_root: str, session):
    config = "cosmic-ray.empty.conf"

    subprocess.check_call(
        [sys.executable, "-m", "cosmic_ray.cli", "run", "--session", session, config],
        cwd=example_project_root,
    )

    session_path = os.path.join(example_project_root, session)
    with use_db(session_path, WorkDB.Mode.open) as work_db:
        rate = survival_rate(work_db)
        assert rate == 0.0


def test_config_command(example_project_root: str, session):
    config = "cosmic-ray.import.conf"

    subprocess.check_call(
        [sys.executable, "-m", "cosmic_ray.cli", "run", "--session", session, config],
        cwd=example_project_root,
    )

    subprocess.check_call(
        [sys.executable, "-m", "cosmic_ray.cli", "config", session],
        cwd=example_project_root,
    )
