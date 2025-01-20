from bitcoinrpc.BitcoinRpcClient import BitcoinRpcClient
import pycoingecko
import requests

from bitcoinrpc.Block import Block, Transaction

class Bitcoin:
    """Bitcoin client for interacting with Bitcoin Core and related services."""
    
    def __init__(self, user, password, host="localhost", port=8332):
        """Initialize the Bitcoin client with connection parameters."""
        self.client = BitcoinRpcClient(user, password, host, port)
        self.priceApi = pycoingecko.CoinGeckoAPI()
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.printInfo()

    def printInfo(self):
        """Print current blockchain and network information."""
        print("Connecting to Bitcoin Core")
        print("-" * 50)
        info = self.getBlockchainInfo()
        print(f"Chain: {info['chain']}")
        print(f"Block height: {info['blocks']}")
        print(f"Chainwork: {info['chainwork']}")
        print(f"Pruned: {info['pruned']}")
        print(f"Size on disk in GB: {info['size_on_disk'] / 1024**3}")
        print(f"Block download progress: {info['blocks'] / info['headers']}")
        print(f"Price: {self.getPrice()}")
        print("-" * 50)

    # Block Operations
    def getBlockCount(self) -> int:
        """Get the current block height."""
        return self.client.getBlockCount()

    def getBlockFromHeight(self, blockHeight: int) -> Block:
        """Get detailed block information including price and transaction data."""
        try:
            blockHash = self.client.getblockhash(blockHeight)
            if not blockHash:
                raise Exception(f"Block hash not found for height {blockHeight}")
                
            block = self.client.getblock(blockHash, 2)
            if not block:
                raise Exception(f"Block data not found for hash {blockHash}")
                
            price = self.getPriceFromBlockTimestamp(block)
            txs = self.buildTxs(block["tx"])
            block = Block(block, price, txs)
            return block
            
        except Exception as e:
            print(f"Error retrieving block {blockHeight}: {str(e)}")
            raise

    def getLatestBlock(self) -> Block:
        """Get the most recent block."""
        return self.getBlockFromHeight(self.getBlockCount())

    def iterateBlocks(self, start=0, stop=0, stepSize=1):
        """Iterate through blocks within a given range."""
        if stop == 0:
            stop = self.getBlockCount()
        for i in range(start, stop, stepSize):
            yield self.getBlockFromHeight(i)

    def getUtxoSetInfo(self) -> dict:
        """Get information about the current UTXO set."""
        return self.client.gettxoutsetinfo("none")

    # Transaction Operations
    def findTxByValue(self, value: float, epsilon=0.001):
        """Find a transaction output with a specific value within epsilon."""
        height = self.getBlockCount()
        for block in self.iterateBlocksDetailed(height, height-100, -1):
            for tx in block.transactions:
                for output in tx.outputs:
                    if value - epsilon < output.value < value + epsilon:
                        return output

    def getTransaction(self, txid: str):
        """Get transaction details by transaction ID."""
        return self.client.gettransaction(txid)

    def buildTxs(self, txs: list[dict]) -> list[Transaction]:
        """Build transaction objects with input values."""
        result: list[Transaction] = []
        for tx in txs:
            for vin in tx['vin']:
                if 'coinbase' in vin:
                    continue
                prev_tx = self.client.getrawtransaction(vin['txid'], True)
                prev_output = prev_tx['vout'][vin['vout']]
                vin['value'] = prev_output['value']
            result.append(Transaction(tx))
        return result

    # Mempool Operations
    def getMempoolFees(self) -> int:
        """Return all fee rates of mempool transactions."""
        mempoolTxIds = self.getMempoolTxIds()
        feeRates = []

        for txid in mempoolTxIds:
            try:
                tx = self.client.getmempoolentry(txid)
                feeRates.append(float(tx["fees"]["base"] / tx["vsize"]) * 1e8)
            except:
                pass

        return feeRates

    def getMempool(self) -> dict:
        """Get detailed mempool information."""
        return self.client.getrawmempool(True)

    def getMempoolTxIds(self) -> dict:
        """Get mempool transaction ids."""
        return self.client.getrawmempool()

    # Price Operations
    def getPrice(self) -> tuple[int, int]:
        """Get current Bitcoin price from CoinGecko."""
        btc_data = self.priceApi.get_coin_market_chart_by_id('bitcoin', 'usd', '1minute')
        price = [data[1] for data in btc_data['prices']][-1]
        inversePrice = 1 / price
        return int(price), int(inversePrice*1e8)
    
    def getPriceFromBlockTimestamp(self, block: dict) -> tuple[float, float]:
        """Get Bitcoin price at the time of block creation."""
        timestamp = block["time"] * 1000
        
        url = f"https://api.binance.com/api/v3/klines"
        params = {
            'symbol': 'BTCUSDT',
            'interval': '1m',
            'startTime': timestamp - 60000,
            'endTime': timestamp + 60000,
            'limit': 2
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if not data:
            return 0, 0
                    
        closest_price = float(data[0][4])
        return int(closest_price), int(1.0 / closest_price * 1e8)

    # Blockchain Info
    def getBlockchainInfo(self) -> dict:
        """Get general blockchain information."""
        return self.client.getblockchaininfo()
