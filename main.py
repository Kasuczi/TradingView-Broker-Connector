import ssl
import logging
from fastapi import FastAPI, Request
from binance.client import *
from binance.enums import *
import MetaTrader5 as mt5

app = FastAPI()
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s:%(message)s')


class Broker:
    """
    Blueprint for brokers
    """
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
    """
    MT5 broker handler

    Args:
        Broker (class): blueprint
    """
    def __init__(self, symbol):
        super().__init__(symbol)

    def open_long(self):
        quantity = self.calculate_position_size()
        self.close_position()
        mt5.Buy(self.symbol, quantity)
        logging.info(f"Long position have just been opened: {self.symbol}")

    def open_short(self):
        quantity = self.calculate_position_size()
        self.close_position()
        mt5.Sell(self.symbol, quantity)
        logging.info(f"Short position have just been opened: {self.symbol}")

    def close_position(self):
        mt5.Close(self.symbol)
        logging.info(f"Positions closed successfully for symbol: {self.symbol}")

    def calculate_position_size(self):
        account_info = mt5.account_info()
        equity = account_info.equity
        position_size = 0.01 * (equity / 100)
        return position_size


class BinanceBroker(Broker):
    """
    Binance broker handler

    Args:
        Broker (class): blueprint
    """
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
        logging.info(f"Long have been just opened on: {self.symbol}")

    def open_short(self):
        self.close_position()
        quantity = self.calculate_position_size()
        self.create_order(SIDE_SELL, quantity)
        logging.info(f"Short have been just opened on: {self.symbol}")

    def close_position(self):
        positions = self.client.futures_position_information()
        for position in positions:
            if position['symbol'] == self.symbol:
                quantity = float(position['positionAmt'])
                if quantity > 0:
                    self.create_order(SIDE_SELL, quantity)
                    logging.info(f"Closed long on: {self.symbol}")
                elif quantity < 0:
                    quantity = abs(quantity)
                    self.create_order(SIDE_BUY, quantity)
                    logging.info(f"Closed short on: {self.symbol}")
                elif quantity == 0:
                    logging.info(f"No positions on: {self.symbol}")

    def calculate_position_size(self):
        futures_account = self.client.futures_account()
        account_balance = futures_account['totalWalletBalance']
        position_size = 0.10 * float(account_balance)  # 10% of account size
        return position_size


class BrokerFactory:
    """
    Factory for getting the broker

    Returns:
        object: broker
    """
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
    broker_type = payload_list[3]

    broker = BrokerFactory.get_broker(broker_type, symbol)

    if direction == 'buy':
        broker.open_long()
    elif direction == 'sell':
        broker.open_short()

    logging.info(f"Received webhook with payload: {payload_list}")


if __name__ == "__main__":
    # pass your mt5 creditentials below
    if mt5.initialize() and mt5.login(1234567, 'password', server='VantageInternational-Live'):
        # print account info
        account_info = mt5.account_info()
        logging.info(f"Account Info: {account_info}")
    else:
        logging.info("MT5 Login failed")

    import uvicorn

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile="certificate.crt", keyfile="private.key")
    uvicorn.run(app, host="195.238.122.243", port=443, ssl_certfile="certificate.crt", ssl_keyfile="private.key")
