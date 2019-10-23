"""This is the command-line program for cosmic ray.

Here we manage command-line parsing and launching of the internal machinery that does mutation testing.
"""
import json
import logging
import os
import signal
import subprocess
import sys
import docopt
import docopt_subcommands
from docopt_subcommands.subcommands import Subcommands
from exit_codes import ExitCode

from cosmic_ray.db.work_db import use_db, WorkDB
from cosmic_ray.utils.config import load_config, root_config, serialize_config, \
    ConfigError
from cosmic_ray.utils.progress import report_progress
from cosmic_ray.version import __version__


log = logging.getLogger(__name__)


DOC_TEMPLATE = """{program}

Usage: {program} [options] <command> [<args> ...]

Options:
  -h --help           Show this screen.
  --version           Show the program version.
  -v --verbosity=LEVEL  Use verbose output [default: WARNING]

Available commands:
  {available_commands}

See '{program} <command> -h' for help on specific commands.
"""


class CosmicRaySubcommands(Subcommands):
    """Subcommand handler.
    """

    def _precommand_option_handler(self, config):
        verbosity_level = getattr(logging, config.get('--verbosity', 'WARNING'))

        logging.basicConfig(
            level=verbosity_level,
            format='%(asctime)s %(name)s %(levelname)s %(message)s')

        return super()._precommand_option_handler(config)


dsc = CosmicRaySubcommands(
    program='cosmic-ray',
    version='Cosmic Ray {}'.format(__version__),
    doc_template=DOC_TEMPLATE,
)


@dsc.command()
def handle_new_config(args):
    """usage: cosmic-ray new-config <config-file>

    Create a new config file.
    """
    from cosmic_ray.commands.new_config import new_config

    config = new_config()
    config_str = serialize_config(config)
    with open(args['<config-file>'], mode='wt') as handle:
        handle.write(config_str)

    return ExitCode.OK


def _get_session_file(args):
    config_file = args['<config-file>']
    session_file = args.get('--session')

    # Get absoklute path because we will do chdir
    if session_file:
        session_file = os.path.abspath(session_file)
    config_file = os.path.abspath(config_file)

    # Go to config file directoory (to read relative path relatively to config file.
    os.chdir(os.path.dirname(config_file))

    load_config(config_file)

    if session_file:
        root_config['session-file'] = session_file
    else:
        session_file = root_config['session-file']

    return session_file


@dsc.command()
def handle_run(args):
    """usage: cosmic-ray run [--session=<session-file>] <config-file>

    Initialize a mutation testing session from a configuration. This
    primarily creates a session - a database of "work to be done" -
    which describes all of the mutations and test runs that need to be
    executed for a full mutation testing run. The configuration
    specifies the top-level module to mutate, the tests to run, and how
    to run them.

    This command doesn't actually run any tests. Instead, it scans the
    modules-under-test and simply generates the work order which can be
    executed with other commands.

    The `session-file` is the filename for the database in which the
    work order will be stored.
    """
    from cosmic_ray.utils.modules import get_module_list
    from cosmic_ray.commands.run import Run

    session_file = _get_session_file(args)

    module_path = root_config['module-path']
    exclude_modules = root_config['exclude-modules']

    modules = get_module_list(exclude_modules, module_path)
    with use_db(session_file) as work_db:
        return Run(work_db).run(modules)


@dsc.command()
def handle_badge(args):
    """usage: cosmic-ray badge [--session=<session-file>] [--output=<badge-file>] <config-file>

Generate badge file.

options:
    --config <config-file> Configuration file to use instead of session configuration
    """
    from cosmic_ray.commands.badge import generate_badge

    session_file = _get_session_file(args)
    badge_filename = args.get('--output')

    with use_db(session_file, WorkDB.Mode.open) as work_db:
        generate_badge(work_db, badge_filename)


@dsc.command()
def handle_html(args):
    """usage: cosmic-ray html [--only-completed] [--skip-success] [--session=<session-file>] [--output=<output-file>] <config-file>

Print an HTML formatted report of test results.
    """
    from cosmic_ray.commands.html import generate_html_report, report_html_config

    session_file = _get_session_file(args)
    only_completed = args['--only-completed']
    skip_sucess = args['--skip-success']
    output_filename = args.get('--output')
    if not output_filename:
        output_filename = report_html_config['output']

    with use_db(session_file, WorkDB.Mode.open) as work_db:
        doc = generate_html_report(work_db, only_completed, skip_sucess)

    dir = os.path.dirname(output_filename)
    if dir:
        os.makedirs(dir, exist_ok=True)

    with open(output_filename, 'w') as output:
        output.write(doc.getvalue())


@dsc.command()
def handle_xml(args):
    """usage: cosmic-ray xml [--session=<session-file>] <config-file>

Print an XML formatted report of test results for continuous integration systems
    """
    from cosmic_ray.commands.xml import generate_xml_report

    session_file = _get_session_file(args)
    with use_db(session_file, WorkDB.Mode.open) as work_db:
        xml_elem = generate_xml_report(work_db)
        xml_elem.write(sys.stdout.buffer, encoding='utf-8', xml_declaration=True)


