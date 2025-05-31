import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from requests.exceptions import RequestException, Timeout
from bitcoin_sdk.client import BitcoinClient, BitcoinRPCError

class TestBitcoinClient(unittest.TestCase):

    def setUp(self):
        # The rpc_url in the client constructor is not actually used for connection in tests
        # as we mock session.post. However, the user/pass part is used for session.auth.
        self.client = BitcoinClient("http://localhost:8332", "testuser", "testpass")

    @patch('requests.Session.post')
    def test_get_block_count_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': 123456, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_block_count()
        self.assertEqual(result, 123456)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getblockcount')
        self.assertEqual(kwargs['json']['params'], [])
        self.assertEqual(kwargs['timeout'], 30) # Check default timeout

    @patch('requests.Session.post')
    def test_get_block_count_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200 # RPC error is a 200 OK with error in JSON
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -5, 'message': 'Block not found'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_block_count()
        self.assertEqual(context.exception.rpc_error_code, -5)
        self.assertIn('Block not found', str(context.exception))
        mock_post.assert_called_once()

    @patch('requests.Session.post')
    def test_get_block_count_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Connection timed out")

        with self.assertRaises(RequestException) as context: # Parent class for Timeout
            self.client.get_block_count()
        self.assertIn("Connection timed out", str(context.exception))
        mock_post.assert_called_once()

    # Tests for get_block_hash
    @patch('requests.Session.post')
    def test_get_block_hash_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': '0000000000000000000abcdeffedcba01234567890abcdef0123456789abcdef',
            'error': None,
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        height = 123456
        result = self.client.get_block_hash(height)
        self.assertEqual(result, '0000000000000000000abcdeffedcba01234567890abcdef0123456789abcdef')
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getblockhash')
        self.assertEqual(kwargs['json']['params'], [height])

    @patch('requests.Session.post')
    def test_get_block_hash_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -8, 'message': 'Block height out of range'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_block_hash(999999999) # Invalid height
        self.assertEqual(context.exception.rpc_error_code, -8)
        self.assertIn('Block height out of range', str(context.exception))

    @patch('requests.Session.post')
    def test_get_block_hash_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network issue")

        with self.assertRaises(RequestException):
            self.client.get_block_hash(123456)

    # Tests for get_block
    @patch('requests.Session.post')
    def test_get_block_success(self, mock_post):
        mock_block_data = {'hash': 'some_block_hash', 'height': 123, 'tx': ['tx1', 'tx2']}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': mock_block_data,
            'error': None,
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        block_hash = 'some_block_hash'
        result = self.client.get_block(block_hash) # Default verbosity = 1
        self.assertEqual(result, mock_block_data)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getblock')
        self.assertEqual(kwargs['json']['params'], [block_hash, 1])

    @patch('requests.Session.post')
    def test_get_block_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -5, 'message': 'Block not found'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_block('non_existent_hash')
        self.assertEqual(context.exception.rpc_error_code, -5)
        self.assertIn('Block not found', str(context.exception))

    @patch('requests.Session.post')
    def test_get_block_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Timeout getting block")

        with self.assertRaises(RequestException): # Parent class for Timeout
            self.client.get_block('some_block_hash')

    # Tests for get_raw_transaction
    @patch('requests.Session.post')
    def test_get_raw_transaction_success_non_verbose(self, mock_post):
        mock_hex_tx = "0100000001abcdef..."
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_hex_tx, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        txid = "some_txid"
        result = self.client.get_raw_transaction(txid, verbose=False)
        self.assertEqual(result, mock_hex_tx)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getrawtransaction')
        self.assertEqual(kwargs['json']['params'], [txid, 0])

    @patch('requests.Session.post')
    def test_get_raw_transaction_success_verbose(self, mock_post):
        mock_verbose_tx = {'txid': 'some_txid', 'hex': '0100000001abcdef...', 'confirmations': 100}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_verbose_tx, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        txid = "some_txid"
        result = self.client.get_raw_transaction(txid, verbose=True)
        self.assertEqual(result, mock_verbose_tx)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getrawtransaction')
        self.assertEqual(kwargs['json']['params'], [txid, 1])

    @patch('requests.Session.post')
    def test_get_raw_transaction_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -5, 'message': 'No such mempool or blockchain transaction.'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_raw_transaction('non_existent_txid')
        self.assertEqual(context.exception.rpc_error_code, -5)
        self.assertIn('No such mempool or blockchain transaction.', str(context.exception))

    @patch('requests.Session.post')
    def test_get_raw_transaction_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network issue")

        with self.assertRaises(RequestException):
            self.client.get_raw_transaction('some_txid')

    # Tests for decode_raw_transaction
    @patch('requests.Session.post')
    def test_decode_raw_transaction_success(self, mock_post):
        mock_decoded_tx = {'txid': 'decoded_txid', 'vin': [], 'vout': []}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_decoded_tx, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        hex_string = "0100000001fedcba..."
        result = self.client.decode_raw_transaction(hex_string)
        self.assertEqual(result, mock_decoded_tx)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'decoderawtransaction')
        self.assertEqual(kwargs['json']['params'], [hex_string])

    @patch('requests.Session.post')
    def test_decode_raw_transaction_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -22, 'message': 'TX decode failed'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.decode_raw_transaction('invalid_hex_string')
        self.assertEqual(context.exception.rpc_error_code, -22)
        self.assertIn('TX decode failed', str(context.exception))

    @patch('requests.Session.post')
    def test_decode_raw_transaction_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Timeout decoding tx")

        with self.assertRaises(RequestException):
            self.client.decode_raw_transaction('some_hex_string')

    # Tests for send_raw_transaction
    @patch('requests.Session.post')
    def test_send_raw_transaction_success(self, mock_post):
        sent_txid = "txid_of_sent_transaction"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': sent_txid, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        hex_string = "0100000002actualtxdata..."
        result = self.client.send_raw_transaction(hex_string)
        self.assertEqual(result, sent_txid)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'sendrawtransaction')
        self.assertEqual(kwargs['json']['params'], [hex_string])

    @patch('requests.Session.post')
    def test_send_raw_transaction_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -25, 'message': 'Missing inputs'}, # Example error
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.send_raw_transaction('bad_tx_hex_string')
        self.assertEqual(context.exception.rpc_error_code, -25)
        self.assertIn('Missing inputs', str(context.exception))

    @patch('requests.Session.post')
    def test_send_raw_transaction_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Failed to send")

        with self.assertRaises(RequestException):
            self.client.send_raw_transaction('some_tx_hex_string')

if __name__ == '__main__':
    unittest.main()
