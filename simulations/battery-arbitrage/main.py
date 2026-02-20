import numpy as np

def run_battery_sim(capacity_mwh: float, power_mw: float, rte: float, seed: int) -> str:
    """
    Bare-bones arbitrage sim:
    - 24 hourly prices (synthetic)
    - charge below 30th percentile, discharge above 70th percentile
    - enforce capacity + power limits
    - simple efficiency: when discharging, delivered energy = discharged_energy * rte
    """
    rng = np.random.default_rng(int(seed))

    # Synthetic day-ahead-ish price shape: baseline + evening peak + random noise
    hours = np.arange(24)
    # Daily wave baseline shape
    base = 45 + 10*np.sin((hours - 7) * np.pi / 12)
    # Add evening peak function
    peak_height = 20
    peak_center = 18
    peak_sigma = 3  # hours
    evening_peak = peak_height * np.exp(
        -((hours - peak_center)**2) / (2 * peak_sigma**2)
    )
    # Add noise, maybe later add acute event impact
    noise = rng.normal(0, 6, size=24)

    # Price section
    p_floor = -20
    p_ceiling = None
    # Forecast prices
    forecast_prices = base + evening_peak
    realized_prices = np.clip(forecast_prices + noise, a_min=p_floor, a_max=p_ceiling)

    # Realized prices
    realized_prices = np.clip(forecast_prices + noise, a_min=p_floor, a_max=p_ceiling)

    # charge and discharge thresholds
    charge_thr = np.percentile(forecast_prices, 30)
    discharge_thr = np.percentile(forecast_prices, 70)

    # init state of charge in MWh
    soc = 0.0  # state of charge in MWh
    profit = 0.0

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

    # Format output as plain text (easy MVP)
    out = []
    out.append(f"Inputs: capacity={capacity_mwh:.1f} MWh, power={power_mw:.1f} MW, RTE={rte:.2f}, seed={seed}")
    out.append(f"Thresholds: charge<= {charge_thr:.2f}, discharge>= {discharge_thr:.2f}")
    out.append(f"Total profit (toy): ${profit:,.2f}")
    out.append("")
    out.append("hr | price | action     | SOC(MWh) | chg(MWh) | dis(MWh)")
    out.append("---|-------|------------|----------|----------|---------")
    for h, p, action, soc, chg, dis in rows:
        out.append(f"{h:>2} | {p:>5.1f} | {action:<10} | {soc:>8.1f} | {chg:>8.1f} | {dis:>7.1f}")

    return "\n".join(out)