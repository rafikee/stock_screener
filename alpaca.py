import alpaca_trade_api as tradeapi

# Must have environment variables set

# APCA_API_SECRET_KEY
# APCA_API_KEY_ID

api = tradeapi.rest.REST()

# Get account information
account = api.get_account()

# Get positions
positions = api.list_positions()

############################


import urllib3
import os
import json

http = urllib3.PoolManager()

APCA_API_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
APCA_API_KEY_ID = os.getenv("APCA_API_KEY_ID")

headers = {
    'APCA-API-SECRET-KEY': APCA_API_SECRET_KEY,
    'APCA-API-KEY-ID': APCA_API_KEY_ID,
    'Accept': 'application/json'
    }

# Get account information
url = "https://api.alpaca.markets/v2/account"
response= http.request("GET", url, headers=headers)
data = json.loads(response.data)
buying_power = float(data['buying_power'])
portfolio_value = float(data['portfolio_value'])
market_value = float(data['long_market_value'])
# format cash, buying_power, portfolio_value, market_value in $ format with 2 decimal places and commas
buying_power = "${:,.2f}".format(buying_power)
portfolio_value = "${:,.2f}".format(portfolio_value)
market_value = "${:,.2f}".format(market_value)

# Get positions
url = "https://api.alpaca.markets/v2/positions"
response= http.request("GET", url, headers=headers)
data = json.loads(response.data)

positions = []
for position in data:
    symbol = position['symbol']
    qty = int(position['qty'])
    entry_price = float(position['avg_entry_price'])
    current_price = float(position['current_price'])
    cost_basis = float(position['cost_basis'])
    market_value = float(position['market_value'])
    profit_loss = float(position['unrealized_pl'])
    profit_loss_pct = float(position['unrealized_plpc'])
    intraday_pl = float(position['unrealized_intraday_pl'])
    intraday_pl_pct = float(position['unrealized_intraday_plpc'])
    
    # format cost_basis, market_value, profit_loss, intraday_pl in $ format with 2 decimal places and commas
    cost_basis = "${:,.2f}".format(cost_basis)
    market_value = "${:,.2f}".format(market_value)
    profit_loss = "${:,.2f}".format(profit_loss)
    intraday_pl = "${:,.2f}".format(intraday_pl)
    current_price = "${:,.2f}".format(current_price)
    entry_price = "${:,.2f}".format(entry_price)
    
    # format profit_loss_pct, intraday_pl_pct in % format with 2 decimal places
    profit_loss_pct = "{:.2f}%".format(profit_loss_pct*100)
    intraday_pl_pct = "{:.2f}%".format(intraday_pl_pct*100)

    # append position to positions list
    positions.append({
        "symbol": symbol,
        "qty": qty,
        "entry_price": entry_price,
        "current_price": current_price,
        "cost_basis": cost_basis,
        "market_value": market_value,
        "profit_loss": profit_loss,
        "profit_loss_pct": profit_loss_pct,
        "intraday_pl": intraday_pl,
        "intraday_pl_pct": intraday_pl_pct
    })