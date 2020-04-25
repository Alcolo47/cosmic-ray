"""A tool for generating HTML reports.
"""

import datetime

from itertools import chain

from yattag import Doc

from cosmic_ray.db.work_item import Outcome
from cosmic_ray.utils.config import root_config, Config
from cosmic_ray.utils.survival_rate import survival_rate
from cosmic_ray.db.work_item import WorkItem
from cosmic_ray.db.work_item import WorkResult


report_html_config = Config(
    root_config,
    'report_html',
    valid_entries={
        'output': None,
    },
)


def generate_html_report(db, only_completed, skip_success):
    # pylint: disable=too-many-statements
    doc, tag, text = Doc().tagtext()
    doc.asis('<!DOCTYPE html>')
    with tag('html', lang='en'):
        with tag('head'):
            doc.stag('meta', charset='utf-8')
            doc.stag(
                'meta',
                name='viewport',
                content='width=device-width, initial-scale=1, shrink-to-fit=no')
            doc.stag(
                'link',
                rel='stylesheet',
                href='https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css',
                integrity='sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T',
                crossorigin='anonymous')
            with tag('title'):
                text('Cosmic Ray Report')
        with tag('body'):
            with tag('div', klass='container'):
                with tag('h1'):
                    with tag('p', klass='text-dark'):
                        text('Cosmic Ray Report')

            all_items = db.completed_work_items
            if not only_completed:
                incomplete = ((item, None) for item in db.pending_work_items)
                all_items = chain(all_items, incomplete)

            num_items = db.num_work_items
            num_complete = db.num_results

            with tag('div', klass='container'):

                # Summary info

                with tag('div', klass='mb-1', id='summary_info___accordion'):
                    with tag('div', klass='card'):
                        with tag('a', ('data-toggle', 'collapse'), ('data-target', '#summary_info___collapse_1'),
                                 ('aria-expanded', 'true'), ('aria-controls', 'summary_info___collapse_1'), href='#'):
                            with tag('div', klass='card-header', id='summary_info___heading_1'):
                                with tag('button', klass='btn btn-outline-dark'):
                                    with tag('h4', klass='m-0'):
                                        text('Summary info')

                        with tag('div', ('aria-labelledby', 'summary_info___heading_1'),
                                 ('data-parent', '#summary_info___accordion'),
                                 klass='collapse show', id='summary_info___collapse_1'):
                            with tag('div', klass='card-body'):
                                with tag('p'):
                                    text('Date time: {}'.format(datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')))

                                with tag('p'):
                                    text('Total jobs: {}'.format(num_items))

                                if num_complete > 0:
                                    with tag('p'):
                                        text('Complete: {} ({:.2f}%)'.format(
                                            num_complete, num_complete / num_items * 100))
                                    with tag('p'):
                                        text('Survival rate: {:.2f}%'.format(survival_rate(db)))
                                else:
                                    with tag('p'):
                                        text('No jobs completed')

                # Job list

                with tag('div', klass='mb-1', id='job_list___accordion'):
                    with tag('div', klass='card'):
                        with tag('a', ('data-toggle', 'collapse'), ('data-target', '#job_list___collapse_1'),
                                 ('aria-expanded', 'false'), ('aria-controls', 'job_list___collapse_1'), href='#'):
                            with tag('div', klass='card-header', id='job_list___heading_1'):
                                with tag('button', klass='btn btn-outline-dark'):
                                    with tag('h4', klass='m-0'):
                                        text('Job list')

                        with tag('div', ('aria-labelledby', 'job_list___heading_1'),
                                 ('data-parent', '#job_list___accordion'),
                                 klass='collapse', id='job_list___collapse_1'):
                            with tag('div', klass='card-body'):
                                with tag('div', klass='text-right mb-1'):
                                    with tag('div', klass='mx-1', id='job_item_expand_all'):
                                        with tag('a',
                                                 href='#',
                                                 onclick="$('div.job_list___sub_multi_collapse').collapse('show');"):
                                            with tag('button', klass='btn btn-outline-dark'):
                                                with tag('span'):
                                                    text('Expand All')
                                    with tag('div', klass='mx-1', id='job_item_collapse_all'):
                                        with tag('a',
                                                 href='#',
                                                 onclick="$('div.job_list___sub_multi_collapse').collapse('hide');"):
                                            with tag('button', klass='btn btn-outline-dark'):
                                                with tag('span'):
                                                    text('Collapse All')

                                # Job item

                                for index, (work_item, result) in enumerate(all_items, start=1): # type: int, (WorkItem, WorkResult)
                                    if result is not None:
                                        if result.is_killed:
                                            if result.outcome == Outcome.INCOMPETENT:
                                                level = 'info'
                                            else:
                                                level = 'success'
                                                if skip_success:
                                                    continue
                                        else:
                                            level = 'danger'

                                    with tag('div', klass='mb-1', id='job_list___sub_accordion_{}'.format(index)):
                                        with tag('div', klass='card'):
                                            with tag('a', ('data-toggle', 'collapse'),
                                                     ('data-target', '#job_list___sub_collapse_{}_1'.format(index)),
                                                     ('aria-expanded', 'false'),
                                                     ('aria-controls', 'job_list___sub_collapse_{}_1'.format(index)),
                                                     href='#', klass='job_list___sub_multi_heading'):
                                                with tag('div', ('role', 'alert'),
                                                         klass='card-header alert-{}'.format(level),
                                                         id='job_list___sub_heading_{}_1'.format(index)):
                                                    with tag('button', klass='btn btn-outline-{}'.format(level)):
                                                        with tag('span', klass='job_id'):
                                                            text('{} : Job ID {}'.format(index, work_item.job_id))

                                            with tag('div',
                                                     ('aria-labelledby', 'job_list___sub_heading_{}_1'.format(index)),
                                                     ('data-parent', '#job_list___sub_accordion_{}'.format(index)),
                                                     klass='collapse job_list___sub_multi_collapse',
                                                     id='job_list___sub_collapse_{}_1'.format(index)):
                                                with tag('div', klass='card-body'):
                                                    with tag('div', klass='work-item'):
                                                        with tag('div',
                                                                 klass='alert alert-{} test-outcome'.format(level),
                                                                 role='alert'):
                                                            if result is not None:
                                                                if not result.is_killed:
                                                                    with tag('p'):
                                                                        text('SURVIVED')
                                                                with tag('p'):
                                                                    text('worker outcome: {}'.
                                                                         format(result.worker_outcome))
                                                                with tag('p'):
                                                                    text('test outcome: {}'.
                                                                         format(result.outcome))

                                                    with tag('pre', klass='location'):
                                                        with tag('a',
                                                                 href=_pycharm_url(
                                                                     work_item.module_path,
                                                                     work_item.start_pos[0]), klass='text-secondary'):
                                                            with tag('button', klass='btn btn-outline-dark'):
                                                                text('{}, start pos: {}, end pos: {}'.
                                                                     format(work_item.module_path, work_item.start_pos,
                                                                            work_item.end_pos))

                                                    with tag('pre'):
                                                        text('operator: {}, occurrence: {}'.
                                                             format(work_item.operator_name, work_item.occurrence))

                                                    if result is not None:
                                                        if work_item.diff:
                                                            with tag('div', klass='alert alert-secondary'):
                                                                with tag('pre', klass='diff'):
                                                                    text(work_item.diff)

                                                        if result.output:
                                                            with tag('div', klass='alert alert-secondary'):
                                                                with tag('pre', klass='diff'):
                                                                    text(result.output)

            with tag('script'):
                doc.attr(src='https://code.jquery.com/jquery-3.3.1.slim.min.js')
                doc.attr(('integrity', 'sha384-q8i/X+965DzO0rT7abK41JStQIAqVgRVzpbzo5smXKp4YfRvH+8abtTE1Pi6jizo'))
                doc.attr(('crossorigin', 'anonymous'))
            with tag('script'):
                doc.attr(src='https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js')
                doc.attr(('integrity', 'sha384-UO2eT0CpHqdSJQ6hJty5KVphtPhzWj9WO1clHTMGa3JDZwrnQq4sF86dIHNDz0W1'))
                doc.attr(('crossorigin', 'anonymous'))
            with tag('script'):
                doc.attr(src='https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js')
                doc.attr(('integrity', 'sha384-JjSmVgyd0p3pXB1rRibZUAYoIIy6OrQ6VrjIEaFf/nJGzIxFDsf4x0xIM+B07jRM'))
                doc.attr(('crossorigin', 'anonymous'))
            with tag('script', type='text/javascript'):
                doc.asis(
                    '$(\'div.job_list___sub_multi_collapse\').on(\'shown.bs.collapse\','
                    '  function () {'
                    '    correct_behavior_functional_buttons();'
                    '  });'

                    '$(\'div.job_list___sub_multi_collapse\').on(\'hidden.bs.collapse\','
                    '  function () {'
                    '    correct_behavior_functional_buttons();'
                    '  });'

                    'function correct_behavior_functional_buttons() {'
                    '    var expand = false;'
                    '    var collapse = false;'

                    '    $(\'a.job_list___sub_multi_heading\').each(function(index) {'
                    '      if ($(this).attr(\'aria-expanded\') == \'false\') {'
                    '        expand = true;'
                    '        return false;'
                    '      };'
                    '    });'

                    '    $(\'a.job_list___sub_multi_heading\').each(function(index) {'
                    '      if ($(this).attr(\'aria-expanded\') == \'true\') {'
                    '        collapse = true;'
                    '        return false;'
                    '      };'
                    '    });'

                    '    if (expand) {'
                    '      $(\'div#job_item_expand_all\').css(\'display\', \'inline-block\');'
                    '    } else {'
                    '      $(\'div#job_item_expand_all\').css(\'display\', \'none\');'
                    '    };'

                    '    if (collapse) {'
                    '      $(\'div#job_item_collapse_all\').css(\'display\', \'inline-block\');'
                    '    } else {'
                    '      $(\'div#job_item_collapse_all\').css(\'display\', \'none\');'
                    '    };'

                    '  };'

                    'correct_behavior_functional_buttons();'
                )

    return doc


def _pycharm_url(filename, line_number):
    """Get a URL for opening a file in Pycharm.
    """
    return 'pycharm://open?file={}&line={}'.format(filename, line_number)