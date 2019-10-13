"Tool for printing the survival rate in a session."

from cosmic_ray.db.work_db import WorkDB


def survival_rate(work_db: WorkDB):
    """Calcuate the survival rate for the results in a WorkDB.
    """
    kills = sum(r.is_killed for _, r in work_db.results)
    num_results = work_db.num_results

    if not num_results:
        return 0

    return (1 - kills / num_results) * 100
