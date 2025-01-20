"""
Bitcoin RPC client library
~~~~~~~~~~~~~~~~~~~~~~~~~
Basic usage:

    >>> from bitcoinrpc import Bitcoin
    >>> client = Bitcoin(username="user", password="pass")
    >>> info = client.get_blockchain_info()
"""

from .Bitcoin import Bitcoin
from .Block import Block, Transaction, Input, Output, Script, BlockLite 

__version__ = "0.1.0"
__all__ = ["Bitcoin", "Block"]