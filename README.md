# Cloud Arbitrage Monitoring Service

An asynchronous FastAPI service that compares cryptocurrency prices across
Wallex and Nobitex, records price samples and arbitrage opportunities, exposes
Prometheus metrics, and optionally sends Telegram or Bale notifications.

## Highlights

- Concurrent price polling for multiple trading pairs
- Configurable spread threshold and polling interval
- Async PostgreSQL persistence with SQLAlchemy
- Prometheus metrics and Grafana-ready monitoring
- Docker Compose setup for the API, PostgreSQL, Prometheus, and Grafana
- Environment-based API keys and notification credentials

## Run

1. Copy .env.example to .env and adjust the values.
2. Run: docker compose up --build
3. Open /healthz and /metrics on port 8000, Prometheus on 9090, and Grafana on 3000.

Public market endpoints work without exchange API keys. Notification credentials
are optional.

## Author

Mehrdad Sheikh Abbasi
