import json
import mock
import pytest

from collections import OrderedDict
from io import StringIO

from stepic_pytest.plugin import ZoeReporter


ZOE_REPORT_PREFIX = u'\n##rootnroll_zoe'


class TestZoeReporter(object):
    @pytest.fixture
    def config(self):
        config = mock.MagicMock()
        config.option.zoe_report = True
        return config

    @pytest.fixture
    def reporter(self, config):
        output = StringIO()
        return ZoeReporter(config, output=output)

    def test_pytest_sessionfinish(self, reporter):
        assert not hasattr(reporter, '_exitstatus')
        reporter.pytest_sessionfinish(0)
        assert reporter._result == reporter.RESULT_PASSED
        reporter.pytest_sessionfinish(1)
        assert reporter._result == reporter.RESULT_FAILED

    def test_pytest_unconfigure(self, reporter, config):
        reporter._result = reporter.RESULT_PASSED
        with mock.patch.object(reporter, 'report_result') as report_result:
            config.option.zoe_report = False
            reporter.pytest_unconfigure(config)
            assert not report_result.called

            config.option.zoe_report = True
            reporter.pytest_unconfigure(config)
            report_result.assert_called_once_with(
                reporter.RESULT_PASSED,
                failed_tests=reporter._failed_tests,
                error=reporter._error
            )

    def test_report_result_passed(self, reporter):
        reporter.report_result(reporter.RESULT_PASSED)

        report_string = reporter.output.getvalue()
        assert report_string.startswith(ZOE_REPORT_PREFIX)
        assert report_string.endswith(u'\n')
        report = json.loads(report_string[len(ZOE_REPORT_PREFIX):])
        assert report['result'] == reporter.RESULT_PASSED

    def test_report_result_failed(self, reporter):
        failed_tests = OrderedDict()
        failed_tests[2] = "error message"
        failed_tests[10] = "other error message"

        reporter.report_result(reporter.RESULT_FAILED,
                               failed_tests=failed_tests)

        report_string = reporter.output.getvalue()
        assert report_string.startswith(ZOE_REPORT_PREFIX)
        assert report_string.endswith(u'\n')
        report = json.loads(report_string[len(ZOE_REPORT_PREFIX):])
        assert report['result'] == reporter.RESULT_FAILED
        expected_failed_tests = [
            {'number': 2, 'message': failed_tests[2]},
            {'number': 10, 'message': failed_tests[10]},
        ]
        assert report['failed_tests'] == expected_failed_tests

    def test_report_result_failed_with_error(self, reporter):
        reporter.report_result(reporter.RESULT_FAILED, error="internal error")

        report_string = reporter.output.getvalue()
        assert report_string.startswith(ZOE_REPORT_PREFIX)
        assert report_string.endswith(u'\n')
        report = json.loads(report_string[len(ZOE_REPORT_PREFIX):])
        assert report['result'] == reporter.RESULT_FAILED
        assert report['error'] == "internal error"
