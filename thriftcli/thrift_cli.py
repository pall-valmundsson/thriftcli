import argparse
import json
import os

from .thrift_argument_converter import ThriftArgumentConverter
from .thrift_cli_error import ThriftCLIError
from .thrift_executor import ThriftExecutor
from .thrift_parser import ThriftParser

__version__ = '0.0.1'


class ThriftCLI(object):
    """ Provides an interface for setting up a client, making requests, and cleaning up.

    Call init to open a connection with a server and inform ThriftCLI of the available endpoints.
    Call run to make a request.
    Call cleanup to close the connection and delete the generated python code.
    """

    def __init__(self, thrift_path, server_address, thrift_dir_paths=None):
        """
        :param thrift_path: The path to the thrift file being used.
        :type thrift_path: str
        :param thrift_dir_paths: Additional directories to search for included thrift files in.
        :type thrift_dir_paths: list of str
        :param server_address: The address of the server to make requests to.
        :type server_address: str

        """
        self._thrift_path = thrift_path
        self._thrift_argument_converter = ThriftArgumentConverter(thrift_path, thrift_dir_paths)
        self._thrift_executor = ThriftExecutor(thrift_path, server_address, thrift_dir_paths)

    def run(self, endpoint, request_body):
        """ Runs the endpoint on the connected server as defined by the thrift file.

        :param endpoint: The name of the endpoint to ask the server to run.
        :type endpoint: str
        :param request_body: The arguments to provide as arguments to the endpoint.
        :type request_body: dict
        :returns: endpoint result

        """
        (service_name, method_name) = ThriftCLI._split_endpoint(endpoint)
        service_reference = '%s.%s' % (ThriftParser.get_package_name(self._thrift_path), service_name)
        request_args = self._thrift_argument_converter.convert_args(service_reference, method_name, request_body)
        return self._thrift_executor.run(service_reference, method_name, request_args)

    def cleanup(self, remove_generated_src=False):
        """ Deletes the gen-py code and closes the transport with the server. """
        self._thrift_executor.cleanup(remove_generated_src)

    @staticmethod
    def _split_endpoint(endpoint):
        """ Extracts the service name and method name from an endpoint. """
        split = endpoint.split('.')
        if not split or len(split) != 2:
            raise ThriftCLIError('Endpoint should be in format \'Service.function\', given: \'%s\'' % endpoint)
        return split


def _load_file(path):
    """ Returns the contents of a file. """
    with open(path, 'r') as file_to_read:
        return file_to_read.read()


def _load_request_body_from_path(request_body_path):
    """ Parses file content into JSON. """
    try:
        content = _load_file(request_body_path)
        return json.loads(content)
    except ValueError as e:
        raise ThriftCLIError('Request body file contains invalid JSON.', e.message)


def _load_request_body(request_body_arg):
    """ Parses the request body argument as either a JSON string or as a path to a JSON file. """
    if not request_body_arg:
        return {}
    elif os.path.isfile(request_body_arg):
        return _load_request_body_from_path(request_body_arg)
    try:
        return json.loads(request_body_arg)
    except ValueError:
        raise ThriftCLIError('Invalid JSON arg - not a path to JSON file and not a valid JSON string.\n' +
                             'Note that double quotes need to be escaped in bash.')


def _parse_namespace(args):
    """ Converts the namespace object returned by argparse into the desired variables. """
    server_address = args.server_address
    endpoint = args.endpoint
    thrift_path = args.thrift_path
    thrift_dir_paths = args.include
    request_body = _load_request_body(args.body)
    return server_address, endpoint, thrift_path, thrift_dir_paths, request_body


def _make_parser():
    """ Initializes the ArgumentParser with all desired arguments. """
    parser = argparse.ArgumentParser(description='Execute thrift endpoints on a running server.')
    parser.add_argument('server_address', type=str,
                        help='address of running server that implements the endpoint')
    parser.add_argument('endpoint', type=str,
                        help='name of endpoint, defined as Service.function')
    parser.add_argument('thrift_path', type=str,
                        help='path to thrift file declaring the endpoint')
    parser.add_argument('-I', '--include', type=str, nargs='*', default=[],
                        help='path to directory containing included thrift files')
    parser.add_argument('-b', '--body', type=str, nargs='?',
                        help='json string or path to json file encoding the request body')
    return parser


def _run_cli(server_address, endpoint_name, thrift_path, thrift_dir_paths, request_body, remove_generated_src=False):
    """ Runs a remote request and prints the result if it is not None. """
    cli = ThriftCLI(thrift_path, server_address, thrift_dir_paths)
    try:
        result = cli.run(endpoint_name, request_body)
        if result is not None:
            print result
    finally:
        cli.cleanup(remove_generated_src)


def _parse_args():
    """ Creates an ArgumentParser, parses sys.argv, and returns the desired arguments. """
    parser = _make_parser()
    namespace = parser.parse_args()
    return _parse_namespace(namespace)


def main():
    """ Runs a remote request and prints the result if it is not None. """
    args = _parse_args()
    _run_cli(*args)