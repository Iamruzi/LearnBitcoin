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

    # Blockchain RPCs - Set 1
    def get_best_block_hash(self):
        return self._rpc_request("getbestblockhash")

    def get_blockchain_info(self):
        return self._rpc_request("getblockchaininfo")

    def get_block_filter(self, block_hash, filter_type="basic"):
        return self._rpc_request("getblockfilter", [block_hash, filter_type])

    def get_block_header(self, block_hash, verbose=True):
        return self._rpc_request("getblockheader", [block_hash, verbose])

    def get_block_stats(self, hash_or_height, stats=None):
        params = [hash_or_height]
        if stats is not None:
            params.append(stats)
        return self._rpc_request("getblockstats", params)

    # Blockchain RPCs - Set 2
    def get_chain_tips(self): # Renamed to avoid conflict with potential getchaintips attribute
        return self._rpc_request("getchaintips")

    def get_chain_tx_stats(self, nblocks=None, block_hash=None): # Renamed for clarity
        params = []
        if nblocks is not None:
            params.append(nblocks)
            if block_hash is not None: # block_hash is only relevant if nblocks is specified
                params.append(block_hash)
        # If params is empty, it calls with no arguments, e.g. getchaintxstats
        # If only nblocks, e.g. getchaintxstats nblocks
        # If both, e.g. getchaintxstats nblocks block_hash
        return self._rpc_request("getchaintxstats", params if params else None)


    def get_difficulty(self):
        return self._rpc_request("getdifficulty")

    def get_mempool_ancestors(self, txid, verbose=False):
        return self._rpc_request("getmempoolancestors", [txid, verbose])

    def get_mempool_descendants(self, txid, verbose=False):
        return self._rpc_request("getmempooldescendants", [txid, verbose])

    # Blockchain RPCs - Set 3
    def get_mempool_entry(self, txid): # Renamed for consistency
        return self._rpc_request("getmempoolentry", [txid])

    def get_mempool_info(self): # Renamed for consistency
        return self._rpc_request("getmempoolinfo")

    def get_raw_mempool(self, verbose=False, mempool_sequence=False): # Renamed for consistency
        params = [verbose]
        if verbose: # mempool_sequence is only used if verbose is True
            params.append(mempool_sequence)
        return self._rpc_request("getrawmempool", params)

    def get_tx_out(self, txid, vout, include_mempool=True): # Renamed for consistency
        return self._rpc_request("gettxout", [txid, vout, include_mempool])

    # Blockchain RPCs - Set 4
    def get_tx_out_proof(self, txids, block_hash=None): # Renamed
        params = [txids]
        if block_hash is not None:
            params.append(block_hash)
        return self._rpc_request("gettxoutproof", params)

    def get_tx_out_set_info(self, hash_type='hash_serialized_2', hash_or_height=None, use_index=None): # Renamed
        params = [hash_type]
        # Append hash_or_height only if it's provided or if use_index is provided (as use_index depends on hash_or_height)
        if hash_or_height is not None or use_index is not None:
            params.append(hash_or_height)
        # Append use_index only if it's provided
        if use_index is not None:
            params.append(use_index)
        return self._rpc_request("gettxoutsetinfo", params)

    def precious_block(self, block_hash): # Renamed
        return self._rpc_request("preciousblock", [block_hash])

    def prune_blockchain(self, height): # Renamed
        return self._rpc_request("pruneblockchain", [height])

    def save_mempool(self):
        return self._rpc_request("savemempool")

    # Blockchain RPCs - Set 5
    def scan_tx_out_set(self, action, scan_objects): # Renamed
        """
        Scans the unspent transaction output set for entries that match certain output descriptors.
        Example scan_objects: ["addr(1Address...)", {"desc": "wpkh(02PublicKey...)"}]
        """
        return self._rpc_request("scantxoutset", [action, scan_objects])

    def verify_chain(self, checklevel=3, nblocks=6): # Renamed
        """
        Verifies blockchain database.
        Default checklevel (0-4) is 3. Default nblocks (0 means all) is 6.
        """
        return self._rpc_request("verifychain", [checklevel, nblocks])

    def verify_tx_out_proof(self, proof): # Renamed
        """
        Verifies that a proof points to a transaction in a block, returning the transaction it commits to.
        """
        return self._rpc_request("verifytxoutproof", [proof])

    # Control RPCs - Set 1
    def get_memory_info(self, mode='stats'): # Renamed
        """
        Returns information about memory usage.
        Mode can be "stats" or "mallocinfo".
        """
        return self._rpc_request("getmemoryinfo", [mode])

    def get_rpc_info(self): # Renamed
        """
        Returns runtime details of the RPC server.
        """
        return self._rpc_request("getrpcinfo")

    def help(self, command=None):
        """
        Returns help message for a specific command or all commands.
        """
        params = []
        if command is not None:
            params.append(command)
        return self._rpc_request("help", params if params else None)

    # Control RPCs - Set 2
    def logging(self, include=None, exclude=None, add=None, remove=None, clear=None, stat=None):
        """
        Gets and sets the logging configuration.
        When called without arguments, returns the list of categories with status that are currently being debug logged.
        When called with arguments, updates the logging configuration.
        All arguments are optional.
        include, exclude, add, remove: lists of category strings.
        clear, stat: booleans.
        """
        # Passing None for list arguments will be sent as null by JSON-RPC, which is fine.
        # For boolean flags, if None, they should not be passed or passed as a default that implies no change.
        # However, the `logging` RPC seems to take all arguments positionally if any are provided.
        # The exact behavior for None vs. default booleans (e.g. False) might differ by RPC version.
        # We will pass them as is; if None, they become null. User should pass explicit True/False for booleans.
        params = [include, exclude, add, remove, clear, stat]

        # To avoid sending trailing nulls if they are not meant to override,
        # we could try to find the last non-None argument and slice params.
        # However, for `logging` it might be that all positions are expected if any arg is used.
        # The simple approach is to send all, and rely on Bitcoin Core to interpret nulls as "no change" or default.
        # If strict positional non-nulls are required, the user must supply them.
        # A common pattern for `logging` is to query with no args, or set with specific args.
        if all(p is None for p in params): # If all args are None, call with no params to query
            return self._rpc_request("logging", None)
        else:
            return self._rpc_request("logging", params)

    def stop(self):
        """
        Requests a graceful shutdown of Bitcoin Core.
        """
        return self._rpc_request("stop")

    def uptime(self):
        """
        Returns the total runtime of the server in seconds.
        """
        return self._rpc_request("uptime")

    # Generating RPCs
    def generate_block(self, output, transactions): # Renamed
        """
        Mine a block with a specific output script and a list of transactions.
        output: The address or script (hex) to send the coinbase reward to.
        transactions: A list of raw transaction hex strings to include in the block.
        Returns a dictionary with block hash and other info.
        """
        return self._rpc_request("generateblock", [output, transactions])

    def generate_to_address(self, nblocks, address, maxtries=1000000): # Renamed
        """
        Mine blocks immediately to a specified address.
        nblocks: How many blocks are generated.
        address: The address to send the coinbase reward to.
        maxtries: How many iterations to try (default 1000000).
        Returns a list of block hashes.
        """
        return self._rpc_request("generatetoaddress", [nblocks, address, maxtries])

    def generate_to_descriptor(self, num_blocks, descriptor, maxtries=1000000): # Renamed
        """
        Mine blocks immediately to a specified descriptor.
        num_blocks: How many blocks are generated.
        descriptor: The descriptor to send the coinbase reward to.
        maxtries: How many iterations to try (default 1000000).
        Returns a list of block hashes.
        """
        return self._rpc_request("generatetodescriptor", [num_blocks, descriptor, maxtries])

    # Transaction RPCs - Set 2 (Rawtransactions)
    def analyze_psbt(self, psbt): # Renamed
        """
        Analyzes and provides information about the current status of a PSBT and its inputs.
        psbt: A base64-encoded Partially Signed Bitcoin Transaction.
        """
        return self._rpc_request("analyzepsbt", [psbt])

    def combine_psbt(self, txs): # Renamed
        """
        Merge multiple PSBTs into one.
        txs: A list of base64-encoded PSBT strings.
        """
        return self._rpc_request("combinepsbt", [txs])

    def combine_raw_transaction(self, txs): # Renamed
        """
        Combine multiple partially signed transactions into one transaction.
        txs: A list of raw transaction hex strings.
        """
        return self._rpc_request("combinerawtransaction", [txs])

    def convert_to_psbt(self, hexrawtx, permitsigdata=False, iswitness=None): # Renamed
        """
        Converts a network serialized transaction to a PSBT.
        hexrawtx: The hex string of a raw transaction.
        permitsigdata: If true, any signatures in the input will be discarded and conversion
                       will continue. If false, RPC will fail if signatures are present.
        iswitness: Whether the transaction hex is witness serialized.
                   If not specified, an attempt is made to derive the information automatically.
        """
        params = [hexrawtx, permitsigdata]
        if iswitness is not None:
            params.append(iswitness)
        return self._rpc_request("converttopsbt", params)

    # Network RPCs - Set 1
    def add_node(self, node, command): # Renamed
        """
        Attempts to add or remove a node from the addnode list.
        Or try a connection to a node once.
        Commands: "add", "remove", "onetry".
        Returns None on success.
        """
        return self._rpc_request("addnode", [node, command])

    def clear_banned(self): # Renamed
        """
        Clear all banned IPs.
        Returns None on success.
        """
        return self._rpc_request("clearbanned")

    def disconnect_node(self, address=None, nodeid=None): # Renamed
        """
        Immediately disconnects from the specified peer node.
        Specify either address (host:port) or nodeid.
        If both are provided, nodeid takes precedence.
        Returns None on success.
        """
        # Bitcoin Core RPC `disconnectnode ( [address] [nodeid] )`
        # If nodeid is provided, address is ignored.
        # If only address, it's used.
        # If neither, error. The SDK method should enforce at least one.
        # For simplicity, we pass both; Core decides. User should provide one.
        params = []
        if address is not None:
            params.append(address)
        if nodeid is not None:
            # If address was also given, it's already in params.
            # If only nodeid, then params was empty.
            # The RPC expects address first if both are somehow passed this way.
            # However, it's more typical to provide one or the other.
            # To ensure correct positional args if nodeid is the only identifier:
            if not params: # Only nodeid is given
                 params.append(None) # Placeholder for address
            params.append(nodeid)

        if not params: # Should not happen if SDK user provides at least one
            raise ValueError("Either address or nodeid must be provided to disconnectnode")

        return self._rpc_request("disconnectnode", params)

    def get_added_node_info(self, node=None): # Renamed
        """
        Returns information about the given added node, or all added nodes
        (except onetry nodes) if no node is specified.
        """
        params = []
        if node is not None:
            params.append(node)
        return self._rpc_request("getaddednodeinfo", params if params else None)

    def get_connection_count(self): # Renamed
        """
        Returns the number of connections to other nodes.
        """
        return self._rpc_request("getconnectioncount")

    # Network RPCs - Set 2
    def get_net_totals(self): # Renamed
        """
        Returns information about network traffic, including bytes in, bytes out,
        and current time.
        """
        return self._rpc_request("getnettotals")

    def get_network_info(self): # Renamed
        """
        Returns an object containing various state info regarding P2P networking.
        """
        return self._rpc_request("getnetworkinfo")

    def get_node_addresses(self, count=1): # Renamed
        """
        Return known addresses, after trying count times to connect to a random node.
        count: The number of tries to connect to a node to gather addresses from.
        """
        return self._rpc_request("getnodeaddresses", [count])

    def get_peer_info(self): # Renamed
        """
        Returns data about each connected network node as a json array of objects.
        """
        return self._rpc_request("getpeerinfo")

    # Network RPCs - Set 3
    def list_banned(self): # Renamed
        """
        List all banned IPs/Subnets.
        """
        return self._rpc_request("listbanned")

    def ping(self):
        """
        Requests that a ping be sent to all other nodes, to measure ping time.
        Returns None on success. Bitcoin Core will respond once all pings are sent.
        """
        return self._rpc_request("ping")

    def set_ban(self, subnet, command, bantime=86400, absolute=False): # Renamed
        """
        Attempts to add or remove a IP/Subnet from the banned list.
        subnet: The IP/Subnet (see getpeerinfo for nodes) with an optional netmask (e.g. /24)
        command: 'add' to add an IP/Subnet to the list, 'remove' to remove an IP/Subnet from the list
        bantime: Time in seconds how long (or until when if [absolute] is true) the IP is banned (0 or empty means using the default time of 24h which can also be overwritten by the -bantime startup argument).
        absolute: If true, the bantime is an absolute timestamp in seconds since 1970-01-01 UTC.
        Returns None on success.
        """
        return self._rpc_request("setban", [subnet, command, bantime, absolute])

    def set_network_active(self, state): # Renamed
        """
        Disable/enable all p2p network activity.
        state: true to enable networking, false to disable
        Returns the new state.
        """
        return self._rpc_request("setnetworkactive", [state])

    # Mining RPCs
    def get_block_template(self, rules=None): # Renamed
        """
        Returns data needed to construct a block to work on.
        rules: A list of strings, supported rules (e.g., "segwit").
        """
        template_request_object = {}
        if rules is not None:
            template_request_object['rules'] = rules
        # Bitcoin Core expects a JSON object as the first parameter for 'getblocktemplate'.
        # Even if rules is None, an empty object {} might be required.
        return self._rpc_request("getblocktemplate", [template_request_object])

    def get_mining_info(self): # Renamed
        """
        Returns a json object containing mining-related information.
        """
        return self._rpc_request("getmininginfo")

    def get_network_hash_ps(self, nblocks=-1, height=-1): # Renamed
        """
        Returns the estimated network hashes per second based on the last n blocks.
        nblocks: Number of blocks, or -1 for default (120).
        height: Block height to estimate from, or -1 for current best block.
        """
        return self._rpc_request("getnetworkhashps", [nblocks, height])

    def prioritise_transaction(self, txid, fee_delta, dummy=None): # Renamed
        """
        Accepts the transaction into mined blocks at a higher (or lower) priority.
        txid: The transaction id.
        dummy: Kept for positional argument compatibility, pass None or 0. (Historically priority_delta)
        fee_delta: The fee value (in satoshis) to add (or subtract) from the transaction's fee.
        Returns true if successful.
        """
        return self._rpc_request("prioritisetransaction", [txid, dummy, fee_delta])

    def submit_block(self, hexdata, dummy=None): # Renamed
        """
        Attempts to submit new block to network.
        hexdata: The hex-encoded block data.
        dummy: Optional, for compatibility with older versions (was a dictionary). Pass None.
        Returns None on success, or an error string.
        """
        # If dummy is truly ignored or should be omitted if None, this could be:
        # params = [hexdata]
        # if dummy is not None: params.append(dummy)
        # However, to match the common RPC call structure of bitcoin-cli, often a null is passed.
        return self._rpc_request("submitblock", [hexdata, dummy])

    def submit_header(self, hexdata):
        """
        Decode and submit a new block header to the network.
        hexdata: The hex-encoded block header.
        Returns None on success.
        """
        return self._rpc_request("submitheader", [hexdata])
