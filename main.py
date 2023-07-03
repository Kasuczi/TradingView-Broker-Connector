import logging
from datetime import datetime
import ssl
from fastapi import FastAPI, Request
from binance.client import *
from binance.enums import *
import MetaTrader5 as mt5

app = FastAPI()
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')


class Broker:
    """ Blueprint for brokers """
    def __init__(self, symbol):
        self.symbol = symbol

    def open_long(self):
        pass

    def open_short(self):
        pass

    def close_position(self):
        pass

    def calculate_position_size(self):
        pass


class MT5Broker(Broker):
    """ MT5 broker handler """
    def __init__(self, symbol):
        super().__init__(symbol)

    def open_long(self):
        self.close_position()
        lot_size = self.calculate_position_size()
        mt5.Buy(self.symbol, lot_size)
        logging.info("Long position have just been opened: " + self.symbol)

    def open_short(self):
        self.close_position()
        lot_size = self.calculate_position_size()
        mt5.Sell(self.symbol, lot_size)
        logging.info("Short position have just been opened: " + self.symbol)

    def close_position(self):
        mt5.Close(self.symbol)
        logging.info("Positions closed successfully")

    def calculate_position_size(self):
        account_info = mt5.account_info()
        equity = account_info.equity
        lot_size = equity / 10000  # 0.01 lot size for each 100 usd of equity size
        return lot_size


class BinanceBroker(Broker):
    """ Binance broker handler """
    def __init__(self, symbol):
        super().__init__(symbol)
        self.client = Client('api_key', 'api_secret')  # Initialize binance client

    def create_order(self, side, quantity):
        order = self.client.futures_create_order(
            symbol=self.symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
        )
        return order

    def open_long(self):
        self.close_position()
        quantity = self.calculate_position_size()
        self.create_order(SIDE_BUY, quantity)
        logging.info("Long have been just opened on: " + self.symbol)

    def open_short(self):
        self.close_position()
        quantity = self.calculate_position_size()
        self.create_order(SIDE_SELL, quantity)
        logging.info("Short have been just opened on: " + self.symbol)

    def close_position(self):
        positions = self.client.futures_account_balance()
        for position in positions:
            if position['asset'] == 'USDT':  # assuming account is in USDT
                balance = float(position['balance'])
                if balance > 0:
                    self.create_order(SIDE_SELL, balance)
                    logging.info("Closed long on: " + self.symbol)

    def calculate_position_size(self):
        account_info = self.client.futures_account_balance()
        for info in account_info:
            if info['asset'] == 'USDT':  # assuming account is in USDT
                balance = float(info['balance'])
        quantity = balance * 0.1  # 10% of account balance
        return quantity


class BrokerFactory:
    """ Factory for getting the broker """
    @staticmethod
    def get_broker(broker_type, symbol):
        brokers = {
            "M": MT5Broker,
            "B": BinanceBroker
        }
        return brokers[broker_type](symbol)


@app.post("/webhook529376sdgf")
async def process_webhook(request: Request):
    payload_bytes = await request.body()
    payload_str = payload_bytes.decode()
    payload_list = payload_str.splitlines()

    symbol = str(payload_list[0])
    direction = payload_list[1]
    broker_type = payload_list[2]

    broker = BrokerFactory.get_broker(broker_type, symbol)

    logging.info("Received webhook: symbol - " + symbol + ", direction - " + direction + ", broker - " + broker_type)

    if direction == 'buy':
        broker.open_long()
    elif direction == 'sell':
        broker.open_short()

if __name__ == "__main__":
    # pass your mt5 creditentials below
    if mt5.initialize() and mt5.login(1234567, 'password', server='VantageInternational-Live'):
        # print account info
        account_info = mt5.account_info()
        logging.info("Account Info: " + str(account_info))
    else:
        logging.error("MT5 Login failed")

    import uvicorn
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile="certificate.crt", keyfile="private.key")
    uvicorn.run(app, host="195.238.122.243", port=443, ssl_certfile="certificate.crt", ssl_keyfile="private.key")
