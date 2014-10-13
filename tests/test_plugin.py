import json
import mock
import pytest

from collections import OrderedDict

from stepic_pytest.malclient import CheckerJobStatus, CheckerJobResult
from stepic_pytest.plugin import MalReporter


class TestMalReporter(object):
    @pytest.fixture
    def config(self):
        config_mock = mock.MagicMock()
        config_mock.option.mal_job_id = 123
        config_mock.option.mal_api_url = 'http://example.com/api'
        config_mock.option.mal_username = 'checker_username'
        config_mock.option.mal_password = 'checker_password'
        return config_mock

    @pytest.fixture
    def reporter(self, config):
        return MalReporter(config)

    def test_pytest_sessionfinish(self, reporter):
        assert not hasattr(reporter, '_exitstatus')
        reporter.pytest_sessionfinish(0)
        assert reporter._result == CheckerJobResult.PASSED
        reporter.pytest_sessionfinish(1)
        assert reporter._result == CheckerJobResult.FAILED

    def test_pytest_unconfigure(self, reporter, config):
        reporter._result = CheckerJobResult.PASSED
        log = u'test1 PASSED\ntest2 PASSED\ntest3 FAILED'
        reporter._log_file.write(log)
        with mock.patch.object(reporter, 'report_result') as report_result:
            reporter.pytest_unconfigure(config)
            report_result.assert_called_once_with(CheckerJobResult.PASSED, log,
                                                  reporter._errors)

    @mock.patch('stepic_pytest.malclient.requests')
    def test_report_result_passed(self, mock_request, reporter):
        reporter.report_result(CheckerJobResult.PASSED,
                               '### pytest verbose log ###')

        mock_request.request.assert_called_once_with(
            'patch',
            'http://example.com/api/checker-jobs/123',
            headers={'Content-Type': 'application/json'},
            data=mock.ANY,
            auth=('checker_username', 'checker_password'))
        _, kwargs = mock_request.request.call_args
        expected_data = {
            'status': CheckerJobStatus.COMPLETED,
            'result': CheckerJobResult.PASSED,
            'log': '### pytest verbose log ###',
        }
        assert json.loads(kwargs['data']) == expected_data

    @mock.patch('stepic_pytest.malclient.requests')
    def test_report_result_failed(self, mock_request, reporter):
        errors = OrderedDict()
        errors[2] = "error message"
        errors[10] = "other error message"

        reporter.report_result(CheckerJobResult.FAILED,
                               '### pytest verbose log ###', errors)

        _, kwargs = mock_request.request.call_args
        expected_data = {
            'status': CheckerJobStatus.COMPLETED,
            'result': CheckerJobResult.FAILED,
            'log': '### pytest verbose log ###',
            'hint': "Test #2: error message",
        }
        assert json.loads(kwargs['data']) == expected_data
