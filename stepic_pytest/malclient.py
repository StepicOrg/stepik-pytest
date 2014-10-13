import json
import logging

import requests

from copy import copy


logger = logging.getLogger(__name__)


CHECKER_JOB_PATH = '/checker-jobs/{id}'


class CheckerJobStatus(object):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'


class CheckerJobResult(object):
    PASSED = 'passed'
    FAILED = 'failed'


class MalClient(object):
    def __init__(self, api_url, username, password):
        self.api_url = api_url
        self.auth = (username, password)
        self.headers = {'Content-Type': 'application/json'}

    def _resource_url(self, path, **kwargs):
        return (self.api_url + path).format(**kwargs)

    def request(self, method, url, **kwargs):
        logger.debug("MalClient request: %s %s | body: %s",
                     method.upper(), url, kwargs.get('data'))
        if 'data' in kwargs:
            kwargs['data'] = json.dumps(kwargs['data'])

        resp = requests.request(method, url, **kwargs)

        if not resp:
            logger.info("MalClient response: %s %s on request: %s %s | "
                        "body: %s", resp.status_code, resp.content,
                        method.upper(), url, kwargs.get('data'))
        else:
            logger.debug("MalClient response: %s %s on request: %s %s",
                         resp.status_code, resp.content, method.upper(), url)
        return resp

    def patch(self, url, data=None, **kwargs):
        return self.request('patch', url, data=data, **kwargs)

    def update_checker_job(self, id, **data):
        data_for_logger = copy(data)
        data_for_logger['log'] = '*** too long for info logger, truncated ***'
        logger.info("Updating checker job %s: %s", id, data_for_logger)

        job_url = self._resource_url(CHECKER_JOB_PATH, id=id)
        return self.patch(job_url, data=data,
                          headers=self.headers, auth=self.auth)


def malclient(celery_app):
    """Create a mal client for the given celery application."""
    return MalClient(celery_app.conf.MAL_API_URL,
                     celery_app.conf.MAL_CHECKER_USERNAME,
                     celery_app.conf.MAL_CHECKER_PASSWORD)
