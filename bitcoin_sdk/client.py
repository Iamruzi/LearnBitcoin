import requests

class BitcoinRPCError(Exception):
    def __init__(self, message, rpc_error_code=None):
        super().__init__(message)
        self.rpc_error_code = rpc_error_code

class BitcoinClient:
    def __init__(self, rpc_url, rpc_user, rpc_password):
        self.rpc_url = rpc_url
        self.rpc_user = rpc_user
        self.rpc_password = rpc_password
        self.session = requests.Session()
        self.session.auth = (self.rpc_user, self.rpc_password)

    def _rpc_request(self, method, params=None):
        payload = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params or [],
            'id': 'python-bitcoin-sdk'
        }
        try:
            response = self.session.post(self.rpc_url, json=payload, timeout=30)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        except requests.exceptions.RequestException as e:
            # Handle network errors or bad HTTP status codes
            raise requests.exceptions.RequestException(f"Error connecting to Bitcoin RPC: {e}")

        response_json = response.json()

        rpc_error = response_json.get('error')
        if rpc_error:
            raise BitcoinRPCError(
                message=rpc_error['message'],
                rpc_error_code=rpc_error['code']
            )

        return response_json.get('result')

    def get_block_count(self):
        return self._rpc_request("getblockcount")

    def get_block_hash(self, height):
        return self._rpc_request("getblockhash", [height])

    def get_block(self, block_hash, verbosity=1):
        return self._rpc_request("getblock", [block_hash, verbosity])

    def get_raw_transaction(self, txid, verbose=False):
        # Bitcoin Core expects 0 for non-verbose, 1 for verbose.
        return self._rpc_request("getrawtransaction", [txid, 1 if verbose else 0])

    def decode_raw_transaction(self, hex_string):
        return self._rpc_request("decoderawtransaction", [hex_string])

    def send_raw_transaction(self, hex_string):
        return self._rpc_request("sendrawtransaction", [hex_string])
