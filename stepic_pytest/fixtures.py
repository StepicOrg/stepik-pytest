import logging

import cuisine
import pytest
import subprocess
import os

from functools import wraps

from fabric.api import env, execute, output
from fabric.network import disconnect_all

from .exceptions import AbortError


logger = logging.getLogger(__name__)

env.warn_only = True
env.abort_exception = AbortError
env.disable_known_hosts = True
output.commands = False


class Server(object):
    def __init__(self, ip):
        self.ip = ip

    def __getattr__(self, cuisine_func_name):
        try:
            cuisine_func = getattr(cuisine, cuisine_func_name)
        except AttributeError:
            raise AttributeError("Cuisine module has no function '{0}'"
                                 .format(cuisine_func_name))

        @wraps(cuisine_func)
        def func(*args, **kwargs):
            results = execute(cuisine_func, *args, host=self.ip, **kwargs)
            result = results[self.ip]
            logger.debug("[%s] command: '%s', return code: %s, output:\n%s",
                         self.ip, result.command, result.return_code, result)
            return result

        return func


class Localhost(object):

    class Str(str):
        pass

    def __init__(self):
        self.ip = '127.0.0.1'
        self.cwd = os.environ.get('HOME')

    def __getattr__(self, func):
        raise AttributeError(func + ' is not available for localhost')

    def run(self, cmd):
        out = ''
        succeeded = False
        try:
            out = subprocess.check_output(cmd, cwd=self.cwd, shell=True)
            succeeded = True
        except subprocess.CalledProcessError:
            pass
        res = self.Str(out)
        res.succeeded = succeeded
        return res



@pytest.fixture(scope='session')
def s(request):
    """Server to be checked."""
    ip = request.config.getoption('server_ip')
    if ip in ('127.0.0.1', 'localhost'):
        return Localhost()
    else:
        env.user = 'root'
        env.key_filename = request.config.getoption('ssh_key_path')
        request.addfinalizer(disconnect_all)
        return Server(ip)
