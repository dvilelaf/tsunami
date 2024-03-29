import json
from collections import Counter
from datetime import datetime, timedelta

import requests

from packages.dvilela.skills.tsunami_abci.subgraph import (
    OMEN_XDAI_FPMMS_QUERY,
    OMEN_XDAI_TRADES_QUERY,
)


OMEN_API_ENDPOINT = "https://api.thegraph.com/subgraphs/name/protofire/omen-xdai"

now = datetime.now() - timedelta(hours=1)
creation_timestamp_gt = str(int((now - timedelta(days=1)).timestamp()))

headers = {
    "Accept": "application/json, multipart/mixed",
    "Content-Type": "application/json",
}

query = OMEN_XDAI_FPMMS_QUERY.substitute(
    creationTimestamp_gt=creation_timestamp_gt,
)

content_json = {
    "query": query,
    "variables": None,
    "extensions": {"headers": None},
}

response = requests.post(
    url=OMEN_API_ENDPOINT,
    json=content_json,
    headers=headers,
    timeout=60,
)
markets = response.json().get("data", {}).get("fixedProductMarketMakers", [])

with open("omen_markets.json", "w", encoding="utf-8") as file:
    json.dump(markets, file, indent=4)

query = OMEN_XDAI_TRADES_QUERY.substitute(
    creationTimestamp_gt=creation_timestamp_gt,
)

content_json = {
    "query": query,
    "variables": None,
    "extensions": {"headers": None},
}

response = requests.post(
    url=OMEN_API_ENDPOINT,
    json=content_json,
    headers=headers,
    timeout=60,
)
trades = response.json().get("data", {}).get("fpmmTrades", [])

with open("omen_trades.json", "w", encoding="utf-8") as file:
    json.dump(trades, file, indent=4)


# Calculate data
n_markets = len(markets)
n_trades = len(trades)
usd_amount = sum([float(t["collateralAmountUSD"]) for t in trades])
traders = [t["creator"]["id"] for t in trades]
trader_counter = Counter(traders)
n_traders = len(trader_counter)
biggest_trader_address, biggest_trader_trades = trader_counter.most_common(1)[0]


print(f"n_markets={n_markets}")
print(f"n_trades={n_trades}")
print(f"usd_amount={usd_amount}")
print(f"n_traders={n_traders}")
print(f"biggest_trader_address={biggest_trader_address}")
print(f"biggest_trader_trades={biggest_trader_trades}")
