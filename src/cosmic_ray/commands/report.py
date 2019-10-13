"""Tool for printing reports on mutation testing sessions.
"""

from cosmic_ray.utils.survival_rate import survival_rate


def print_report(work_db, show_output, show_diff, show_pending):
    for work_item, result in work_db.completed_work_items:
        print('{} {} {} {}'.format(work_item.job_id, work_item.module_path,
                                   work_item.operator_name,
                                   work_item.occurrence))

        print('worker outcome: {}, test outcome: {}'.format(
            result.worker_outcome, result.outcome))

        if show_output:
            print('=== OUTPUT ===')
            print(result.output)
            print('==============')

        if show_diff:
            print('=== DIFF ===')
            print(result.diff)
            print('============')

    if show_pending:
        for work_item in work_db.pending_work_items:
            print('{} {} {} {}'.format(
                work_item.job_id, work_item.module_path,
                work_item.operator_name, work_item.occurrence))

    num_items = work_db.num_work_items
    num_complete = work_db.num_results

    print('total jobs: {}'.format(num_items))

    if num_complete > 0:
        print('complete: {} ({:.2f}%)'.format(
            num_complete, num_complete / num_items * 100))
        print('survival rate: {:.2f}%'.format(survival_rate(work_db)))
    else:
        print('no jobs completed')
