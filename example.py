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


fees = bitcoin.getMempoolFees()