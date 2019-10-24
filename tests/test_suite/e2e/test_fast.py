import os
import subprocess
import sys

import pytest

from cosmic_ray.db.work_db import use_db, WorkDB
from cosmic_ray.utils.survival_rate import survival_rate


@pytest.fixture(scope="session")
def project_root(pytestconfig):
    return os.path.join(pytestconfig.rootdir, "..", "fast_tests")


def test_fast_tests(project_root: str, session):
    """This tests that CR works correctly on suites that execute very rapidly.

    A single mutation-test round can be faster than the resolution of file timestamps for some filesystems. When this
    happens, we found that Python would not correctly create new pyc files - because it had no way to know do do so! We
    modified CR to work around this problem, and this test tries to ensure that we don't regress.
    """
    subprocess.check_call(
        [sys.executable, "-m", "cosmic_ray.cli", "run", "--session", session, "cr.conf"],
        cwd=project_root)

    session_path = os.path.join(project_root, session)
    with use_db(session_path, WorkDB.Mode.open) as work_db:
        rate = survival_rate(work_db)
        assert round(rate, 2) == 15.38
