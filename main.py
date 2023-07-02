import ssl
from fastapi import FastAPI, Request
from binance.client import *
from binance.enums import *
import MetaTrader5 as mt5

app = FastAPI()


class Broker:
    """
    Blueprint for brokers
    """
    def __init__(self, symbol, quantity):
        self.symbol = symbol
        self.quantity = quantity

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
    def __init__(self, symbol, quantity):
        super().__init__(symbol, quantity)

    def open_long(self):
        self.close_position()
        mt5.Buy(self.symbol, self.quantity)
        print("Long position have just been opened: ", self.symbol)

    def open_short(self):
        self.close_position()
        mt5.Sell(self.symbol, self.quantity)
        print("Short position have just been opened: ", self.symbol)

    def close_position(self):
        mt5.Close(self.symbol)
        print("Positions closed successfully")


class BinanceBroker(Broker):
    """
    Binance broker handler

    Args:
        Broker (class): blueprint
    """
    def __init__(self, symbol, quantity):
        super().__init__(symbol, quantity)
        self.client = Client('api_key', 'api_secret')  # Initialize binance client

    def create_order(self, side):
        order = self.client.futures_create_order(
            symbol=self.symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=self.quantity,
        )
        return order

    def open_long(self):
        self.close_position()
        self.create_order(SIDE_BUY)
        print("Long have been just opened on: ", self.symbol)

    def open_short(self):
        self.close_position()
        self.create_order(SIDE_SELL)
        print("Short have been just opened on: ", self.symbol)

    def close_position(self):
        positions = self.client.futures_position_information()
        for position in positions:
            if position['symbol'] == self.symbol:
                quantity = float(position['positionAmt'])
                if quantity > 0:
                    self.create_order(SIDE_SELL)
                    print("Closed long on: ", self.symbol)
                if quantity < 0:
                    quantity = -quantity
                    self.create_order(SIDE_BUY)
                    print("Closed short on: ", self.symbol)
                if quantity == 0:
                    print("No positions on: ", self.symbol)


class BrokerFactory:
    """
    Factory for getting the broker

    Returns:
        object: broker
    """
    @staticmethod
    def get_broker(broker_type, symbol, quantity):
        brokers = {
            "M": MT5Broker,
            "B": BinanceBroker
        }
        return brokers[broker_type](symbol, quantity)


@app.post("/webhook529376sdgf")
async def process_webhook(request: Request):
    payload_bytes = await request.body()
    payload_str = payload_bytes.decode()
    payload_list = payload_str.splitlines()

    symbol = str(payload_list[0])
    direction = payload_list[1]
    lot = float(payload_list[2])
    broker_type = payload_list[3]

    broker = BrokerFactory.get_broker(broker_type, symbol, lot)

    if direction == 'buy':
        broker.open_long()
    elif direction == 'sell':
        broker.open_short()


if __name__ == "__main__":
    # pass your mt5 creditentials below
    if mt5.initialize() and mt5.login(1234567, 'password', server='VantageInternational-Live'):
        # print account info
        account_info = mt5.account_info()
        print("Account Info: ", account_info)
    else:
        print("MT5 Login failed")

    import uvicorn

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile="certificate.crt", keyfile="private.key")
    uvicorn.run(app, host="IP", port=443, ssl_certfile="certificate.crt", ssl_keyfile="private.key")
