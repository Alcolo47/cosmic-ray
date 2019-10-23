"""Classes for describing work and results.
"""
import enum
import json
import pathlib


class StrEnum(str, enum.Enum):
    """An Enum subclass with str values.
    """


class WorkerOutcome(StrEnum):
    """Possible outcomes for a worker.
    """
    NORMAL = 'normal'  # The worker exited normally, producing valid output
    EXCEPTION = 'exception'  # The worker exited with an exception
    ABNORMAL = 'abnormal'  # The worker did not exit normally or with an exception (e.g. a segfault)
    NO_TEST = 'no-test'  # The worker had no test to run
    SKIPPED = 'skipped'  # The job was skipped (worker was not executed)


class Outcome(StrEnum):
    """A enum of the possible outcomes for any mutant test run.
    """
    SURVIVED = 'survived'
    KILLED = 'killed'
    INCOMPETENT = 'incompetent'


class WorkResult:
    """The result of a single mutation and test run.
    """

    def __init__(self,
                 worker_outcome: WorkerOutcome,
                 output=None,
                 outcome: Outcome = None,
                 ):
        if worker_outcome is None:
            raise ValueError('Worker outcome must always have a value.')

        self.output = output
        self.outcome = outcome
        self.worker_outcome = worker_outcome

    def to_dict(self):
        return {
            'outcome': self.outcome.name,
            'worker_outcome': self.worker_outcome.name,
            'output': self.output,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            output=d['output'],
            outcome=Outcome[d['outcome']],
            worker_outcome=WorkerOutcome[d['worker_outcome']],
        )

    def as_dict(self):
        "Get the WorkResult as a dict."
        return {
            'output': self.output,
            'outcome': self.outcome,
            'worker_outcome': self.worker_outcome,
        }

    @property
    def is_killed(self):
        "Whether the mutation should be considered 'killed'"
        return self.outcome != Outcome.SURVIVED

    def __eq__(self, rhs):
        return self.as_dict() == rhs.as_dict()

    def __neq__(self, rhs):
        return not self == rhs

    def __repr__(self):
        return "<WorkResult {outcome}/{worker_outcome}: '{output}'>".format(
            outcome=self.outcome,
            worker_outcome=self.worker_outcome,
            output=self.output)


class WorkItem:
    """Description of the work for a single mutation and test run.
    """

    # pylint: disable=R0913
    def __init__(self,
                 job_id,
                 module_path,
                 operator_name,
                 occurrence,
                 start_pos,
                 end_pos,
                 diff=None,
            ):
        if start_pos[0] > end_pos[0]:
            raise ValueError('Start line must not be after end line')

        if start_pos[0] == end_pos[0]:
            if start_pos[1] >= end_pos[1]:
                raise ValueError('End position must come after start position.')

        self.job_id = job_id
        self.module_path = pathlib.Path(module_path)
        self.operator_name = operator_name
        self.occurrence = occurrence
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.diff = diff

    def as_dict(self):
        """Get fields as a dict.
        """
        return {
            'module_path': str(self.module_path),
            'operator_name': self.operator_name,
            'occurrence': self.occurrence,
            'start_pos': self.start_pos,
            'end_pos': self.end_pos,
            'diff': self.diff,
            'job_id': self.job_id,
        }

    def __eq__(self, rhs):
        return self.as_dict() == rhs.as_dict()

    def __str__(self):
        return "%s(%s)" % (self.operator_name, self.occurrence)

    def __repr__(self):
        return "<WorkItem {job_id}: ({start_pos}/{end_pos}) {occurrence} - {operator} ({module})>".format(
            job_id=self.job_id,
            start_pos=self.start_pos,
            end_pos=self.end_pos,
            occurrence=self.occurrence,
            operator=self.operator_name,
            module=self.module_path)


class WorkItemJsonEncoder(json.JSONEncoder):
    """Custom JSON encoder for workitems and workresults.
    """

    def default(self, o):  # pylint: disable=E0202
        if isinstance(o, WorkItem):
            return {"_type": "WorkItem", "values": o.as_dict()}

        if isinstance(o, WorkResult):
            return {"_type": "WorkResult", "values": o.as_dict()}

        return super().default(o)


class WorkItemJsonDecoder(json.JSONDecoder):
    """Custom JSON decoder for WorkItems and WorkResults.
    """

    def __init__(self):
        json.JSONDecoder.__init__(self, object_hook=self._decode_work_items)

    @staticmethod
    def _decode_work_items(obj):
        if (obj.get('_type') == 'WorkItem') and ('values' in obj):
            values = obj['values']
            return WorkItem(**values)

        if (obj.get('_type') == 'WorkResult') and ('values' in obj):
            values = obj['values']
            return WorkResult(**values)

        return obj
