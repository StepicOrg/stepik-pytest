from .exceptions import QueryError, TimeoutError


class Dig(object):
    def __init__(self, test_server, name_server):
        self.s = test_server
        self.name_server = name_server

    def __getattr__(self, query_type):
        def query(name, options='', split_lines=True):
            command = 'dig @{0} {1} {2} {3}'.format(self.name_server, name,
                                                    query_type.upper(),
                                                    options)
            r = self.s.run_local(command)
            if r.return_code != 0:
                if ";; connection timed out;" in r:
                    raise TimeoutError(r)
                raise QueryError(r)

            if split_lines:
                return r.splitlines()
            return r

        return query
