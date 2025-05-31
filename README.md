# Python Bitcoin SDK

A Python SDK for interacting with a Bitcoin node via RPC.

## Installation

You can install the SDK using pip (once it's packaged and published). For now, you can include it directly in your project.

Make sure you have the `requests` library installed:
```bash
pip install requests
```

## Configuration

To use the SDK, you need to initialize the `BitcoinClient` with your Bitcoin node's RPC credentials:

```python
from bitcoin_sdk.client import BitcoinClient, BitcoinRPCError
import requests # Import for requests.exceptions.RequestException

rpc_url = "http://your_rpc_user:your_rpc_password@your_node_ip:your_node_port"
# Example for a local Bitcoin Core node with default regtest settings:
# rpc_url = "http://rpcuser:rpcpassword@127.0.0.1:18443"
# For mainnet, the default port is 8332. For testnet, it's 18332.

client = BitcoinClient(
    rpc_url="http://myuser:mypassword@127.0.0.1:8332", # Replace with your actual URL
    rpc_user="myuser",        # Replace with your RPC username
    rpc_password="mypassword" # Replace with your RPC password
)
```
**Note:** The `rpc_user` and `rpc_password` are passed separately in the `BitcoinClient` constructor for authentication with the `requests` library session, even though they might also be part of the `rpc_url`.

## Usage Examples

Here are some examples of how to use the SDK:

```python
try:
    # Get Block Count
    block_count = client.get_block_count()
    print(f"Current block count: {block_count}")

    # Get Block Hash by Height
    block_hash = client.get_block_hash(height=block_count)
    print(f"Hash of block {block_count}: {block_hash}")

    # Get Block Information by Hash
    block_info = client.get_block(block_hash=block_hash)
    print(f"Information for block {block_hash}: {block_info['hash']}") # Access elements like a dict

    # Example: Get a specific transaction (replace with a real txid)
    # txid = "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16" # Example TXID
    # if txid != "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16": # Avoid running with placeholder
    #     raw_tx_hex = client.get_raw_transaction(txid)
    #     print(f"Raw transaction (hex): {raw_tx_hex[:64]}...") # Print first 64 chars

    #     raw_tx_json = client.get_raw_transaction(txid, verbose=True)
    #     print(f"Raw transaction (JSON): {raw_tx_json['txid']}")

    # Decode a raw transaction (replace with actual raw hex)
    # sample_raw_tx_hex = "0100000001..." # A very long string
    # if sample_raw_tx_hex != "0100000001...": # Avoid running with placeholder
    #     decoded_tx = client.decode_raw_transaction(sample_raw_tx_hex)
    #     print(f"Decoded transaction: {decoded_tx['txid']}")

    # Sending a raw transaction (use with extreme caution!)
    # signed_tx_hex = "02000000..." # A fully signed raw transaction hex
    # if signed_tx_hex != "02000000...": # Avoid running with placeholder
    #     sent_txid = client.send_raw_transaction(signed_tx_hex)
    #     print(f"Transaction sent, TXID: {sent_txid}")

except BitcoinRPCError as e:
    print(f"Bitcoin RPC Error: {e.message} (Code: {e.rpc_error_code})")
except requests.exceptions.RequestException as e:
    print(f"Request Error (e.g., network issue): {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
```

## Error Handling

The SDK handles two main types of errors:
- `requests.exceptions.RequestException`: For network-related issues (e.g., connection timeout, DNS failure).
- `bitcoin_sdk.client.BitcoinRPCError`: For errors returned by the Bitcoin node's RPC API. This exception has `message` and `rpc_error_code` attributes.

It's recommended to wrap SDK calls in `try...except` blocks as shown in the examples.

## Implemented API Calls

- `get_block_count()`
- `get_block_hash(height)`
- `get_block(block_hash, verbosity=1)`
- `get_raw_transaction(txid, verbose=False)`
- `decode_raw_transaction(hex_string)`
- `send_raw_transaction(hex_string)`
