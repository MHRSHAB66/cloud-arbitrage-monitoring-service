from prometheus_client import Counter, Summary, Gauge


# API call latency per exchange
api_latency = Summary(
"api_latency_seconds",
"API latency per exchange",
["exchange", "pair"],
)


# Requests outcome per exchange
api_requests_total = Counter(
"api_requests_total",
"API requests (labeled by outcome)",
["exchange", "pair", "status"], # status: ok|error
)


# Latest observed spread per pair (best route only)
spread_latest = Gauge(
"spread_latest_pct",
"Latest observed arbitrage spread (percent)",
["pair"],
)


# Arbitrage discoveries counter per pair
arbitrage_found_total = Counter(
"arbitrage_found_total",
"Number of arbitrage discoveries",
["pair"],
)


# Last price per exchange/pair
price_last = Gauge(
"price_last",
"Last fetched price",
["exchange", "pair"],
)