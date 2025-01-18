from concurrent.futures import ThreadPoolExecutor, as_completed
from bitcoinrpc.authproxy import AuthServiceProxy
import time
import pycoingecko
import numpy as np
import requests

from src.block import Block, BlockDetailed, Transaction


class Bitcoin():
    def __init__(self, user, password, host, port):
        self.rpcConnection = AuthServiceProxy(f"http://{user}:{password}@{host}:{port}", timeout=300)
        self.priceApi = pycoingecko.CoinGeckoAPI()
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.printInfo()

    def printInfo(self):
            print("Connecting to Bitcoin Core...\n############################################################")
            info = self.getBlockchainInfo()
            print(f"Chain: {info['chain']}")
            print(f"Block height: {info['blocks']}")
            print(f"Chainwork: {info['chainwork']}")
            print(f"Pruned: {info['pruned']}")
            print(f"Size on disk in GB: {info['size_on_disk'] / 1024**3}")
            print(f"Block download progress: {info['blocks'] / info['headers']}")
            print(f"Price: {self.getPrice()}")
            print("############################################################")

    def rpc(self, method: str, *args):
        for _ in range(10):
            try:
                return self.rpcConnection.__getattr__(method)(*args)
            except Exception as e:
                # print(f"Exception in rpc call: {e}")
                # pass
                self.rpcConnection = AuthServiceProxy(f"http://{self.user}:{self.password}@{self.host}:{self.port}")
        print(f"RPC request failed: {method} ({args})")
        exit(1)

    def getBlockCount(self):
        return self.rpc("getblockcount")
    
    def getBlockchainInfo(self):
        return self.rpc("getblockchaininfo")
    
    def getUtxoSetInfo(self) -> dict:
        return self.rpc("gettxoutsetinfo", "none")

    def getBlockFromHeight(self, blockHeight: int) -> Block:
        blockHash = self.rpc("getblockhash", blockHeight)
        block = self.rpc("getblock", blockHash, 2)
        if block:
            block = Block(block)
            return block

        raise("Block not found")

    def getBlockDetailedFromHeight(self, blockHeight: int) -> BlockDetailed:
        blockHash = self.rpc("getblockhash", blockHeight)
        block = self.rpc("getblock", blockHash, 2)

        if block:
            block = BlockDetailed(block, self.getPriceFromBlockTimestamp(block), self.buildTxs(block["tx"]))
            print(f"retrieved block {blockHeight}")
            return block

        raise("Block not found")

    def getLatestBlock(self) -> Block:
        return self.getBlockFromHeight(self.getBlockCount())

    def getLatestBlockDetailed(self) -> BlockDetailed:
        return self.getBlockDetailedFromHeight(self.getBlockCount())

    def iterateBlocks(self, start=0, stop=0, stepSize=1):
        if stop == 0:
            stop = self.getBlockCount()
        for i in range(start, stop, stepSize):
            block = self.getBlockFromHeight(i)
            yield block

    def iterateBlocksDetailed(self, start=0, stop=0, stepSize=1):
        if stop == 0:
            stop = self.getBlockCount()
        for i in range(start, stop, stepSize):
            block = self.getBlockDetailedFromHeightMulti(i)
            yield block

    def getBlocksDetailed(self, start=0, stop=0, stepSize=1) -> list[BlockDetailed]:
        if stop == 0:
            stop = self.getBlockCount()
        
        blocks = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all blocks to the executor
            future_blocks = [
                executor.submit(self.getBlockDetailedFromHeightMulti, height) 
                for height in range(start, stop, stepSize)
            ]
            
            # As they complete, add them to our blocks list
            for future in as_completed(future_blocks):
                try:
                    block = future.result()
                    blocks.append(block)
                except Exception as e:
                    print(f"Error processing block: {e}")
                    
        # Sort blocks by height before returning
        blocks.sort(key=lambda x: x.height)
        return blocks

    def getBlockDetailedFromHeightMulti(self, blockHeight: int) -> BlockDetailed:
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_hash = executor.submit(self.rpc, "getblockhash", blockHeight)
            blockHash = future_hash.result()
            
            if not blockHash:
                raise Exception("Block hash not found")

            # parallelize the block data, price, and transaction fetching
            future_block = executor.submit(self.rpc, "getblock", blockHash, 2)
            
            block = future_block.result()
            if block:
                # Parallelize price and transaction processing
                future_price = executor.submit(self.getPriceFromBlockTimestamp, block)
                future_txs = executor.submit(self.buildTxs, block["tx"])
                
                # Wait for all results
                price = future_price.result()
                txs = future_txs.result()
                
                block = BlockDetailed(block, price, txs)
                print(f"retrieved block {blockHeight}")
                return block

            raise Exception("Block not found")            

    def iterateLatestBlocks(self, nBlocks=100):
        start = self.getBlockCount()
        for i in range(nBlocks):
            block = self.getBlockFromHeight(start-i)
            yield block

    def iterateLatestBlocksDetailed(self, nBlocks=100):
        start = self.getBlockCount()
        for i in range(nBlocks):
            block = self.getBlockDetailedFromHeight(start-i)
            yield block

    def iterateBlocksForAlerts(self, nBlocks=100):
        start = self.getBlockCount() - 1
        for i in range(nBlocks):
            block = self.getBlockFromHeight(start-i)
            yield block

    def getBlockValue(self, block: Block):
        return sum([sum(out['value'] for out in tx['vout']) for tx in block['tx'][1:]])

    def getBlockUtxoValues(self, block) -> list[int]:
        utxoValues = []
        for tx in block["tx"]:
            if len(tx["vout"]) > 2:
                continue
            for output in tx["vout"]:
                utxoValues.append(float(output["value"]))
        return utxoValues
    
    def getUtxosFromBlock(self, block):
        utxos = []
        for tx in block["tx"]:
            for output in tx["vout"]:
                utxos.append(output)
        return utxos
    
    def getInputsFromBlock(self, block):
        inputs = []
        for tx in block["tx"]:
            for input in tx["vin"]:
                inputs.append(input)
        return inputs

    def findTxByValue(self, value: int, epsilon=0.001):
        height = self.getBlockCount()
        for block in self.iterateBlocksDetailed(height, height-100, -1):
            for tx in block.transactions:
                for output in tx.outputs:
                    if value - epsilon < output.value < value + epsilon:
                        return output
                    
    def getFeePriorities(self, txIncluded=1500) -> int:
        mempoolTxIds = self.rpc("getrawmempool")
        feeRates = []

        for txid in mempoolTxIds[:txIncluded]:
            try:
                tx = self.rpc("getmempoolentry", txid)
                feeRates.append(float(tx["fees"]["base"] / tx["vsize"]) * 1e8)
            except:
                pass

        return int(np.median(feeRates[:txIncluded]))

    def getLeadingZeroesInBinary(self, block):
        binaryHash = bin(int(block["hash"], 16))[2:].zfill(256)
        leadingZeros = binaryHash.index("1")
        return leadingZeros
    
    def getPrice(self) -> tuple[int, int]:
        btc_data = self.priceApi.get_coin_market_chart_by_id('bitcoin', 'usd', '1minute')
        price = [data[1] for data in btc_data['prices']][-1]
        inversePrice = 1 / price

        return int(price), int(inversePrice*1e8)
    
    def getPriceFromBlockTimestamp(self, block: dict) -> tuple[float, float]:
        timestamp = block["time"] * 1000
        
        url = f"https://api.binance.com/api/v3/klines"
        params = {
            'symbol': 'BTCUSDT',
            'interval': '1m',
            'startTime': timestamp - 60000,  # 1 minute before
            'endTime': timestamp + 60000,    # 1 minute after
            'limit': 2
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if not data:
            return 0, 0
                    
        closest_price = float(data[0][4])
        return int(closest_price), int(1.0 / closest_price * 1e8)


    def getTransaction(self, txid):
        return self.rpc("gettransaction", txid)

    def buildTxs(self, txs: list[dict]) -> list[Transaction]:
        result: list[Transaction] = []
        for tx in txs:
            for vin in tx['vin']:
                if 'coinbase' in vin:
                    continue
                prev_tx = self.rpc("getrawtransaction", vin['txid'], True)
                prev_output = prev_tx['vout'][vin['vout']]
                vin['value'] = prev_output['value']
            result.append(Transaction(tx))

        return result

    def getInputValue(self) -> list[float]:
        values = []
        for vin in self.inputs:
            try:
                prev_tx = Bitcoin.staticRpc("getrawtransaction", vin['txid'], True)
                prev_output = prev_tx['vout'][vin['vout']]
                values.append(float(prev_output['value']))
            except Exception as e:
                print(f"Error getting input value: {e}")
                values.append(0)
        return values
    
    def getMempoolDetailed(self):
        return self.rpc("getrawmempool", True)
    
    # def getMempool(self):
        # return self.rpc("getrawmempool")




if __name__ == "__main__":
    bitcoin = Bitcoin()
    info = bitcoin.getUtxoSetInfo()
    print(info)