@dsc.command()
def handle_report(args):
    """usage: cosmic-ray report [--show-output] [--show-diff] [--show-pending] [--session=<session-file>] <config-file>

Print a nicely formatted report of test results and some basic statistics.

options:
    --show-output   Display output of test executions
    --show-diff     Display diff of mutants
    --show-pending  Display results for incomplete tasks
    """
    from cosmic_ray.commands.report import print_report

    session_file = _get_session_file(args)
    show_pending = args['--show-pending']
    show_output = args['--show-output']
    show_diff = args['--show-diff']

    if not session_file:
        session_file = root_config['session-file']

    with use_db(session_file, WorkDB.Mode.open) as work_db:
        print_report(work_db,
                     show_output=show_output,
                     show_diff=show_diff,
                     show_pending=show_pending)


@dsc.command()
def handle_survival_rate(args):
    """usage: cosmic-ray rate [--session=<session-file>] <config-file>

    Calculate the survival rate of a session.
    """
    from cosmic_ray.utils.survival_rate import survival_rate

    session_file = _get_session_file(args)
    with use_db(session_file, WorkDB.Mode.open) as work_db:
        rate = survival_rate(work_db)
        print('{:.2f}'.format(rate))


@dsc.command()
def handle_config(args):
    """usage: cosmic-ray config <session-file>

    Show the configuration for in a session.
    """
    session_file = args['<session-file>']
    with use_db(session_file) as database:
        config = database.get_config()
        print(serialize_config(config))

    return ExitCode.OK


@dsc.command()
def handle_dump(args):
    """usage: cosmic-ray dump <session-file>

    JSON dump of session data. This output is typically run through other
    programs to produce reports.

    Each line of output is a list with two elements: a WorkItem and a
    WorkResult, both JSON-serialized. The WorkResult can be null, indicating a
    WorkItem with no results.
    """
    from cosmic_ray.db.work_item import WorkItemJsonEncoder

    session_file = _get_session_file(args)

    with use_db(session_file, WorkDB.Mode.open) as work_db:
        for work_item, result in work_db.completed_work_items:
            print(json.dumps((work_item, result), cls=WorkItemJsonEncoder))
        for work_item in work_db.pending_work_items:
            print(json.dumps((work_item, None), cls=WorkItemJsonEncoder))

    return ExitCode.OK


@dsc.command()
def handle_operators(args):
    """usage: {program} operators

    List the available operator plugins.
    """
    from cosmic_ray.operators import operators

    print('\n'.join(operators.keys()))

    return ExitCode.OK


@dsc.command()
def handle_execution_engines(args):
    """usage: {program} execution-engines

    List the available execution-engine plugins.
    """
    from cosmic_ray.execution_engines import execution_engines

    print('\n'.join(execution_engines.keys()))

    return ExitCode.OK


@dsc.command()
def handle_interceptors(args):
    """usage: {program} interceptors

    List the available interceptor plugins.
    """

    from cosmic_ray.interceptors import interceptors

    print('\n'.join(interceptors.keys()))

    return ExitCode.OK


DOC_TEMPLATE = """{program}

Usage: {program} [options] <command> [<args> ...]

Options:
  -h --help     Show this screen.
  -v --verbose  Use verbose logging

Available commands:
  {available_commands}

See '{program} help <command>' for help on specific commands.
"""


_SIGNAL_EXIT_CODE_BASE = 128


def main(argv=None):
    """ Invoke the cosmic ray evaluation.

    :param argv: the command line arguments
    """
    signal.signal(signal.SIGINT, lambda *args: sys.exit(_SIGNAL_EXIT_CODE_BASE + signal.SIGINT))

    if hasattr(signal, 'SIGINFO'):
        signal.signal(getattr(signal, 'SIGINFO'), lambda *args: report_progress(sys.stderr))

    try:
        return docopt_subcommands.main(
            commands=dsc,
            argv=argv,
            doc_template=DOC_TEMPLATE,
            exit_at_end=False
        )

    except docopt.DocoptExit as exc:
        print(exc, file=sys.stderr)
        return ExitCode.USAGE

    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return ExitCode.NO_INPUT

    except PermissionError as exc:
        print(exc, file=sys.stderr)
        return ExitCode.NO_PERM

    except ConfigError as exc:
        print(repr(exc), file=sys.stderr)
        if exc.__cause__ is not None:
            print(exc.__cause__, file=sys.stderr)
        return ExitCode.CONFIG

    except subprocess.CalledProcessError as exc:
        print('Error in subprocess', file=sys.stderr)
        print(exc, file=sys.stderr)
        return exc.returncode


if __name__ == '__main__':
    sys.exit(main())
