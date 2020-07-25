from lnurl.cli import LnRPC
from lnurl.types import LightningNodeUri
import requests
from enum import Enum

try:
    from typing import Mapping, Any, Optional  # type: ignore
except ImportError:  # pragma: nocover
    from typing_extensions import Mapping, Any, Optional  # type: ignore

class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"

class UnexpectedHttpStatusException(Exception):
    """Thrown when LND returns something else than 200"""

    status_code: int
    method: str
    error: Optional[str]

    def __init__(self, status_code: int, method, error: Optional[str]):
        self.status_code = status_code
        self.method = method
        self.error = error

        if self.error is None:
            super().__init__("Unexpected LND HTTP status: %d, method: %s" % (self.status_code, self.method))
        else:
            super().__init__("Unexpected LND HTTP status: %d, method: %s, error message: %s" % (self.status_code, self.method, self.error))

class LndRestRPC(LnRPC):
    """RPC handler using LND REST API"""

    _rest_address: str
    _session: requests.Session

    # We cache node ID because it doesn't change
    _node_id: Optional[str] = None

    def __init__(self, config: Mapping[str, Any]):
        self._rest_address = config["address"]

        # We load the file at init to catch possible errors ASAP and also
        # to avoid re-loading it if the same instance is used for multiple calls.
        with open(config["macaroon_file"], "rb") as macaroon_file:
            macaroon = macaroon_file.read().hex()

        headers = { "Grpc-Metadata-macaroon": macaroon }

        self._session = requests.Session()
        self._session.headers.update(headers)
        self._session.verify = config["tls_cert_file"]

    def _call(self, http_method: HTTPMethod, rpc_method: str, data: Optional[Mapping["str", Any]] = None):
        """Calls specific method of LND with given arguments"""

        url = "https://%s/v1/%s" % (self._rest_address, rpc_method)
        request = requests.Request(http_method.value, url, json=data)

        prepared = self._session.prepare_request(request)
        response = self._session.send(prepared)

        if response.status_code != 200:
            try:
                resp_json = response.json()
                error = resp_json["error"]
            except Exception:
                error = None

            raise UnexpectedHttpStatusException(response.status_code, rpc_method, error)

        return response.json()

    def close(self):
        self._session.close()

    def get_node_id(self) -> str:
        if self._node_id is None:
            self._node_id = self._call(HTTPMethod.GET, "getinfo")["identity_pubkey"]

        return self._node_id

    def connect(self, node: LightningNodeUri):
        if node.port is None:
            host = node.ip
        else:
            host = "%s:%s" % (node.ip, node.port)

        try:
            self._call(HTTPMethod.POST, "peers", { "addr": { "pubkey": node.key, "host": host }, "perm": False })
        except UnexpectedHttpStatusException as e:
            if e.error is None or not e.error.startswith("already connected to peer"):
                raise e
