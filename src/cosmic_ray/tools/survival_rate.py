"Tool for printing the survival rate in a session."

import docopt

from cosmic_ray.work_db import use_db, WorkDB


def format_survival_rate():
    """cr-rate

    Usage: cr-rate <session-file>

    Calculate the survival rate of a session.
    """
    arguments = docopt.docopt(
        format_survival_rate.__doc__, version='cr-rate 1.0')
    with use_db(arguments['<session-file>'], WorkDB.Mode.open) as db:  # type: WorkDB
        rate = db.abnormal_rate * 100

    print('{:.2f}'.format(rate))
