try:
    from typing import Protocol
except ImportError:  # pragma: nocover
    from typing_extensions import Protocol # type: ignore

from lnurl.types import LightningNodeUri

class LnRPC(Protocol):
    """Protocol defining the interface with LN node implementations.
    
    Implementors of this protocol can be used to execute the LNURL actions.
    """

    def close(self):
        """Closes RPC session.

        All method calls after a call to this methods are invalid.

        Warning: do NOT confuse with closing a channel!
        """

    def get_node_id(self) -> str:
        """Returns the ID (hex-encoded public key) of the node"""

    def connect(self, node: LightningNodeUri):
        """Instructs the node to connect to a remote peer.
        
        Warning: Do NOT confuse with connecting to RPC server! Connecting to the
        RPC server is implementation-specific, this is a command for a node to
        connect to another node.
        """
