#!/usr/bin/env python3
from bitcoinrpc import Bitcoin
from configparser import ConfigParser
import time
from datetime import datetime
import numpy as np
from typing import List, Dict

def load_config() -> tuple[str, str]:
    """Load Bitcoin RPC credentials from config file."""
    config = ConfigParser()
    config.read("/home/julian/bitcoin/bitcoinRpc/config/bitcoinPy.conf")
    return config['settings']['user'], config['settings']['password']

def test_block_operations(bitcoin: Bitcoin) -> None:
    """Test various block-related operations."""
    try:
        print("\n=== Testing Block Operations ===")
        
        # Get current block height
        current_height = bitcoin.getBlockCount()
        print(f"Current block height: {current_height}")
        
        # Get latest block details
        print("\nFetching latest block...")
        latest_block = bitcoin.getLatestBlock()
        if latest_block:
            print(f"Latest block info:")
            print(f"Height: {latest_block.height}")
            print(f"Hash: {latest_block.hash}")
            print(f"Transaction count: {len(latest_block.transactions)}")
            print(f"Size: {latest_block.size} bytes")
            print(f"Time: {datetime.fromtimestamp(latest_block.time)}")
            print(f"Total value: {latest_block.totalValue / 1e8:.2f} BTC")
            print(f"Total fees: {latest_block.totalFees / 1e8:.8f} BTC")
            print(f"Mean fee rate: {latest_block.meanFeeRate:.2f} sat/vB")
        
        # Analyze a range of recent blocks
        print("\nAnalyzing last 5 blocks:")
        for block in bitcoin.iterateBlocks(current_height - 4, current_height + 1):
            if block and block.transactions:
                # Use the correct properties from the Block class
                total_value = sum(output.value for tx in block.transactions for output in tx.outputs)
                print(f"Block {block.height}:")
                print(f"  Transactions: {len(block.transactions)}")
                print(f"  Total value: {total_value / 1e8:.2f} BTC")
                print(f"  Total fees: {block.totalFees / 1e8:.8f} BTC")
                print(f"  Mean fee rate: {block.meanFeeRate:.2f} sat/vB")
                print(f"  Size: {block.size:,} bytes")
                
    except Exception as e:
        print(f"Error in block operations test: {str(e)}")
        raise

def analyze_mempool(bitcoin: Bitcoin) -> None:
    """Analyze current mempool state."""
    print("\n=== Analyzing Mempool ===")
    
    # Get mempool fee rates
    fee_rates = bitcoin.getMempoolFees()
    if fee_rates:
        print(f"\nFee rate statistics (sat/vB):")
        print(f"Min fee rate: {min(fee_rates):.2f}")
        print(f"Max fee rate: {max(fee_rates):.2f}")
        print(f"Median fee rate: {np.median(fee_rates):.2f}")
        print(f"Mean fee rate: {np.mean(fee_rates):.2f}")
    
    # Get mempool info
    mempool = bitcoin.getMempool()
    print(f"\nTotal transactions in mempool: {len(mempool)}")
    
    # Analyze transaction sizes
    sizes = [tx_data['vsize'] for tx_data in mempool.values()]
    if sizes:
        print(f"Average transaction vsize: {np.mean(sizes):.2f}")
        print(f"Largest transaction vsize: {max(sizes)}")
        print(f"Smallest transaction vsize: {min(sizes)}")

def monitor_price_changes(bitcoin: Bitcoin, intervals: int = 5, delay: int = 60) -> None:
    """Monitor Bitcoin price changes over time."""
    print(f"\n=== Monitoring Price Changes ({intervals} intervals) ===")
    
    prices = []
    timestamps = []
    
    for i in range(intervals):
        price, sats_per_dollar = bitcoin.getPrice()
        current_time = datetime.now()
        
        prices.append(price)
        timestamps.append(current_time)
        
        print(f"Time: {current_time.strftime('%H:%M:%S')}")
        print(f"Price: ${price:,}")
        print(f"Sats per dollar: {sats_per_dollar:,}")
        
        if i < intervals - 1:
            time.sleep(delay)
    
    # Calculate price statistics
    if len(prices) > 1:
        price_changes = np.diff(prices)
        print("\nPrice change statistics:")
        print(f"Max increase: ${max(price_changes):,.2f}")
        print(f"Max decrease: ${min(price_changes):,.2f}")
        print(f"Average change: ${np.mean(price_changes):,.2f}")

def analyze_utxo_set(bitcoin: Bitcoin) -> None:
    """Analyze the current UTXO set."""
    print("\n=== Analyzing UTXO Set ===")
    
    utxo_info = bitcoin.getUtxoSetInfo()
    print(f"Total UTXOs: {utxo_info['txouts']:,}")
    print(f"Total size: {utxo_info['disk_size'] / 1024 / 1024:.2f} MB")
    print(f"Total amount: {utxo_info['total_amount']:,.8f} BTC")
    print(f"Block height: {utxo_info['height']}")
    print(f"Best block hash: {utxo_info['bestblock']}")

def main():
    """Main function to run all tests."""
    try:
        # Initialize Bitcoin client
        user, password = load_config()
        bitcoin = Bitcoin(user, password)
        
        # Run tests
        test_block_operations(bitcoin)
        analyze_mempool(bitcoin)
        monitor_price_changes(bitcoin, intervals=3, delay=30)  # 3 intervals, 30 seconds each
        analyze_utxo_set(bitcoin)
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main()