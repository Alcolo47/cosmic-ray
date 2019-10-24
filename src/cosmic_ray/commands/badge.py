import os
from logging import getLogger

from anybadge import Badge

from cosmic_ray.utils.config import root_config, Config, Entry
from cosmic_ray.utils.survival_rate import survival_rate
from cosmic_ray.db.work_db import WorkDB


log = getLogger()


badge_config = Config(
    root_config,
    'badge',
    valid_entries={
        'output': Entry(required=True),
        'label': "mutation",
        'format': "%.2f %%",
        'thresholds': {
            '50': 'red',
            '70': 'orange',
            '100': 'yellow',
            '101': 'green',
        },
    },
)


def generate_badge(work_db: WorkDB, badge_filename):
    percent = 100 - survival_rate(work_db)

    if not badge_filename:
        badge_filename = badge_config['output']

    badge = Badge(
        label=badge_config['label'],
        value=percent,
        value_format=badge_config['format'],
        thresholds=badge_config['thresholds'],
    )

    log.info(("Generating badge: " + badge_config['format']) % percent)

    try:
        os.unlink(badge_filename)
    except OSError:
        pass

    directory = os.path.dirname(badge_filename)
    if directory:
        os.makedirs(directory, exist_ok=True)

    badge.write_badge(badge_filename)
