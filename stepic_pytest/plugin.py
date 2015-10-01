import json
import sys

from collections import OrderedDict

from _pytest.python import Module

from .exceptions import AbortError, QueryError, TimeoutError, WrongAnswer
from .fixtures import s


def pytest_addoption(parser):
    group = parser.getgroup("zoe check system", "zoe checker")
    group._addoption('-z', '--zoe', action='store_true', dest='zoe',
                     default=False,
                     help="enable zoe check system")
    group._addoption('--zoe-report', action='store_true', dest='zoe_report',
                     default=False, help="enable reporting in zoe format")
    group.addoption('--server', metavar='ip', dest='server_ip',
                    help="server IP address")
    group.addoption('--ssh-key', metavar='filepath', dest='ssh_key_path',
                    help="ssh private key of server")


def error(message):
    sys.stderr.write("zoe check system: error: {}\n".format(message))
    sys.exit(2)

def pytest_cmdline_main(config):
    if not config.option.zoe:
        return
    if not all((config.option.server_ip, config.option.ssh_key_path)):
        error("--server and --ssh-key are required arguments")


def pytest_configure(config):
    """Activate mal reporter."""
    if config.option.zoe:
        config.pluginmanager.register(ZoeReporter(config), 'zoereporter')


class ZoeReporter(object):
    REPORT_PREFIX = u'\n##rootnroll_zoe'
    RESULT_PASSED = 'passed'
    RESULT_FAILED = 'failed'

    def __init__(self, config, output=sys.stderr):
        self.config = config
        self.output = output
        self._result = None
        self._error = None
        self._failed_tests = OrderedDict()

    def pytest_collection_modifyitems(self, session, config, items):
        for number, item in enumerate(items, start=1):
            item.number = number

    def pytest_sessionfinish(self, exitstatus):
        if exitstatus == 0:
            self._result = self.RESULT_PASSED
        else:
            self._result = self.RESULT_FAILED

    def pytest_exception_interact(self, node, call, report):
        if isinstance(node, Module):
            self._error = "Test scenario contains errors"
            return
        exc = call.excinfo.value
        error_message = "Unknown error: {0}".format(exc)
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
            error_message = exc.message if exc.message else "Assertion error"
        self._failed_tests[node.number] = error_message

    def pytest_unconfigure(self, config):
        if config.option.zoe_report:
            self.report_result(self._result,
                               failed_tests=self._failed_tests,
                               error=self._error)

    def report_result(self, result, failed_tests=None, error=None):
        report = {'result': result}
        if error:
            report['error'] = error
        elif failed_tests:
            report['failed_tests'] = []
            for number, message in failed_tests.iteritems():
                test_info = dict(number=number, message=message)
                report['failed_tests'].append(test_info)

        self.output.write(self.REPORT_PREFIX)
        self.output.write(json.dumps(report).decode('utf8'))
        self.output.write(u'\n')
