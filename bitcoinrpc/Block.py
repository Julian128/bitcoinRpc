import numpy as np
from dataclasses import dataclass


class BlockLite:
    def __init__(self, block: dict):
        self.height = block['height']
        self.version = block['version']
        self.merkleroot = block['merkleroot']
        self.time = block['time']
        self.mediantime = block['mediantime']*1000
        self.nonce = block['nonce']
        self.bits = block['bits']
        self.size = block['size']  # bytes
        self.txs = block['nTx']
        self.weight = block['weight']
        self.difficulty = block['difficulty']
        self.hash = block['hash']
        self.chainwork = block['chainwork']
        
    def __repr__(self) -> str:
        return f"block: {self.height}"
    
@dataclass
class Script:
    script: bytes
    
    @classmethod
    def from_hex(cls, hex_str: str) -> 'Script':
        return cls(bytes.fromhex(hex_str))

@dataclass
class Input:
    prev_txid: str             # Previous transaction ID being spent
    prev_vout_index: np.int16  # Output index in previous transaction
    script_sig: Script         # Unlocking script
    sequence: np.int32         # For RBF and timelocks
    witness: list[bytes]       # Segregated witness data
    value: np.int64           # Value of the input in satoshis

@dataclass
class Output:
    value: np.int64           # Amount in satoshis
    script_pubkey: Script     # Locking script
    n: np.int16              # Output index
    

class Transaction:
    def __init__(self, tx: dict):
        self.txid = tx['txid']
        self.version = tx['version']
        self.locktime = tx.get('locktime', 0)
        
        # Parse inputs
        self.inputs = []
        for vin in tx['vin']:
            if 'coinbase' in vin:
                # Special handling for coinbase
                self.inputs.append(Input(
                    prev_txid='0'*64,
                    prev_vout_index=np.int16(-1),
                    script_sig=Script(bytes.fromhex(vin['coinbase'])),
                    sequence=np.int64(vin.get('sequence', 0)),
                    witness=[],
                    value=np.int64(0)
                ))
            else:
                self.inputs.append(Input(
                    prev_txid=vin['txid'],
                    prev_vout_index=np.int16(vin['vout']),
                    script_sig=Script.from_hex(vin.get('scriptSig', {}).get('hex', '')),
                    sequence=np.int64(vin.get('sequence', 0)),
                    witness=[bytes.fromhex(w) for w in vin.get('witness', [])],
                    value=np.int64(vin.get('value', 0) * 1e8)
                ))

        # Parse outputs
        self.outputs = []
        for i, vout in enumerate(tx['vout']):
            self.outputs.append(Output(
                value=np.int64(vout['value'] * 1e8),
                script_pubkey=Script.from_hex(vout['scriptPubKey']['hex']),
                n=np.int16(i)
            ))
        self.size = tx['size']
        self.weight = tx['weight']
        self.isCoinbase = 'coinbase' in tx['vin'][0]

    @property
    def fee(self) -> np.int64:
        if self.isCoinbase:
            return np.int64(0)
        return np.int64(sum(inp.value for inp in self.inputs) - 
                       sum(out.value for out in self.outputs))

    @property
    def feeRate(self) -> float:
        return self.fee / self.vbytes

    @property
    def vbytes(self) -> float:
        return self.weight / 4

    def __repr__(self):
        return f"tx: {self.txid}, fee: {self.fee}, feeRate: {self.feeRate}"
        
class Block(BlockLite):
    def __init__(self, block: dict, price: tuple[int, int], txs: list[Transaction]):
        super().__init__(block)
        self.transactions: list[Transaction] = list(txs)
        self.price = price

    @property
    def utxoValues(self) -> list[float]:
        utxoValues = []
        for tx in self.transactions:
            for output in tx.outputs:
                utxoValues.append(float(output.value))
        return utxoValues

    @property
    def totalFees(self) -> float:
        return sum(tx.fee for tx in self.transactions)
    
    @property
    def meanFeeRate(self) -> float:
        return np.mean([tx.feeRate for tx in self.transactions])
    
    @property
    def medianFeeRate(self) -> float:
        return np.median([tx.feeRate for tx in self.transactions])
    
    @property
    def totalValue(self) -> float:
        return sum(self.utxoValues)

    def __repr__(self) -> str:
        result = f"block: {self.height}\n"
        result += f"price: {self.price}\n"
        result += f"fees: {self.totalFees}\n"
        result += f"meanFeeRate: {self.meanFeeRate}\n"
        result += f"medianFeeRate: {self.medianFeeRate}\n"
        result += f"totalValue: {self.totalValue}\n"
        result += f"size: {self.size}\n"
        result += f"weight: {self.weight}\n"
        return result