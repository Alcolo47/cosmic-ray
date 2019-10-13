"""A tool for creating XML reports.
"""

import xml.etree.ElementTree

from cosmic_ray.db.work_item import Outcome, WorkerOutcome


def generate_xml_report(db):
    errors = 0
    failed = 0
    skipped = 0
    root_elem = xml.etree.ElementTree.Element('testsuite')

    for work_item, result in db.completed_work_items:
        if result.worker_outcome in {
                WorkerOutcome.EXCEPTION, WorkerOutcome.ABNORMAL
        }:
            errors += 1
        if result.is_killed:
            failed += 1
        if result.worker_outcome == WorkerOutcome.SKIPPED:
            skipped += 1

        sub_element = _create_element_from_work_item(work_item)
        sub_element = _update_element_with_result(sub_element, result)
        root_elem.append(sub_element)

    for work_item in db.pending_work_items:
        sub_element = _create_element_from_work_item(work_item)
        root_elem.append(sub_element)

    root_elem.set('errors', str(errors))
    root_elem.set('failures', str(failed))
    root_elem.set('skips', str(skipped))
    root_elem.set('tests', str(db.num_work_items))
    return xml.etree.ElementTree.ElementTree(root_elem)


def _create_element_from_work_item(work_item):
    sub_elem = xml.etree.ElementTree.Element('testcase')

    sub_elem.set('classname', work_item.job_id)
    sub_elem.set('line', str(work_item.start_pos[0]))
    sub_elem.set('file', str(work_item.module_path))

    return sub_elem


def _update_element_with_result(sub_elem, result):
    data = result.output
    outcome = result.worker_outcome

    if outcome == WorkerOutcome.EXCEPTION:
        error_elem = xml.etree.ElementTree.SubElement(sub_elem, 'error')
        error_elem.set('message', "Worker has encountered exception")
        error_elem.text = str(data) + "\n".join(result.diff)
    elif _evaluation_success(result):
        failure_elem = xml.etree.ElementTree.SubElement(sub_elem, 'failure')
        failure_elem.set('message', "Mutant has survived your unit tests")
        failure_elem.text = str(data) + result.diff

    return sub_elem


def _evaluation_success(result):
    return result.worker_outcome == WorkerOutcome.NORMAL and \
        result.outcome in {Outcome.SURVIVED, Outcome.INCOMPETENT}
