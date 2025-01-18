from decimal import Decimal
from src.bitcoin import Bitcoin
from configparser import ConfigParser

config = ConfigParser()
config.read("/home/julian/bitcoin/bitcoinPy/bitcoinPy.conf")
user = config['settings']['user']
password = config['settings']['password']
host = config['settings']['host']
port = config['settings']['port']
bitcoin = Bitcoin(user, password, host, port)
mempool = bitcoin.getMempoolDetailed()

fee_rates = []
sizes = []
for txid, tx_info in mempool.items():
    # Fee rate in satoshis per virtual byte
    fee_rate = tx_info['fees']['modified'] / tx_info['vsize'] * Decimal(1e8)
    fee_rates.append(fee_rate)
    sizes.append(tx_info['vsize'])

# Basic statistics
avg_fee_rate = sum(fee_rates) / len(fee_rates)
total_size = sum(sizes)

print(avg_fee_rate)
print(total_size)

# Sort transactions by fee rate (highest to lowest)
sorted_txs = sorted(
    mempool.items(),
    key=lambda x: x[1]['fees']['modified'] / x[1]['vsize'],
    reverse=True
)

# Get top 10 highest fee-paying transactions
top_10_fees = sorted_txs[:10]
for txid, tx_info in top_10_fees:
    fee_rate = tx_info['fees']['modified'] / tx_info['vsize']
    print(f"TXID: {txid[:8]}... | Fee Rate: {fee_rate:.2f} sat/vB | Size: {tx_info['vsize']} vB")
