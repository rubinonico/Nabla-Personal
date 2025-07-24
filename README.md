
# Nabla v2.1 Trade Executor (FastAPI)

This is a lightweight Python backend service for executing trades via the Hyperliquid SDK.

##Deploy (Recommended: Railway)

1. Clone this repo or upload the files.
2. Create a Railway project: https://railway.app
3. Add the following environment variables:
   - `PRIVATE_KEY`
   - `WALLET_ADDRESS`
   - (optional) `HYPER_API_URL`
4. Set deploy command: `uvicorn main:app --host 0.0.0.0 --port 8000`
5. Set Python version to 3.11+
6. Expose port 8000
7. Test endpoint: POST `/hedge` with JSON payload

## Example Request

```
POST /hedge
Content-Type: application/json

{
  "symbol": "ETH",
  "liquidity": 21000,
  "currentPrice": 2730,
  "lowerBound": 2710,
  "upperBound": 2750,
  "desiredLeverage": 5,
  "isIsolatedMargin": true
}
```

## 🔐 Never expose your private key in n8n. Use Railway's secrets manager.

