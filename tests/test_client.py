import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from requests.exceptions import RequestException, Timeout, HTTPError
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

    # Tests for get_best_block_hash
    @patch('requests.Session.post')
    def test_get_best_block_hash_success(self, mock_post):
        mock_hash = "0000000000000000000aabbccddeeff00112233445566778899aabbccddeeff"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_hash, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_best_block_hash()
        self.assertEqual(result, mock_hash)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getbestblockhash')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_get_best_block_hash_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -1, 'message': 'Generic RPC error'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_best_block_hash()
        self.assertEqual(context.exception.rpc_error_code, -1)
        self.assertIn('Generic RPC error', str(context.exception))

    @patch('requests.Session.post')
    def test_get_best_block_hash_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network down")
        with self.assertRaises(RequestException):
            self.client.get_best_block_hash()

    # Tests for get_blockchain_info
    @patch('requests.Session.post')
    def test_get_blockchain_info_success(self, mock_post):
        mock_info = {"chain": "regtest", "blocks": 101, "headers": 101, "bestblockhash": "somehash"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_info, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_blockchain_info()
        self.assertEqual(result, mock_info)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getblockchaininfo')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_get_blockchain_info_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -2, 'message': 'Node is starting'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_blockchain_info()
        self.assertEqual(context.exception.rpc_error_code, -2)
        self.assertIn('Node is starting', str(context.exception))

    @patch('requests.Session.post')
    def test_get_blockchain_info_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Timeout fetching chain info")
        with self.assertRaises(RequestException):
            self.client.get_blockchain_info()

    # Tests for get_block_filter
    @patch('requests.Session.post')
    def test_get_block_filter_success_default_type(self, mock_post):
        mock_filter_data = {"filter": "hex_filter_string", "header": "block_hash_for_filter"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_filter_data, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        block_hash = "some_block_hash_for_filter"
        result = self.client.get_block_filter(block_hash)
        self.assertEqual(result, mock_filter_data)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getblockfilter')
        self.assertEqual(kwargs['json']['params'], [block_hash, "basic"])

    @patch('requests.Session.post')
    def test_get_block_filter_success_custom_type(self, mock_post):
        mock_filter_data = {"filter": "custom_hex_filter_string", "header": "block_hash_for_filter"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_filter_data, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        block_hash = "some_block_hash_for_filter"
        custom_filter_type = "custom_filter"
        result = self.client.get_block_filter(block_hash, filter_type=custom_filter_type)
        self.assertEqual(result, mock_filter_data)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getblockfilter')
        self.assertEqual(kwargs['json']['params'], [block_hash, custom_filter_type])

    @patch('requests.Session.post')
    def test_get_block_filter_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -5, 'message': 'Block not found or filter not available'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_block_filter("non_existent_block_hash_for_filter")
        self.assertEqual(context.exception.rpc_error_code, -5)
        self.assertIn('Block not found or filter not available', str(context.exception))

    @patch('requests.Session.post')
    def test_get_block_filter_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Filter network error")
        with self.assertRaises(RequestException):
            self.client.get_block_filter("some_block_hash_for_filter")

    # Tests for get_block_header
    @patch('requests.Session.post')
    def test_get_block_header_success_verbose_true(self, mock_post):
        mock_header_json = {"hash": "header_hash", "height": 123, "version": 1}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_header_json, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        block_hash = "some_header_hash"
        result = self.client.get_block_header(block_hash, verbose=True) # Default is True
        self.assertEqual(result, mock_header_json)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getblockheader')
        self.assertEqual(kwargs['json']['params'], [block_hash, True])

    @patch('requests.Session.post')
    def test_get_block_header_success_verbose_false(self, mock_post):
        mock_header_hex = "01000000..." # Hex string for a block header
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_header_hex, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        block_hash = "another_header_hash"
        result = self.client.get_block_header(block_hash, verbose=False)
        self.assertEqual(result, mock_header_hex)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getblockheader')
        self.assertEqual(kwargs['json']['params'], [block_hash, False])

    @patch('requests.Session.post')
    def test_get_block_header_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -5, 'message': 'Block not found'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_block_header("non_existent_header_hash")
        self.assertEqual(context.exception.rpc_error_code, -5)
        self.assertIn('Block not found', str(context.exception))

    @patch('requests.Session.post')
    def test_get_block_header_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Timeout getting header")
        with self.assertRaises(RequestException):
            self.client.get_block_header("some_header_hash")

    # Tests for get_block_stats
    @patch('requests.Session.post')
    def test_get_block_stats_success_hash(self, mock_post):
        mock_stats = {"avgfee": 100, "maxfee": 1000}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_stats, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        block_hash = "a_block_hash_for_stats"
        result = self.client.get_block_stats(block_hash)
        self.assertEqual(result, mock_stats)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getblockstats')
        self.assertEqual(kwargs['json']['params'], [block_hash])

    @patch('requests.Session.post')
    def test_get_block_stats_success_height_no_stats(self, mock_post):
        mock_stats = {"avgfee": 120, "medianfee": 110}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_stats, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        height = 12345
        result = self.client.get_block_stats(height)
        self.assertEqual(result, mock_stats)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getblockstats')
        self.assertEqual(kwargs['json']['params'], [height])

    @patch('requests.Session.post')
    def test_get_block_stats_success_height_with_stats(self, mock_post):
        mock_stats = {"minfee": 50, "maxfee": 5000}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_stats, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        height = 54321
        stats_to_request = ["minfee", "maxfee"]
        result = self.client.get_block_stats(height, stats=stats_to_request)
        self.assertEqual(result, mock_stats)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getblockstats')
        self.assertEqual(kwargs['json']['params'], [height, stats_to_request])

    @patch('requests.Session.post')
    def test_get_block_stats_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -5, 'message': 'Block not found'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_block_stats("non_existent_hash_for_stats")
        self.assertEqual(context.exception.rpc_error_code, -5)
        self.assertIn('Block not found', str(context.exception))

    @patch('requests.Session.post')
    def test_get_block_stats_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error getting stats")
        with self.assertRaises(RequestException):
            self.client.get_block_stats(12345)

    # Tests for get_chain_tips
    @patch('requests.Session.post')
    def test_get_chain_tips_success(self, mock_post):
        mock_tips = [{"height": 120, "hash": "tip1_hash", "branchlen": 1, "status": "active"}]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_tips, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_chain_tips()
        self.assertEqual(result, mock_tips)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getchaintips')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_get_chain_tips_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -3, 'message': 'Chaintips error'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_chain_tips()
        self.assertEqual(context.exception.rpc_error_code, -3)
        self.assertIn('Chaintips error', str(context.exception))

    @patch('requests.Session.post')
    def test_get_chain_tips_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Timeout getting chaintips")
        with self.assertRaises(RequestException):
            self.client.get_chain_tips()

    # Tests for get_chain_tx_stats
    @patch('requests.Session.post')
    def test_get_chain_tx_stats_success_no_args(self, mock_post):
        mock_stats = {"time": 1600000000, "txcount": 10000, "window_block_count": 100}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_stats, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_chain_tx_stats()
        self.assertEqual(result, mock_stats)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getchaintxstats')
        self.assertEqual(kwargs['json']['params'], []) # Expect empty list for no args

    @patch('requests.Session.post')
    def test_get_chain_tx_stats_success_with_nblocks(self, mock_post):
        mock_stats = {"time": 1600000000, "txcount": 500, "window_block_count": 50}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_stats, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        nblocks = 50
        result = self.client.get_chain_tx_stats(nblocks=nblocks)
        self.assertEqual(result, mock_stats)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getchaintxstats')
        self.assertEqual(kwargs['json']['params'], [nblocks])

    @patch('requests.Session.post')
    def test_get_chain_tx_stats_success_with_nblocks_and_hash(self, mock_post):
        mock_stats = {"time": 1500000000, "txcount": 200, "window_block_count": 20}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_stats, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        nblocks = 20
        block_hash = "some_block_hash_for_tx_stats"
        result = self.client.get_chain_tx_stats(nblocks=nblocks, block_hash=block_hash)
        self.assertEqual(result, mock_stats)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getchaintxstats')
        self.assertEqual(kwargs['json']['params'], [nblocks, block_hash])

    @patch('requests.Session.post')
    def test_get_chain_tx_stats_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -8, 'message': 'Block not found'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_chain_tx_stats(nblocks=10, block_hash="non_existent_hash")
        self.assertEqual(context.exception.rpc_error_code, -8)
        self.assertIn('Block not found', str(context.exception))

    @patch('requests.Session.post')
    def test_get_chain_tx_stats_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for txstats")
        with self.assertRaises(RequestException):
            self.client.get_chain_tx_stats()

    # Tests for get_difficulty
    @patch('requests.Session.post')
    def test_get_difficulty_success(self, mock_post):
        mock_difficulty = 12345.6789
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_difficulty, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_difficulty()
        self.assertEqual(result, mock_difficulty)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getdifficulty')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_get_difficulty_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -1, 'message': 'Difficulty error'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_difficulty()
        self.assertEqual(context.exception.rpc_error_code, -1)
        self.assertIn('Difficulty error', str(context.exception))

    @patch('requests.Session.post')
    def test_get_difficulty_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Timeout getting difficulty")
        with self.assertRaises(RequestException):
            self.client.get_difficulty()

    # Tests for get_mempool_ancestors
    @patch('requests.Session.post')
    def test_get_mempool_ancestors_success_verbose_false(self, mock_post):
        mock_ancestors_list = ["txid1", "txid2", "txid3"]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_ancestors_list, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        txid = "target_txid_ancestors"
        result = self.client.get_mempool_ancestors(txid) # verbose=False by default
        self.assertEqual(result, mock_ancestors_list)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getmempoolancestors')
        self.assertEqual(kwargs['json']['params'], [txid, False])

    @patch('requests.Session.post')
    def test_get_mempool_ancestors_success_verbose_true(self, mock_post):
        mock_ancestors_verbose = {
            "txid1": {"size": 100, "fee": 0.001},
            "txid2": {"size": 200, "fee": 0.002}
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_ancestors_verbose, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        txid = "target_txid_ancestors_verbose"
        result = self.client.get_mempool_ancestors(txid, verbose=True)
        self.assertEqual(result, mock_ancestors_verbose)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getmempoolancestors')
        self.assertEqual(kwargs['json']['params'], [txid, True])

    @patch('requests.Session.post')
    def test_get_mempool_ancestors_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -5, 'message': 'Transaction not in mempool'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_mempool_ancestors("non_mempool_txid_ancestors")
        self.assertEqual(context.exception.rpc_error_code, -5)
        self.assertIn('Transaction not in mempool', str(context.exception))

    @patch('requests.Session.post')
    def test_get_mempool_ancestors_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for mempool ancestors")
        with self.assertRaises(RequestException):
            self.client.get_mempool_ancestors("any_txid_ancestors")

    # Tests for get_mempool_descendants
    @patch('requests.Session.post')
    def test_get_mempool_descendants_success_verbose_false(self, mock_post):
        mock_descendants_list = ["txid_child1", "txid_child2"]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_descendants_list, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        txid = "target_txid_descendants"
        result = self.client.get_mempool_descendants(txid) # verbose=False by default
        self.assertEqual(result, mock_descendants_list)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getmempooldescendants')
        self.assertEqual(kwargs['json']['params'], [txid, False])

    @patch('requests.Session.post')
    def test_get_mempool_descendants_success_verbose_true(self, mock_post):
        mock_descendants_verbose = {
            "txid_child1": {"size": 150, "fee": 0.0015},
            "txid_child2": {"size": 250, "fee": 0.0025}
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_descendants_verbose, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        txid = "target_txid_descendants_verbose"
        result = self.client.get_mempool_descendants(txid, verbose=True)
        self.assertEqual(result, mock_descendants_verbose)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getmempooldescendants')
        self.assertEqual(kwargs['json']['params'], [txid, True])

    @patch('requests.Session.post')
    def test_get_mempool_descendants_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -5, 'message': 'Transaction not in mempool'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_mempool_descendants("non_mempool_txid_descendants")
        self.assertEqual(context.exception.rpc_error_code, -5)
        self.assertIn('Transaction not in mempool', str(context.exception))

    @patch('requests.Session.post')
    def test_get_mempool_descendants_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for mempool descendants")
        with self.assertRaises(RequestException):
            self.client.get_mempool_descendants("any_txid_descendants")

    # Tests for get_mempool_entry
    @patch('requests.Session.post')
    def test_get_mempool_entry_success(self, mock_post):
        mock_entry_data = {"size": 250, "fee": 0.00012345, "time": 1600000000}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_entry_data, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        txid = "mempool_txid_entry"
        result = self.client.get_mempool_entry(txid)
        self.assertEqual(result, mock_entry_data)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getmempoolentry')
        self.assertEqual(kwargs['json']['params'], [txid])

    @patch('requests.Session.post')
    def test_get_mempool_entry_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -5, 'message': 'Transaction not in mempool.'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_mempool_entry("non_existent_mempool_txid")
        self.assertEqual(context.exception.rpc_error_code, -5)
        self.assertIn('Transaction not in mempool.', str(context.exception))

    @patch('requests.Session.post')
    def test_get_mempool_entry_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Timeout getting mempool entry")
        with self.assertRaises(RequestException):
            self.client.get_mempool_entry("any_mempool_txid")

    # Tests for get_mempool_info
    @patch('requests.Session.post')
    def test_get_mempool_info_success(self, mock_post):
        mock_info = {"size": 1000, "bytes": 500000, "usage": 2000000}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_info, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_mempool_info()
        self.assertEqual(result, mock_info)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getmempoolinfo')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_get_mempool_info_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200 # Assuming RPC errors still give 200 OK
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -1, 'message': 'Mempool info error'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_mempool_info()
        self.assertEqual(context.exception.rpc_error_code, -1)
        self.assertIn('Mempool info error', str(context.exception))

    @patch('requests.Session.post')
    def test_get_mempool_info_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for mempool info")
        with self.assertRaises(RequestException):
            self.client.get_mempool_info()

    # Tests for get_raw_mempool
    @patch('requests.Session.post')
    def test_get_raw_mempool_success_verbose_false(self, mock_post):
        mock_tx_list = ["txid1", "txid2", "txid3"]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_tx_list, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_raw_mempool() # verbose=False by default
        self.assertEqual(result, mock_tx_list)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getrawmempool')
        self.assertEqual(kwargs['json']['params'], [False])

    @patch('requests.Session.post')
    def test_get_raw_mempool_success_verbose_true_seq_false(self, mock_post):
        mock_tx_verbose_map = {
            "txid1": {"size": 100, "fee": 0.001, "time": 1600000000},
            "txid2": {"size": 200, "fee": 0.002, "time": 1600000001}
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_tx_verbose_map, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_raw_mempool(verbose=True) # mempool_sequence=False by default
        self.assertEqual(result, mock_tx_verbose_map)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getrawmempool')
        self.assertEqual(kwargs['json']['params'], [True, False])

    @patch('requests.Session.post')
    def test_get_raw_mempool_success_verbose_true_seq_true(self, mock_post):
        mock_tx_verbose_seq_map = {
            "txid1": {"size": 100, "fee": 0.001, "time": 1600000000, "mempoolentrysequence": 1},
            "txid2": {"size": 200, "fee": 0.002, "time": 1600000001, "mempoolentrysequence": 2}
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_tx_verbose_seq_map, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_raw_mempool(verbose=True, mempool_sequence=True)
        self.assertEqual(result, mock_tx_verbose_seq_map)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getrawmempool')
        self.assertEqual(kwargs['json']['params'], [True, True])

    @patch('requests.Session.post')
    def test_get_raw_mempool_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -1, 'message': 'Raw mempool error'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_raw_mempool(verbose=True)
        self.assertEqual(context.exception.rpc_error_code, -1)
        self.assertIn('Raw mempool error', str(context.exception))

    @patch('requests.Session.post')
    def test_get_raw_mempool_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for rawmempool")
        with self.assertRaises(RequestException):
            self.client.get_raw_mempool()

    # Tests for get_tx_out
    @patch('requests.Session.post')
    def test_get_tx_out_success_include_mempool_true(self, mock_post):
        mock_tx_out_data = {
            "bestblock": "some_block_hash",
            "confirmations": 123,
            "value": 1.2345,
            "scriptPubKey": {"asm": "OP_DUP OP_HASH160 ...", "hex": "76a914...", "type": "pubkeyhash"}
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_tx_out_data, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        txid = "output_txid"
        vout = 0
        result = self.client.get_tx_out(txid, vout) # include_mempool=True by default
        self.assertEqual(result, mock_tx_out_data)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'gettxout')
        self.assertEqual(kwargs['json']['params'], [txid, vout, True])

    @patch('requests.Session.post')
    def test_get_tx_out_success_include_mempool_false(self, mock_post):
        mock_tx_out_data_no_mempool = {
            "bestblock": "another_block_hash",
            "confirmations": 10,
            "value": 0.5,
            "scriptPubKey": {"asm": "OP_CHECKSIG", "hex": "ac", "type": "pubkey"}
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_tx_out_data_no_mempool, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        txid = "output_txid_no_mempool"
        vout = 1
        result = self.client.get_tx_out(txid, vout, include_mempool=False)
        self.assertEqual(result, mock_tx_out_data_no_mempool)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'gettxout')
        self.assertEqual(kwargs['json']['params'], [txid, vout, False])

    @patch('requests.Session.post')
    def test_get_tx_out_success_unspent(self, mock_post): # Covers case where output is unspent (None result)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': None, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        txid = "unspent_txid"
        vout = 0
        result = self.client.get_tx_out(txid, vout)
        self.assertIsNone(result) # Bitcoin Core returns null for unspent/non-existent outputs
        mock_post.assert_called_once()


    @patch('requests.Session.post')
    def test_get_tx_out_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -5, 'message': 'Invalid TXID or vout index'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_tx_out("invalid_txid_for_gettxout", 99)
        self.assertEqual(context.exception.rpc_error_code, -5)
        self.assertIn('Invalid TXID or vout index', str(context.exception))

    @patch('requests.Session.post')
    def test_get_tx_out_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for gettxout")
        with self.assertRaises(RequestException):
            self.client.get_tx_out("any_txid_for_gettxout", 0)

    # Tests for get_tx_out_proof
    @patch('requests.Session.post')
    def test_get_tx_out_proof_success_no_blockhash(self, mock_post):
        mock_proof_hex = "merkle_proof_hex_string"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_proof_hex, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        txids = ["txid1_for_proof", "txid2_for_proof"]
        result = self.client.get_tx_out_proof(txids)
        self.assertEqual(result, mock_proof_hex)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'gettxoutproof')
        self.assertEqual(kwargs['json']['params'], [txids])

    @patch('requests.Session.post')
    def test_get_tx_out_proof_success_with_blockhash(self, mock_post):
        mock_proof_hex_specific_block = "merkle_proof_hex_string_specific_block"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_proof_hex_specific_block, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        txids = ["txid3_for_proof"]
        block_hash = "specific_block_hash_for_proof"
        result = self.client.get_tx_out_proof(txids, block_hash=block_hash)
        self.assertEqual(result, mock_proof_hex_specific_block)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'gettxoutproof')
        self.assertEqual(kwargs['json']['params'], [txids, block_hash])

    @patch('requests.Session.post')
    def test_get_tx_out_proof_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -5, 'message': 'Transaction not found or block not found'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_tx_out_proof(["non_existent_txid_for_proof"])
        self.assertEqual(context.exception.rpc_error_code, -5)
        self.assertIn('Transaction not found or block not found', str(context.exception))

    @patch('requests.Session.post')
    def test_get_tx_out_proof_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Timeout getting txoutproof")
        with self.assertRaises(RequestException):
            self.client.get_tx_out_proof(["any_txid_for_proof"])

    # Tests for get_tx_out_set_info
    @patch('requests.Session.post')
    def test_get_tx_out_set_info_success_default_params(self, mock_post):
        mock_info = {"height": 500, "bestblock": "best_block_for_txoset", "txouts": 10000}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_info, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_tx_out_set_info() # All defaults
        self.assertEqual(result, mock_info)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'gettxoutsetinfo')
        self.assertEqual(kwargs['json']['params'], ['hash_serialized_2'])

    @patch('requests.Session.post')
    def test_get_tx_out_set_info_success_custom_hash_type(self, mock_post):
        mock_info = {"height": 501, "bestblock": "block_for_txoset_custom", "txouts": 10001}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_info, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_tx_out_set_info(hash_type="muhash")
        self.assertEqual(result, mock_info)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'gettxoutsetinfo')
        self.assertEqual(kwargs['json']['params'], ['muhash'])

    @patch('requests.Session.post')
    def test_get_tx_out_set_info_success_with_height(self, mock_post):
        mock_info = {"height": 123, "bestblock": "block_at_123", "txouts": 1234}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_info, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_tx_out_set_info(hash_or_height=123)
        self.assertEqual(result, mock_info)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'gettxoutsetinfo')
        self.assertEqual(kwargs['json']['params'], ['hash_serialized_2', 123])

    @patch('requests.Session.post')
    def test_get_tx_out_set_info_success_with_hash_and_index(self, mock_post):
        mock_info = {"height": 456, "bestblock": "block_hash_for_index", "txouts": 5678}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_info, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_tx_out_set_info(hash_type="muhash", hash_or_height="block_hash_for_index", use_index=True)
        self.assertEqual(result, mock_info)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'gettxoutsetinfo')
        self.assertEqual(kwargs['json']['params'], ['muhash', "block_hash_for_index", True])

    @patch('requests.Session.post')
    def test_get_tx_out_set_info_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -8, 'message': 'Block not found for txoutsetinfo'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_tx_out_set_info(hash_or_height="non_existent_block_for_txoset")
        self.assertEqual(context.exception.rpc_error_code, -8)
        self.assertIn('Block not found for txoutsetinfo', str(context.exception))

    @patch('requests.Session.post')
    def test_get_tx_out_set_info_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for txoutsetinfo")
        with self.assertRaises(RequestException):
            self.client.get_tx_out_set_info()

    # Tests for precious_block
    @patch('requests.Session.post')
    def test_precious_block_success(self, mock_post):
        # preciousblock returns None on success
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': None, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        block_hash = "a_precious_block_hash"
        result = self.client.precious_block(block_hash)
        self.assertIsNone(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'preciousblock')
        self.assertEqual(kwargs['json']['params'], [block_hash])

    @patch('requests.Session.post')
    def test_precious_block_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None, # Should still be None even on error for this command
            'error': {'code': -5, 'message': 'Block not found or already precious'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.precious_block("non_existent_precious_block")
        self.assertEqual(context.exception.rpc_error_code, -5)
        self.assertIn('Block not found or already precious', str(context.exception))

    @patch('requests.Session.post')
    def test_precious_block_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Timeout making block precious")
        with self.assertRaises(RequestException):
            self.client.precious_block("any_precious_block")

    # Tests for prune_blockchain
    @patch('requests.Session.post')
    def test_prune_blockchain_success(self, mock_post):
        pruned_height = 500
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': pruned_height, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        target_height = 1000
        result = self.client.prune_blockchain(target_height)
        self.assertEqual(result, pruned_height) # This is what the RPC returns
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'pruneblockchain')
        self.assertEqual(kwargs['json']['params'], [target_height])

    @patch('requests.Session.post')
    def test_prune_blockchain_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None, # Or specific error code for prune failure
            'error': {'code': -1, 'message': 'Prune mode disabled or invalid height'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.prune_blockchain(100) # Assuming prune mode is off or height too low
        self.assertEqual(context.exception.rpc_error_code, -1)
        self.assertIn('Prune mode disabled or invalid height', str(context.exception))

    @patch('requests.Session.post')
    def test_prune_blockchain_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error during prune")
        with self.assertRaises(RequestException):
            self.client.prune_blockchain(2000)

    # Tests for save_mempool
    @patch('requests.Session.post')
    def test_save_mempool_success(self, mock_post):
        # savemempool returns None on success in recent versions
        # Older versions might return a dict like {"filename": "mempool.dat"}
        # For this test, we'll assume recent behavior (None)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': None, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.save_mempool()
        self.assertIsNone(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'savemempool')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_save_mempool_rpc_error(self, mock_post):
        # Example: If node is not running with -persistmempool
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -1, 'message': 'Mempool not saved, persistance disabled'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.save_mempool()
        self.assertEqual(context.exception.rpc_error_code, -1)
        self.assertIn('Mempool not saved, persistance disabled', str(context.exception))

    @patch('requests.Session.post')
    def test_save_mempool_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error saving mempool")
        with self.assertRaises(RequestException):
            self.client.save_mempool()

    # Tests for scan_tx_out_set
    @patch('requests.Session.post')
    def test_scan_tx_out_set_success_start(self, mock_post):
        mock_scan_result = {"success": True, "txouts": 10, "height": 700000, "bestblock": "someblockhash"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_scan_result, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        action = "start"
        scan_objects = ["addr(bc1q...)"] # Corrected: removed extra quote inside the string list
        result = self.client.scan_tx_out_set(action, scan_objects)
        self.assertEqual(result, mock_scan_result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'scantxoutset')
        self.assertEqual(kwargs['json']['params'], [action, scan_objects])

    @patch('requests.Session.post')
    def test_scan_tx_out_set_success_status(self, mock_post):
        mock_status_result = {"success": True, "progress": 50.5, "current_height": 350000}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_status_result, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        action = "status"
        # scan_objects might not be needed for 'status' if a scan is in progress,
        # but the RPC might expect an empty list or specific format.
        # For this SDK, we'll pass what the user gives.
        scan_objects = []
        result = self.client.scan_tx_out_set(action, scan_objects)
        self.assertEqual(result, mock_status_result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'scantxoutset')
        self.assertEqual(kwargs['json']['params'], [action, scan_objects])

    @patch('requests.Session.post')
    def test_scan_tx_out_set_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -8, 'message': 'Invalid scan object'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.scan_tx_out_set("start", ["invalid_object"])
        self.assertEqual(context.exception.rpc_error_code, -8)
        self.assertIn('Invalid scan object', str(context.exception))

    @patch('requests.Session.post')
    def test_scan_tx_out_set_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for scantxoutset")
        with self.assertRaises(RequestException):
            self.client.scan_tx_out_set("abort", [])

    # Tests for verify_chain
    @patch('requests.Session.post')
    def test_verify_chain_success_default_params(self, mock_post):
        # verifychain returns true if successful, false if not.
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': True, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.verify_chain() # Default checklevel=3, nblocks=6
        self.assertTrue(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'verifychain')
        self.assertEqual(kwargs['json']['params'], [3, 6])

    @patch('requests.Session.post')
    def test_verify_chain_success_custom_params(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': True, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        checklevel = 4
        nblocks = 100
        result = self.client.verify_chain(checklevel=checklevel, nblocks=nblocks)
        self.assertTrue(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'verifychain')
        self.assertEqual(kwargs['json']['params'], [checklevel, nblocks])

    @patch('requests.Session.post')
    def test_verify_chain_failure_response(self, mock_post): # Test case where verifychain itself returns false
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': False, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.verify_chain(checklevel=0, nblocks=0) # Check all blocks, basic check
        self.assertFalse(result)
        mock_post.assert_called_once()

    @patch('requests.Session.post')
    def test_verify_chain_rpc_error(self, mock_post):
        # This would be an unexpected error, as verifychain itself usually returns true/false
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None, # Or True/False, but with an error object
            'error': {'code': -1, 'message': 'Verifychain internal error'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.verify_chain()
        self.assertEqual(context.exception.rpc_error_code, -1)
        self.assertIn('Verifychain internal error', str(context.exception))

    @patch('requests.Session.post')
    def test_verify_chain_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Timeout during verifychain")
        with self.assertRaises(RequestException):
            self.client.verify_chain()

    # Tests for verify_tx_out_proof
    @patch('requests.Session.post')
    def test_verify_tx_out_proof_success_valid_proof(self, mock_post):
        mock_txids = ["txid_verified1", "txid_verified2"]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_txids, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        proof_hex = "valid_merkle_proof_hex"
        result = self.client.verify_tx_out_proof(proof_hex)
        self.assertEqual(result, mock_txids)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'verifytxoutproof')
        self.assertEqual(kwargs['json']['params'], [proof_hex])

    @patch('requests.Session.post')
    def test_verify_tx_out_proof_success_invalid_proof(self, mock_post):
        # If proof is invalid, Bitcoin Core returns an empty list or null.
        # Let's assume null based on some RPC docs (or an empty list []).
        # We will test for None as that's a common way to represent null in JSON.
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': None, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        proof_hex = "invalid_merkle_proof_hex"
        result = self.client.verify_tx_out_proof(proof_hex)
        self.assertIsNone(result) # Or self.assertEqual(result, []) depending on core behavior
        mock_post.assert_called_once()

    @patch('requests.Session.post')
    def test_verify_tx_out_proof_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -8, 'message': 'Proof must be hexadecimal string'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.verify_tx_out_proof("not_a_hex_proof")
        self.assertEqual(context.exception.rpc_error_code, -8)
        self.assertIn('Proof must be hexadecimal string', str(context.exception))

    @patch('requests.Session.post')
    def test_verify_tx_out_proof_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for verifytxoutproof")
        with self.assertRaises(RequestException):
            self.client.verify_tx_out_proof("some_proof_hex")

    # Tests for get_memory_info
    @patch('requests.Session.post')
    def test_get_memory_info_success_default_mode(self, mock_post):
        mock_mem_info_stats = {"locked": {"used": 0, "free": 65536, "total": 65536, "locked": 65536, "chunks_used": 0, "chunks_free": 1}}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_mem_info_stats, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_memory_info() # mode='stats' by default
        self.assertEqual(result, mock_mem_info_stats)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getmemoryinfo')
        self.assertEqual(kwargs['json']['params'], ['stats'])

    @patch('requests.Session.post')
    def test_get_memory_info_success_specific_mode(self, mock_post):
        mock_mem_info_malloc = "<malloc version=\"jemalloc-5.2.1\"> ..." # XML String
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_mem_info_malloc, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_memory_info(mode="mallocinfo")
        self.assertEqual(result, mock_mem_info_malloc)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getmemoryinfo')
        self.assertEqual(kwargs['json']['params'], ['mallocinfo'])

    @patch('requests.Session.post')
    def test_get_memory_info_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -8, 'message': 'Invalid mode for getmemoryinfo'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_memory_info(mode="invalid_mode")
        self.assertEqual(context.exception.rpc_error_code, -8)
        self.assertIn('Invalid mode for getmemoryinfo', str(context.exception))

    @patch('requests.Session.post')
    def test_get_memory_info_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for getmemoryinfo")
        with self.assertRaises(RequestException):
            self.client.get_memory_info()

    # Tests for get_rpc_info
    @patch('requests.Session.post')
    def test_get_rpc_info_success(self, mock_post):
        mock_rpc_info = {
            "active_commands": [
                {"method": "getrpcinfo", "duration": 12345}
            ],
            "logpath": "/home/user/.bitcoin/debug.log"
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_rpc_info, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_rpc_info()
        self.assertEqual(result, mock_rpc_info)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getrpcinfo')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_get_rpc_info_rpc_error(self, mock_post):
        # Unlikely to have a specific RPC error for getrpcinfo itself, usually works or network error
        mock_response = MagicMock()
        mock_response.status_code = 500 # Or some other non-200
        mock_response.json.side_effect = ValueError # If server gives non-JSON on actual error
        mock_response.raise_for_status.side_effect = HTTPError("Server Error")
        mock_post.return_value = mock_response

        # If it's an RPC error formatted in JSON (less likely for this command)
        # mock_response.status_code = 200
        # mock_response.json.return_value = {'result': None, 'error': {'code': -32603, 'message': 'Internal server error'}}


        # This test expects a RequestException because raise_for_status() is called first.
        # If the server returned a JSON RPC error with a 200, then BitcoinRPCError would be tested.
        with self.assertRaises(RequestException): # Use imported RequestException directly
             self.client.get_rpc_info()


    @patch('requests.Session.post')
    def test_get_rpc_info_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Timeout getting RPC info")
        with self.assertRaises(RequestException):
            self.client.get_rpc_info()

    # Tests for help
    @patch('requests.Session.post')
    def test_help_success_no_command(self, mock_post):
        mock_help_text_all = "getinfo\ngetblock \"hash\" ( verbose )\n..."
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_help_text_all, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.help()
        self.assertEqual(result, mock_help_text_all)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'help')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_help_success_with_command(self, mock_post):
        mock_help_text_specific = "getblock \"hash\" ( verbose )\n\nReturns ... (rest of help text)"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_help_text_specific, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        command = "getblock"
        result = self.client.help(command=command)
        self.assertEqual(result, mock_help_text_specific)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'help')
        self.assertEqual(kwargs['json']['params'], [command])

    @patch('requests.Session.post')
    def test_help_rpc_error_invalid_command(self, mock_post):
        # Bitcoin Core's help for an invalid command might still be a string,
        # but if it were a structured error, it would be like this.
        # More typically, it might return a string message like "help: unknown command: non_existent_command".
        # For this test, we'll assume it can return a standard RPC error if the command is truly problematic beyond just not found.
        # However, the primary way 'help' indicates "not found" is by the content of the success string.
        # This tests a more generic RPC error during a help call.
        mock_response = MagicMock()
        mock_response.status_code = 200 # Or potentially a 500 if the RPC server itself has an issue with 'help'
        mock_response.json.return_value = {
            'result': None, # Or help text for "unknown command"
            'error': {'code': -1, 'message': 'Invalid command for help'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            # This specific call might not trigger this error type in a real node,
            # as "help non_existent_command" often returns a string.
            # This is more for testing the error path of _rpc_request.
            self.client.help(command="trigger_generic_error_path")
        self.assertEqual(context.exception.rpc_error_code, -1)
        self.assertIn('Invalid command for help', str(context.exception))

    @patch('requests.Session.post')
    def test_help_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Timeout for help command")
        with self.assertRaises(RequestException):
            self.client.help()

    # Tests for logging
    @patch('requests.Session.post')
    def test_logging_success_query(self, mock_post):
        mock_log_status = {"net": True, "tor": False, "mempool": True}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_log_status, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.logging() # Query current status
        self.assertEqual(result, mock_log_status)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'logging')
        self.assertEqual(kwargs['json']['params'], []) # No params for query

    @patch('requests.Session.post')
    def test_logging_success_include_only(self, mock_post):
        mock_log_status_after_include = {"net": True, "tor": True, "mempool": False}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_log_status_after_include, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        include_categories = ["tor"]
        # Result is the current logging status *after* the change
        result = self.client.logging(include=include_categories)
        self.assertEqual(result, mock_log_status_after_include)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'logging')
        # Params: [include, exclude, add, remove, clear, stat]
        self.assertEqual(kwargs['json']['params'], [include_categories, None, None, None, None, None])

    @patch('requests.Session.post')
    def test_logging_success_clear_only(self, mock_post):
        mock_log_status_after_clear = {} # All categories cleared
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_log_status_after_clear, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.logging(clear=True)
        self.assertEqual(result, mock_log_status_after_clear)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'logging')
        self.assertEqual(kwargs['json']['params'], [None, None, None, None, True, None])


    @patch('requests.Session.post')
    def test_logging_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -1, 'message': 'Invalid logging category'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.logging(add=["nonexistentcategory"])
        self.assertEqual(context.exception.rpc_error_code, -1)
        self.assertIn('Invalid logging category', str(context.exception))

    @patch('requests.Session.post')
    def test_logging_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for logging")
        with self.assertRaises(RequestException):
            self.client.logging()

    # Tests for stop
    @patch('requests.Session.post')
    def test_stop_success(self, mock_post):
        stop_message = "Bitcoin Core stopping"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': stop_message, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.stop()
        self.assertEqual(result, stop_message)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'stop')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_stop_rpc_error(self, mock_post):
        # Unlikely to have a JSON-RPC error for stop if it starts stopping,
        # usually it would just stop or fail at network level if already stopped.
        # This is a hypothetical RPC error.
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -1, 'message': 'Stop error, already stopping?'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.stop()
        self.assertEqual(context.exception.rpc_error_code, -1)
        self.assertIn('Stop error, already stopping?', str(context.exception))

    @patch('requests.Session.post')
    def test_stop_network_error(self, mock_post):
        # This is more likely if the server stops before responding
        mock_post.side_effect = RequestException("Connection refused - server stopped")
        with self.assertRaises(RequestException):
            self.client.stop()

    # Tests for uptime
    @patch('requests.Session.post')
    def test_uptime_success(self, mock_post):
        server_uptime_seconds = 86400 # e.g., 1 day
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': server_uptime_seconds, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.uptime()
        self.assertEqual(result, server_uptime_seconds)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'uptime')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_uptime_rpc_error(self, mock_post):
        # Highly unlikely for uptime to have an RPC error if the server is up.
        # This is mostly for testing the error handling path.
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -1, 'message': 'Uptime retrieval error (hypothetical)'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.uptime()
        self.assertEqual(context.exception.rpc_error_code, -1)
        self.assertIn('Uptime retrieval error (hypothetical)', str(context.exception))

    @patch('requests.Session.post')
    def test_uptime_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Timeout getting uptime")
        with self.assertRaises(RequestException):
            self.client.uptime()

    # Tests for generate_block
    @patch('requests.Session.post')
    def test_generate_block_success(self, mock_post):
        mock_block_info = {"hash": "newly_generated_block_hash"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_block_info, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        output_address = "some_address_or_script"
        transactions = ["rawtxhex1", "rawtxhex2"]
        result = self.client.generate_block(output_address, transactions)
        self.assertEqual(result, mock_block_info)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'generateblock')
        self.assertEqual(kwargs['json']['params'], [output_address, transactions])

    @patch('requests.Session.post')
    def test_generate_block_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -8, 'message': 'Invalid parameter for generateblock'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.generate_block("invalid_output", [])
        self.assertEqual(context.exception.rpc_error_code, -8)
        self.assertIn('Invalid parameter for generateblock', str(context.exception))

    @patch('requests.Session.post')
    def test_generate_block_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for generateblock")
        with self.assertRaises(RequestException):
            self.client.generate_block("address", [])

    # Tests for generate_to_address
    @patch('requests.Session.post')
    def test_generate_to_address_success_default_maxtries(self, mock_post):
        mock_block_hashes = ["hash1", "hash2"]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_block_hashes, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        nblocks = 2
        address = "target_address_for_generation"
        result = self.client.generate_to_address(nblocks, address)
        self.assertEqual(result, mock_block_hashes)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'generatetoaddress')
        self.assertEqual(kwargs['json']['params'], [nblocks, address, 1000000]) # Default maxtries

    @patch('requests.Session.post')
    def test_generate_to_address_success_custom_maxtries(self, mock_post):
        mock_block_hashes_custom = ["hash3"]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_block_hashes_custom, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        nblocks = 1
        address = "another_address_for_generation"
        maxtries = 5000
        result = self.client.generate_to_address(nblocks, address, maxtries=maxtries)
        self.assertEqual(result, mock_block_hashes_custom)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'generatetoaddress')
        self.assertEqual(kwargs['json']['params'], [nblocks, address, maxtries])

    @patch('requests.Session.post')
    def test_generate_to_address_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -8, 'message': 'Invalid address for generatetoaddress'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.generate_to_address(1, "invalid_address")
        self.assertEqual(context.exception.rpc_error_code, -8)
        self.assertIn('Invalid address for generatetoaddress', str(context.exception))

    @patch('requests.Session.post')
    def test_generate_to_address_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for generatetoaddress")
        with self.assertRaises(RequestException):
            self.client.generate_to_address(1, "some_address")

    # Tests for generate_to_descriptor
    @patch('requests.Session.post')
    def test_generate_to_descriptor_success_default_maxtries(self, mock_post):
        mock_block_hashes_desc = ["hash_desc1", "hash_desc2"]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_block_hashes_desc, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        num_blocks = 2
        descriptor = "wpkh(02...)"
        result = self.client.generate_to_descriptor(num_blocks, descriptor)
        self.assertEqual(result, mock_block_hashes_desc)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'generatetodescriptor')
        self.assertEqual(kwargs['json']['params'], [num_blocks, descriptor, 1000000]) # Default maxtries

    @patch('requests.Session.post')
    def test_generate_to_descriptor_success_custom_maxtries(self, mock_post):
        mock_block_hashes_desc_custom = ["hash_desc3"]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_block_hashes_desc_custom, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        num_blocks = 1
        descriptor = "tr(03...)"
        maxtries = 12345
        result = self.client.generate_to_descriptor(num_blocks, descriptor, maxtries=maxtries)
        self.assertEqual(result, mock_block_hashes_desc_custom)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'generatetodescriptor')
        self.assertEqual(kwargs['json']['params'], [num_blocks, descriptor, maxtries])

    @patch('requests.Session.post')
    def test_generate_to_descriptor_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -5, 'message': 'Invalid descriptor'}, # Example error code
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.generate_to_descriptor(1, "invalid_descriptor_string")
        self.assertEqual(context.exception.rpc_error_code, -5)
        self.assertIn('Invalid descriptor', str(context.exception))

    @patch('requests.Session.post')
    def test_generate_to_descriptor_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for generatetodescriptor")
        with self.assertRaises(RequestException):
            self.client.generate_to_descriptor(1, "wpkh(02...)")

    # Tests for get_block_template
    @patch('requests.Session.post')
    def test_get_block_template_success_no_rules(self, mock_post):
        mock_template = {"version": 0x20000000, "previousblockhash": "someprevhash", "transactions": []}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_template, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_block_template() # No rules
        self.assertEqual(result, mock_template)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getblocktemplate')
        self.assertEqual(kwargs['json']['params'], [{}]) # Empty object for default rules

    @patch('requests.Session.post')
    def test_get_block_template_success_with_rules(self, mock_post):
        mock_template_segwit = {"version": 0x20000000, "rules": ["segwit"], "capabilities": ["proposal"]}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_template_segwit, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        rules = ["segwit"]
        result = self.client.get_block_template(rules=rules)
        self.assertEqual(result, mock_template_segwit)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getblocktemplate')
        self.assertEqual(kwargs['json']['params'], [{"rules": rules}])

    @patch('requests.Session.post')
    def test_get_block_template_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -1, 'message': 'Block template error'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_block_template(rules=["invalidrule"])
        self.assertEqual(context.exception.rpc_error_code, -1)
        self.assertIn('Block template error', str(context.exception))

    @patch('requests.Session.post')
    def test_get_block_template_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for getblocktemplate")
        with self.assertRaises(RequestException):
            self.client.get_block_template()

    # Tests for get_mining_info
    @patch('requests.Session.post')
    def test_get_mining_info_success(self, mock_post):
        mock_mining_info = {
            "blocks": 12345, "currentblockweight": 1000, "currentblocktx": 1,
            "difficulty": 100.5, "networkhashps": 1000000, "pooledtx": 5
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_mining_info, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_mining_info()
        self.assertEqual(result, mock_mining_info)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getmininginfo')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_get_mining_info_rpc_error(self, mock_post):
        # Unlikely to have a specific RPC error for getmininginfo itself
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError
        mock_response.raise_for_status.side_effect = HTTPError("Server Error for mining info")
        mock_post.return_value = mock_response

        with self.assertRaises(RequestException):
            self.client.get_mining_info()

    @patch('requests.Session.post')
    def test_get_mining_info_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Timeout getting mining info")
        with self.assertRaises(RequestException):
            self.client.get_mining_info()

    # Tests for get_network_hash_ps
    @patch('requests.Session.post')
    def test_get_network_hash_ps_success_default_params(self, mock_post):
        mock_hash_ps = 1000000000.0 # Example hash rate
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_hash_ps, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_network_hash_ps() # Default nblocks=-1, height=-1
        self.assertEqual(result, mock_hash_ps)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getnetworkhashps')
        self.assertEqual(kwargs['json']['params'], [-1, -1])

    @patch('requests.Session.post')
    def test_get_network_hash_ps_success_custom_params(self, mock_post):
        mock_hash_ps_custom = 1200000000.0
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_hash_ps_custom, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        nblocks = 60
        height = 123456
        result = self.client.get_network_hash_ps(nblocks=nblocks, height=height)
        self.assertEqual(result, mock_hash_ps_custom)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getnetworkhashps')
        self.assertEqual(kwargs['json']['params'], [nblocks, height])

    @patch('requests.Session.post')
    def test_get_network_hash_ps_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -8, 'message': 'Invalid block height for getnetworkhashps'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_network_hash_ps(height=999999999) # Invalid height
        self.assertEqual(context.exception.rpc_error_code, -8)
        self.assertIn('Invalid block height for getnetworkhashps', str(context.exception))

    @patch('requests.Session.post')
    def test_get_network_hash_ps_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for getnetworkhashps")
        with self.assertRaises(RequestException):
            self.client.get_network_hash_ps()

    # Tests for prioritise_transaction
    @patch('requests.Session.post')
    def test_prioritise_transaction_success(self, mock_post):
        # Returns true if successful
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': True, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        txid = "tx_to_prioritise"
        fee_delta = 10000 # Add 10000 satoshis to the fee
        result = self.client.prioritise_transaction(txid, fee_delta=fee_delta) # dummy is None by default
        self.assertTrue(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'prioritisetransaction')
        self.assertEqual(kwargs['json']['params'], [txid, None, fee_delta])

    @patch('requests.Session.post')
    def test_prioritise_transaction_with_dummy_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': True, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        txid = "tx_to_prioritise_dummy"
        dummy_value = 0 # Explicitly passing dummy, though it's ignored
        fee_delta = 5000
        result = self.client.prioritise_transaction(txid, fee_delta=fee_delta, dummy=dummy_value)
        self.assertTrue(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'prioritisetransaction')
        self.assertEqual(kwargs['json']['params'], [txid, dummy_value, fee_delta])

    @patch('requests.Session.post')
    def test_prioritise_transaction_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None, # Or False, but error object is primary
            'error': {'code': -5, 'message': 'Transaction not in mempool for prioritise'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.prioritise_transaction("non_mempool_tx_prioritise", fee_delta=1000)
        self.assertEqual(context.exception.rpc_error_code, -5)
        self.assertIn('Transaction not in mempool for prioritise', str(context.exception))

    @patch('requests.Session.post')
    def test_prioritise_transaction_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for prioritisetransaction")
        with self.assertRaises(RequestException):
            self.client.prioritise_transaction("any_tx_prioritise", fee_delta=0)

    # Tests for submit_block
    @patch('requests.Session.post')
    def test_submit_block_success(self, mock_post):
        # submitblock returns None on success, or an error string if rejected
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': None, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        hexdata = "full_block_hex_data"
        result = self.client.submit_block(hexdata) # dummy is None by default
        self.assertIsNone(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'submitblock')
        self.assertEqual(kwargs['json']['params'], [hexdata, None])

    @patch('requests.Session.post')
    def test_submit_block_rejected(self, mock_post):
        # Example of a rejected block (result is an error string)
        rejection_reason = "duplicate"
        mock_response = MagicMock()
        mock_response.status_code = 200 # Still 200 OK, but with error string in result
        mock_response.json.return_value = {'result': rejection_reason, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        # Note: The current _rpc_request logic would not raise BitcoinRPCError if 'error' field is null.
        # It would return the string content of 'result'. This behavior is specific to submitblock.
        # If the RPC server set the 'error' field, then BitcoinRPCError would be raised.
        # We are testing the case where 'error' is null, and 'result' contains the rejection reason.
        hexdata = "duplicate_block_hex_data"
        result = self.client.submit_block(hexdata)
        self.assertEqual(result, rejection_reason)


    @patch('requests.Session.post')
    def test_submit_block_rpc_error_json(self, mock_post):
        # This tests if the RPC server returns a JSON-RPC error object (less common for submitblock rejections)
        mock_response = MagicMock()
        mock_response.status_code = 200 # Or 500 if it's a server-side issue
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -22, 'message': 'Block decode failed'}, # Example: decode error
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.submit_block("invalid_block_hex_data")
        self.assertEqual(context.exception.rpc_error_code, -22)
        self.assertIn('Block decode failed', str(context.exception))

    @patch('requests.Session.post')
    def test_submit_block_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for submitblock")
        with self.assertRaises(RequestException):
            self.client.submit_block("any_block_hex_data")

    # Tests for submit_header
    @patch('requests.Session.post')
    def test_submit_header_success(self, mock_post):
        # submitheader returns None on success
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': None, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        hexdata = "block_header_hex_data"
        result = self.client.submit_header(hexdata)
        self.assertIsNone(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'submitheader')
        self.assertEqual(kwargs['json']['params'], [hexdata])

    @patch('requests.Session.post')
    def test_submit_header_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -22, 'message': 'Block header decode failed'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.submit_header("invalid_header_hex")
        self.assertEqual(context.exception.rpc_error_code, -22)
        self.assertIn('Block header decode failed', str(context.exception))

    @patch('requests.Session.post')
    def test_submit_header_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for submitheader")
        with self.assertRaises(RequestException):
            self.client.submit_header("any_header_hex")

    # Network RPCs - Set 1
    @patch('requests.Session.post')
    def test_add_node_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': None, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        node = "192.168.0.1:8333"
        command = "add"
        result = self.client.add_node(node, command)
        self.assertIsNone(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'addnode')
        self.assertEqual(kwargs['json']['params'], [node, command])

    @patch('requests.Session.post')
    def test_add_node_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -23, 'message': 'Node already added'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.add_node("192.168.0.1:8333", "add")
        self.assertEqual(context.exception.rpc_error_code, -23)
        self.assertIn('Node already added', str(context.exception))

    @patch('requests.Session.post')
    def test_add_node_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for addnode")
        with self.assertRaises(RequestException):
            self.client.add_node("192.168.0.1:8333", "add")

    @patch('requests.Session.post')
    def test_clear_banned_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': None, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.clear_banned()
        self.assertIsNone(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'clearbanned')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_clear_banned_rpc_error(self, mock_post):
        # Unlikely to have an RPC error for clearbanned, but test path
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError
        mock_response.raise_for_status.side_effect = HTTPError("Server Error for clearbanned")
        mock_post.return_value = mock_response

        with self.assertRaises(RequestException):
            self.client.clear_banned()

    @patch('requests.Session.post')
    def test_clear_banned_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for clearbanned")
        with self.assertRaises(RequestException):
            self.client.clear_banned()

    @patch('requests.Session.post')
    def test_disconnect_node_success_by_address(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': None, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        address = "192.168.0.1:8333"
        result = self.client.disconnect_node(address=address)
        self.assertIsNone(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'disconnectnode')
        self.assertEqual(kwargs['json']['params'], [address])

    @patch('requests.Session.post')
    def test_disconnect_node_success_by_nodeid(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': None, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        nodeid = 1
        result = self.client.disconnect_node(nodeid=nodeid)
        self.assertIsNone(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'disconnectnode')
        self.assertEqual(kwargs['json']['params'], [None, nodeid])

    @patch('requests.Session.post')
    def test_disconnect_node_success_by_address_and_nodeid(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': None, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        address = "192.168.0.1:8333"
        nodeid = 1
        result = self.client.disconnect_node(address=address, nodeid=nodeid)
        self.assertIsNone(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'disconnectnode')
        self.assertEqual(kwargs['json']['params'], [address, nodeid])


    def test_disconnect_node_value_error(self):
        with self.assertRaises(ValueError) as context:
            self.client.disconnect_node() # No args
        self.assertIn("Either address or nodeid must be provided", str(context.exception))


    @patch('requests.Session.post')
    def test_disconnect_node_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -29, 'message': 'Node not found'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.disconnect_node(address="1.2.3.4:5")
        self.assertEqual(context.exception.rpc_error_code, -29)
        self.assertIn('Node not found', str(context.exception))

    @patch('requests.Session.post')
    def test_disconnect_node_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for disconnectnode")
        with self.assertRaises(RequestException):
            self.client.disconnect_node(nodeid=1)

    @patch('requests.Session.post')
    def test_get_added_node_info_success_no_node(self, mock_post):
        mock_info = [{"addednode": "192.168.0.1:8333", "connected": True, "addresses": []}]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_info, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_added_node_info()
        self.assertEqual(result, mock_info)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getaddednodeinfo')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_get_added_node_info_success_with_node(self, mock_post):
        mock_node_specific_info = [{"addednode": "192.168.0.1:8333", "connected": True, "addresses": []}] # Same as all if only one matches
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_node_specific_info, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        node = "192.168.0.1:8333"
        result = self.client.get_added_node_info(node=node)
        self.assertEqual(result, mock_node_specific_info)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getaddednodeinfo')
        self.assertEqual(kwargs['json']['params'], [node])

    @patch('requests.Session.post')
    def test_get_added_node_info_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -24, 'message': 'Node has not been added'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_added_node_info(node="1.2.3.4")
        self.assertEqual(context.exception.rpc_error_code, -24)
        self.assertIn('Node has not been added', str(context.exception))

    @patch('requests.Session.post')
    def test_get_added_node_info_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for getaddednodeinfo")
        with self.assertRaises(RequestException):
            self.client.get_added_node_info()

    @patch('requests.Session.post')
    def test_get_connection_count_success(self, mock_post):
        mock_count = 8
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_count, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_connection_count()
        self.assertEqual(result, mock_count)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getconnectioncount')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_get_connection_count_rpc_error(self, mock_post):
        # Unlikely for this command
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError
        mock_response.raise_for_status.side_effect = HTTPError("Server Error for getconnectioncount")
        mock_post.return_value = mock_response
        with self.assertRaises(RequestException):
            self.client.get_connection_count()

    @patch('requests.Session.post')
    def test_get_connection_count_network_error(self, mock_post):
        mock_post.side_effect = Timeout("Timeout getting connection count")
        with self.assertRaises(RequestException):
            self.client.get_connection_count()

    # Network RPCs - Set 2
    @patch('requests.Session.post')
    def test_get_net_totals_success(self, mock_post):
        mock_totals = {
            "totalbytesrecv": 100000, "totalbytessent": 200000,
            "timemillis": 1234567890, "uploadtarget": {}
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_totals, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_net_totals()
        self.assertEqual(result, mock_totals)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getnettotals')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_get_net_totals_rpc_error(self, mock_post):
        # Unlikely for this command
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError
        mock_response.raise_for_status.side_effect = HTTPError("Server Error for getnettotals")
        mock_post.return_value = mock_response
        with self.assertRaises(RequestException):
            self.client.get_net_totals()

    @patch('requests.Session.post')
    def test_get_net_totals_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for getnettotals")
        with self.assertRaises(RequestException):
            self.client.get_net_totals()

    @patch('requests.Session.post')
    def test_get_network_info_success(self, mock_post):
        mock_net_info = {
            "version": 220000, "subversion": "/Satoshi:0.22.0/",
            "protocolversion": 70016, "localservices": "0000000000000409",
            "localrelay": True, "timeoffset": 0
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_net_info, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_network_info()
        self.assertEqual(result, mock_net_info)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getnetworkinfo')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_get_network_info_rpc_error(self, mock_post):
        # Unlikely for this command
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError
        mock_response.raise_for_status.side_effect = HTTPError("Server Error for getnetworkinfo")
        mock_post.return_value = mock_response
        with self.assertRaises(RequestException):
            self.client.get_network_info()

    @patch('requests.Session.post')
    def test_get_network_info_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for getnetworkinfo")
        with self.assertRaises(RequestException):
            self.client.get_network_info()

    # Tests for get_node_addresses
    @patch('requests.Session.post')
    def test_get_node_addresses_success_default_count(self, mock_post):
        mock_addresses = [{"time": 1600000000, "services": 1, "address": "1.2.3.4", "port": 8333}]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_addresses, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_node_addresses() # Default count=1
        self.assertEqual(result, mock_addresses)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getnodeaddresses')
        self.assertEqual(kwargs['json']['params'], [1])

    @patch('requests.Session.post')
    def test_get_node_addresses_success_custom_count(self, mock_post):
        mock_addresses_custom = [
            {"time": 1600000000, "services": 1, "address": "1.2.3.4", "port": 8333},
            {"time": 1600000001, "services": 1, "address": "5.6.7.8", "port": 8333}
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_addresses_custom, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        count = 5
        result = self.client.get_node_addresses(count=count)
        self.assertEqual(result, mock_addresses_custom)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getnodeaddresses')
        self.assertEqual(kwargs['json']['params'], [count])

    @patch('requests.Session.post')
    def test_get_node_addresses_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -8, 'message': 'Invalid count for getnodeaddresses'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.get_node_addresses(count=-1) # Invalid count
        self.assertEqual(context.exception.rpc_error_code, -8)
        self.assertIn('Invalid count for getnodeaddresses', str(context.exception))

    @patch('requests.Session.post')
    def test_get_node_addresses_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for getnodeaddresses")
        with self.assertRaises(RequestException):
            self.client.get_node_addresses()

    # Tests for get_peer_info
    @patch('requests.Session.post')
    def test_get_peer_info_success(self, mock_post):
        mock_peer_data = [
            {"id": 0, "addr": "1.2.3.4:8333", "services": "NODE_NETWORK", "subver": "/Satoshi:0.22.0/"}
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_peer_data, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.get_peer_info()
        self.assertEqual(result, mock_peer_data)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'getpeerinfo')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_get_peer_info_rpc_error(self, mock_post):
        # Unlikely for this command
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError
        mock_response.raise_for_status.side_effect = HTTPError("Server Error for getpeerinfo")
        mock_post.return_value = mock_response
        with self.assertRaises(RequestException):
            self.client.get_peer_info()

    @patch('requests.Session.post')
    def test_get_peer_info_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for getpeerinfo")
        with self.assertRaises(RequestException):
            self.client.get_peer_info()

    # Network RPCs - Set 3
    @patch('requests.Session.post')
    def test_list_banned_success(self, mock_post):
        mock_banned_list = [{"address": "192.168.0.1/24", "banned_until": 1600000000, "ban_reason": "manual"}]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_banned_list, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.list_banned()
        self.assertEqual(result, mock_banned_list)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'listbanned')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_list_banned_rpc_error(self, mock_post):
        # Unlikely for this command, but good for completeness
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError
        mock_response.raise_for_status.side_effect = HTTPError("Server Error for listbanned")
        mock_post.return_value = mock_response
        with self.assertRaises(RequestException):
            self.client.list_banned()

    @patch('requests.Session.post')
    def test_list_banned_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for listbanned")
        with self.assertRaises(RequestException):
            self.client.list_banned()

    @patch('requests.Session.post')
    def test_ping_success(self, mock_post):
        # ping returns None
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': None, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.ping()
        self.assertIsNone(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'ping')
        self.assertEqual(kwargs['json']['params'], [])

    @patch('requests.Session.post')
    def test_ping_rpc_error(self, mock_post):
        # Unlikely, ping is simple.
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError
        mock_response.raise_for_status.side_effect = HTTPError("Server Error for ping")
        mock_post.return_value = mock_response
        with self.assertRaises(RequestException):
            self.client.ping()

    @patch('requests.Session.post')
    def test_ping_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for ping")
        with self.assertRaises(RequestException):
            self.client.ping()

    @patch('requests.Session.post')
    def test_set_ban_success_default_params(self, mock_post):
        # setban returns None
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': None, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        subnet = "192.168.1.0/24"
        command = "add"
        result = self.client.set_ban(subnet, command) # Defaults bantime=86400, absolute=False
        self.assertIsNone(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'setban')
        self.assertEqual(kwargs['json']['params'], [subnet, command, 86400, False])

    @patch('requests.Session.post')
    def test_set_ban_success_custom_params(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': None, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        subnet = "10.0.0.0/8"
        command = "remove"
        bantime = 0 # To remove immediately
        absolute = True # Though irrelevant for remove
        result = self.client.set_ban(subnet, command, bantime=bantime, absolute=absolute)
        self.assertIsNone(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'setban')
        self.assertEqual(kwargs['json']['params'], [subnet, command, bantime, absolute])

    @patch('requests.Session.post')
    def test_set_ban_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -23, 'message': 'Error: Invalid IP/Subnet'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.set_ban("invalid_subnet", "add")
        self.assertEqual(context.exception.rpc_error_code, -23)
        self.assertIn('Error: Invalid IP/Subnet', str(context.exception))

    @patch('requests.Session.post')
    def test_set_ban_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for setban")
        with self.assertRaises(RequestException):
            self.client.set_ban("1.2.3.4", "add")

    @patch('requests.Session.post')
    def test_set_network_active_success_true(self, mock_post):
        # Returns the new state
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': True, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.set_network_active(True)
        self.assertTrue(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'setnetworkactive')
        self.assertEqual(kwargs['json']['params'], [True])

    @patch('requests.Session.post')
    def test_set_network_active_success_false(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': False, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        result = self.client.set_network_active(False)
        self.assertFalse(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'setnetworkactive')
        self.assertEqual(kwargs['json']['params'], [False])

    @patch('requests.Session.post')
    def test_set_network_active_rpc_error(self, mock_post):
        # Unlikely for this command
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError
        mock_response.raise_for_status.side_effect = HTTPError("Server Error for setnetworkactive")
        mock_post.return_value = mock_response
        with self.assertRaises(RequestException):
            self.client.set_network_active(True)

    @patch('requests.Session.post')
    def test_set_network_active_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for setnetworkactive")
        with self.assertRaises(RequestException):
            self.client.set_network_active(False)

    # Transaction RPCs - Set 2 (Rawtransactions)
    @patch('requests.Session.post')
    def test_analyze_psbt_success(self, mock_post):
        mock_analysis = {"inputs": [], "next": "signer"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_analysis, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        psbt_str = "cHNidP8BAAAA..."
        result = self.client.analyze_psbt(psbt_str)
        self.assertEqual(result, mock_analysis)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'analyzepsbt')
        self.assertEqual(kwargs['json']['params'], [psbt_str])

    @patch('requests.Session.post')
    def test_analyze_psbt_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -22, 'message': 'PSBT decode failed'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.analyze_psbt("invalid_psbt_string")
        self.assertEqual(context.exception.rpc_error_code, -22)
        self.assertIn('PSBT decode failed', str(context.exception))

    @patch('requests.Session.post')
    def test_analyze_psbt_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for analyzepsbt")
        with self.assertRaises(RequestException):
            self.client.analyze_psbt("any_psbt")

    @patch('requests.Session.post')
    def test_combine_psbt_success(self, mock_post):
        mock_combined_psbt = "cHNidP8COMBINED..."
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_combined_psbt, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        psbt_list = ["cHNidP8BAAAA...", "cHNidP8BBBBB..."]
        result = self.client.combine_psbt(psbt_list)
        self.assertEqual(result, mock_combined_psbt)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'combinepsbt')
        self.assertEqual(kwargs['json']['params'], [psbt_list])

    @patch('requests.Session.post')
    def test_combine_psbt_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -8, 'message': 'Invalid PSBT provided'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.combine_psbt(["invalid_psbt1", "invalid_psbt2"])
        self.assertEqual(context.exception.rpc_error_code, -8)
        self.assertIn('Invalid PSBT provided', str(context.exception))

    @patch('requests.Session.post')
    def test_combine_psbt_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for combinepsbt")
        with self.assertRaises(RequestException):
            self.client.combine_psbt(["psbt1", "psbt2"])

    @patch('requests.Session.post')
    def test_combine_raw_transaction_success(self, mock_post):
        mock_combined_tx_hex = "02000000COMBINED..."
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_combined_tx_hex, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        tx_hex_list = ["01000000...", "01000001..."]
        result = self.client.combine_raw_transaction(tx_hex_list)
        self.assertEqual(result, mock_combined_tx_hex)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'combinerawtransaction')
        self.assertEqual(kwargs['json']['params'], [tx_hex_list])

    @patch('requests.Session.post')
    def test_combine_raw_transaction_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -22, 'message': 'TX decode failed for combinerawtransaction'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.combine_raw_transaction(["invalid_hex1", "invalid_hex2"])
        self.assertEqual(context.exception.rpc_error_code, -22)
        self.assertIn('TX decode failed for combinerawtransaction', str(context.exception))

    @patch('requests.Session.post')
    def test_combine_raw_transaction_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for combinerawtransaction")
        with self.assertRaises(RequestException):
            self.client.combine_raw_transaction(["hex1", "hex2"])

    @patch('requests.Session.post')
    def test_convert_to_psbt_success_default_params(self, mock_post):
        mock_psbt = "cHNidP8CONVERTED..."
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_psbt, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        hexrawtx = "01000000SOMEHEX..."
        result = self.client.convert_to_psbt(hexrawtx) # permitsigdata=False, iswitness=None
        self.assertEqual(result, mock_psbt)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'converttopsbt')
        self.assertEqual(kwargs['json']['params'], [hexrawtx, False])

    @patch('requests.Session.post')
    def test_convert_to_psbt_success_with_iswitness(self, mock_post):
        mock_psbt_witness = "cHNidP8WITNESS..."
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': mock_psbt_witness, 'error': None, 'id': 'python-bitcoin-sdk'}
        mock_post.return_value = mock_response

        hexrawtx = "02000000WITNESS_HEX..."
        result = self.client.convert_to_psbt(hexrawtx, permitsigdata=True, iswitness=True)
        self.assertEqual(result, mock_psbt_witness)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['method'], 'converttopsbt')
        self.assertEqual(kwargs['json']['params'], [hexrawtx, True, True])

    @patch('requests.Session.post')
    def test_convert_to_psbt_rpc_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': None,
            'error': {'code': -22, 'message': 'TX parse error for converttopsbt'},
            'id': 'python-bitcoin-sdk'
        }
        mock_post.return_value = mock_response

        with self.assertRaises(BitcoinRPCError) as context:
            self.client.convert_to_psbt("invalid_raw_hex_for_psbt")
        self.assertEqual(context.exception.rpc_error_code, -22)
        self.assertIn('TX parse error for converttopsbt', str(context.exception))

    @patch('requests.Session.post')
    def test_convert_to_psbt_network_error(self, mock_post):
        mock_post.side_effect = RequestException("Network error for converttopsbt")
        with self.assertRaises(RequestException):
            self.client.convert_to_psbt("some_hex_for_psbt")

if __name__ == '__main__':
    unittest.main()
