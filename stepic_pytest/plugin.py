import logging
import sys

from collections import OrderedDict
from io import StringIO

from malclient import CheckerJobStatus, CheckerJobResult, MalClient

from .exceptions import AbortError, QueryError, TimeoutError, WrongAnswer
from .fixtures import s


logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    group = parser.getgroup("zoe check system", "zoe checker")
    group._addoption('-z', '--zoe', action='store_true', dest='zoe',
                     default=False,
                     help="enable zoe check system")
    group.addoption('--server', metavar='ip', dest='server_ip',
                    help="server IP address")
    group.addoption('--ssh-key', metavar='filepath', dest='ssh_key_path',
                    help="ssh private key of server")
    group.addoption('--mal-job', metavar='id', type=int, dest='mal_job_id',
                    help="checker job to update")
    group.addoption('--mal-api-url', metavar='url', dest='mal_api_url',
                    help="mal api url to send check results to")
    group.addoption('--mal-username', metavar='username', dest='mal_username',
                    help="mal api checker username")
    group.addoption('--mal-password', metavar='password', dest='mal_password',
                    help="mal api checker password")


def error(message):
    sys.stderr.write("zoe check system: error: {}\n".format(message))
    sys.exit(2)


def pytest_cmdline_main(config):
    if not config.option.zoe:
        return
    if not all((config.option.server_ip, config.option.ssh_key_path)):
        error("--server and --ssh-key are required arguments")
    if not config.option.mal_api_url:
        return
    if not all((config.option.mal_username, config.option.mal_password,
                config.option.mal_job_id)):
        error("--mal-job, --mal-username, --mal--password are required "
              "arguments when result reporting to a mal server is enabled "
              "(by specifying the --mal-api-url argument)")


def pytest_configure(config):
    """Activate mal reporter."""
    if config.option.zoe and config.option.mal_api_url:
        config.pluginmanager.register(MalReporter(config), 'malreporter')


class MalReporter(object):
    def __init__(self, config):
        self.config = config
        self._log_file = StringIO()
        self._result = None
        self._errors = OrderedDict()
        self._malclient = MalClient(self.config.option.mal_api_url,
                                    self.config.option.mal_username,
                                    self.config.option.mal_password)

    def pytest_collection_modifyitems(self, session, config, items):
        for item_id, item in enumerate(items, start=1):
            item.id = item_id

    def pytest_sessionstart(self, session):
        tr = self.config.pluginmanager.getplugin('terminalreporter')

        def redirect_terminal_write(s, **kwargs):
            self._log_file.write(s.decode('utf8'))

        tr._tw.write = redirect_terminal_write

    def pytest_sessionfinish(self, exitstatus):
        if exitstatus == 0:
            self._result = CheckerJobResult.PASSED
        else:
            self._result = CheckerJobResult.FAILED

    def pytest_exception_interact(self, node, call, report):
        exc = call.excinfo.value
        error_message = "Incorrect configuration"
        if isinstance(exc, AbortError):
            if "Network is unreachable" in exc.message:
                error_message = "Network is unreachable"
            else:
                error_message = "Internal check system error"
        elif isinstance(exc, TimeoutError):
            error_message = "Timeout error"
        elif isinstance(exc, QueryError):
            error_message = "Service query error"
        elif isinstance(exc, WrongAnswer):
            error_message = "Wrong answer"
        elif isinstance(exc, AssertionError):
            error_message = exc.message if exc.message else "Failed"
        # TODO: INTERNALERROR>   File "/app/zoe/pytest_plugin.py", line 103, in pytest_exception_interact
        #       INTERNALERROR>     self._errors[node.id] = error_message
        #       INTERNALERROR> AttributeError: 'Module' object has no attribute 'id'
        self._errors[node.id] = error_message

    def pytest_unconfigure(self, config):
        tr = config.pluginmanager.getplugin('terminalreporter')
        tr._tw.__dict__.pop('write', None)

        log = self._log_file.getvalue()
        self.report_result(self._result, log, self._errors)

    def report_result(self, result, log, errors=None):
        job_id = self.config.option.mal_job_id
        logger.info("Reporting result for checker job %s: %s, errors: %s",
                    job_id, result, errors)
        logger.debug(log)

        data = {
            'status': CheckerJobStatus.COMPLETED,
            'result': result,
            'log': log,
        }
        if errors:
            test_id, error_message = next(errors.iteritems())
            data['hint'] = "Test #{0}: {1}".format(test_id, error_message)
            logger.info("Hint for checker job %s: %s", job_id, data['hint'])

        r = self._malclient.update_checker_job(job_id, **data)
        if r.status_code == 200:
            logger.info("Result for checker job %s has been successfully "
                        "reported to mal", job_id)
        else:
            logger.error("Failed to report result for checker job %s: %s %s",
                         job_id, r.status_code, r.text)
