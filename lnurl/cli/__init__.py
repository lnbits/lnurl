import sys
import pkg_resources
from contextlib import contextmanager
from lnurl.models import LnurlResponseModel, LnurlChannelResponse, LnurlSuccessResponse, LnurlErrorResponse
from lnurl.exceptions import LnurlException, LnurlResponseException
from lnurl.core import handle as handle_lnurl
from lnurl.core import get as get_lnurl
from lnurl.cli.lnrpc import LnRPC
import click
import toml
from typing import Generator

try:
    from typing import Mapping, Any  # type: ignore
except ImportError:  # pragma: nocover
    from typing_extensions import Mapping, Any  # type: ignore

class Context:
    """Contains RPC handler with settings"""

    # 0 - public, 1 - private, public by default
    _channel_type: int = 0
    _rpc: LnRPC

    def __init__(self, rpc: LnRPC):
        self._rpc = rpc

    def load_settings(self, config: Mapping[str, Any]):
        """Loads settings from a dictionary

        So far there's only one setting: private_channels: bool
        """

        try:
            if config["private_channels"]:
                self._channel_type = 1
        except KeyError:
            pass

    def handle_url(self, url: str):
        """Processes given LNURL"""

        if url.startswith("lightning:"):
            url = url[len("lightning"):]
        elif url.startswith("lnurl"):
            url = url[len("lnurl"):]

        response = handle_lnurl(url)
        self._dispatch(response)

    def _dispatch(self, response: LnurlResponseModel):
        """Decides following steps based on the response"""

        if isinstance(response, LnurlChannelResponse):
            self._accept_channel(response)
        elif isinstance(response, LnurlErrorResponse):
            raise LnurlException("Error returned by the LNURL server: %s" % response.reason)

        raise LnurlException("Error: LNURL subprotocol %s not implemented" % type(response).__name__)

    def _accept_channel(self, response: LnurlChannelResponse):
        """Handles accepting a channel"""

        node_id = self._rpc.get_node_id()
        callback = response.callback
        query = "k1=%s&remoteid=%s&private=%d" % (response.k1, node_id, self._channel_type)

        if callback.query is None:
            new_uri = "%s?%s" % (callback, query)
        else:
            new_uri = "%s&%s" % (callback, query)

        self._rpc.connect(response.uri)
        result = get_lnurl(new_uri)

        if isinstance(result, LnurlErrorResponse):
            raise LnurlResponseException("Failed to accept a channel: %s" % result.reason)
        if not isinstance(result, LnurlSuccessResponse):
            raise LnurlResponseException("Error: Unexpected result from the server")

    def close(self):
        """Closes all associated resources"""

        self._rpc.close()

def _load_rpc_entry_point(rpc_proto: str):
    """Loads entry point for given RPC protocol"""

    entry_points = pkg_resources.iter_entry_points("lnurl.rpc_handlers", rpc_proto)
    try:
        handler_entry_point = next(entry_points)
        return handler_entry_point.load()
    except StopIteration:
        raise LnurlException("Unknown LN RPC protocol: %s" % rpc_proto)

    # Warn the user if more than one RPC implementation exists
    try:
        next(entry_points)
        print("Warning: more than one implementation for %s exists, picking the first one" % rpc_proto, file=sys.stderr)
    except StopIteration:
        pass

@contextmanager
def _get_config(file_name: str) -> Generator[Context, None, None]:
    with open(file_name, "r") as config_file:
        config = toml.load(config_file)

    rpc_proto = config["rpc_proto"]

    rpc = _load_rpc_entry_point(rpc_proto)(config["rpc"])

    context = Context(rpc)

    try:
        context.load_settings(config)
        yield context
    finally:
        context.close()

@click.command()
@click.option("--config", help="Configuration file path", required=True)
# Can't figure out how to detect if this option was present, so keeping it
# commented to not confuse the users
#@click.option("--private-channels", "channel_type", help="Request accepted channels to be private", flag_value = 1)
#@click.option("--public-channels", "channel_type", help="Request accepted channels to be public. This is the default.", flag_value = 0)
def lnurl(config: str):
    """Entry point - the lnurl command"""

    had_errors = False
    try:
        with _get_config(config) as context:
            for line in sys.stdin.readlines():
                url = line.strip()
                try:
                    context.handle_url(url)
                except Exception as exception:
                    print("Failed to handle URL %s: %s" % (url, str(exception)), file=sys.stderr)
                    had_errors = True

    except Exception as exception:
        print("Failed to load configuration: %s" % str(exception), file=sys.stderr)
        had_errors = True

    if had_errors:
        sys.exit(1)
