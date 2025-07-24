
from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
import math
import uvicorn
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

app = FastAPI()

class HedgeRequest(BaseModel):
    symbol: str
    liquidity: float
    currentPrice: float
    lowerBound: float
    upperBound: float
    desiredLeverage: float
    isIsolatedMargin: bool = True

@app.post("/hedge")
async def hedge(req: HedgeRequest):
    try:
        address = os.environ["WALLET_ADDRESS"]
        private_key = os.environ["PRIVATE_KEY"]
        base_url = os.getenv("HYPER_API_URL", constants.MAINNET_API_URL)

        info = Info(base_url, skip_ws=True)
        exchange = Exchange(private_key=private_key, base_url=base_url)

        L = req.liquidity
        P = req.currentPrice
        Pa = req.lowerBound
        Pb = req.upperBound
        symbol = req.symbol
        is_isolated = not req.isIsolatedMargin
        desired_leverage = req.desiredLeverage

        log = {}

        user_state = info.user_state(address)
        current_hedge_position = 0.0
        for pos in user_state.get("assetPositions", []):
            if pos["position"]["coin"] == symbol:
                current_hedge_position = float(pos["position"]["szi"])
                break

        is_in_range = Pa < P < Pb
        target_hedge_size = 0.0
        delta_lp = 0.0
        gamma_lp = 0.0
        amount_token0_in_lp = 0.0

        if P <= Pa:
            sqrt_pa = math.sqrt(Pa)
            sqrt_pb = math.sqrt(Pb)
            amount_token0_in_lp = L * ((sqrt_pb - sqrt_pa) / (sqrt_pa * sqrt_pb))
            target_hedge_size = -amount_token0_in_lp
            log["position_state"] = "Below Range"
        elif P >= Pb:
            target_hedge_size = 0.0
            log["position_state"] = "Above Range"
        else:
            delta_lp = L * (math.sqrt(P / Pa) - math.sqrt(Pb / P))
            target_hedge_size = -delta_lp
            log["position_state"] = "In Range"

        hedge_adjustment = target_hedge_size - current_hedge_position
        is_hedge_required = False

        if is_in_range:
            gamma_lp = -L / (2 * math.pow(P, 1.5))
            base_deadband_delta = 0.005
            sensitivity_factor = 500.0
            dynamic_deadband = base_deadband_delta / (1 + abs(gamma_lp) * sensitivity_factor)
            if abs(hedge_adjustment) > dynamic_deadband:
                is_hedge_required = True
        else:
            if abs(hedge_adjustment) > 0.001:
                is_hedge_required = True

        log.update({
            "delta_lp": delta_lp if is_in_range else amount_token0_in_lp,
            "gamma_lp": gamma_lp,
            "target_hedge_size": target_hedge_size,
            "hedge_adjustment": hedge_adjustment,
        })

        if is_hedge_required:
            side = "B" if hedge_adjustment > 0 else "A"
            order_size = abs(hedge_adjustment)

            meta = info.meta()
            asset_meta = next((a for a in meta["universe"] if a["name"] == symbol), None)

            if not asset_meta:
                raise Exception("Symbol not found in meta")

            max_leverage = asset_meta["maxLeverage"]
            oracle_price = float(asset_meta["oraclePx"])
            actual_leverage = min(desired_leverage, max_leverage)
            notional = order_size * oracle_price
            margin_required = notional / actual_leverage

            margin_summary = user_state["marginSummary"]
            available_capital = float(margin_summary["accountValue"]) - float(margin_summary["totalMarginUsed"])

            if margin_required > available_capital:
                log["action_taken"] = "Insufficient Capital"
                log["error_message"] = f"Required ${margin_required:.2f}, Available ${available_capital:.2f}"
            else:
                exchange.update_leverage(actual_leverage, symbol, is_isolated)
                result = exchange.order(symbol, side, order_size, None, {"limit": {"tif": "Ioc"}}, reduce_only=False)
                log["action_taken"] = "Hedge Executed"
                log["trade_result"] = result
        else:
            log["action_taken"] = "No Hedge Needed"

        return {"success": True, "log": log}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
