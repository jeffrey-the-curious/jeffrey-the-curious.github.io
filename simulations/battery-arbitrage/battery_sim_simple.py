# imports: numpy for calcs, json for chart
import numpy as np
import json

# main function, inputs from GUI, returns table
def run_battery_sim(charge_thr_pct: float, discharge_thr_pct: float, power_mw: float, rte: float, seed: int) -> str:
    """
    Bare-bones arbitrage sim:
    - 24 hourly prices (synthetic)
    - user sets the charge and discharge percentile (strategy)
    - enforce power limits
    - simple efficiency: when discharging, delivered energy = discharged_energy * rte
    """
    rng = np.random.default_rng(int(seed))

    # Storage facility capacity in MWh
    capacity_mwh = 100

    # Synthetic day-ahead-ish price shape: baseline + evening peak + random noise
    hours = np.arange(24)
    # Daily wave baseline shape
    base = 45 + 10*np.sin((hours - 9) * np.pi / 12)
    # Add evening peak function
    peak_height = 20
    peak_center = 20
    peak_sigma = 2.5  # hours
    evening_peak = peak_height * np.exp(
        -((hours - peak_center)**2) / (2 * peak_sigma**2)
    )
    # Add noise, maybe later add acute event impact
    noise = rng.normal(0, 6, size=24)

    # Price section and limits
    p_floor = -20
    p_ceiling = None
    # Forecast prices
    forecast_prices = base + evening_peak

    # Realized prices
    realized_prices = np.clip(forecast_prices + noise, a_min=p_floor, a_max=p_ceiling)

    # charge and discharge thresholds
    charge_thr = np.percentile(forecast_prices, charge_thr_pct)
    discharge_thr = np.percentile(forecast_prices, discharge_thr_pct)

    # init state of charge in MWh
    soc = 0.0  # state of charge in MWh
    profit = 0.0

    # Simulation by hour
    rows = []
    for h, p in enumerate(realized_prices):
        action = "idle"
        charge_mwh = 0.0
        discharge_mwh = 0.0

        # Charge decision
        if p <= charge_thr and soc < capacity_mwh:
            # can charge up to power limit and remaining capacity
            charge_mwh = min(power_mw, capacity_mwh - soc)
            soc += charge_mwh
            profit -= charge_mwh * p  # pay price to buy energy
            action = "charge"

        # Discharge decision
        elif p >= discharge_thr and soc > 0:
            discharge_mwh = min(power_mw, soc)
            soc -= discharge_mwh
            delivered_mwh = discharge_mwh * rte
            profit += delivered_mwh * p
            action = "discharge"

        rows.append((h, float(p), action, soc, charge_mwh, discharge_mwh))

    # Format output
    payload = {
        "hours": hours.tolist(),
        "forecast_prices": forecast_prices.tolist(),
        "realized_prices": realized_prices.tolist(),
        "charge_thr": float(charge_thr),
        "discharge_thr": float(discharge_thr),
        "profit": float(profit),
        "rows": [
            {
                "h": int(h),
                "price": float(p),
                "action": str(action),
                "soc": float(soc),
                "chg": float(chg),
                "dis": float(dis),
            }
            for (h, p, action, soc, chg, dis) in rows
        ],
    }
    return json.dumps(payload)