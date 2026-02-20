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

    # Synthetic day-ahead-ish price shape: baseline + random noise + mild evening peak
    hours = np.arange(24)
    base = 45 + 10*np.sin((hours - 7) * np.pi / 12)  # daily wave
    evening_peak = 20*np.exp(-0.5*((hours - 18)/3)**2)
    noise = rng.normal(0, 6, size=24)
    prices = np.clip(base + evening_peak + noise, a_min=-20, a_max=None)

    low_thr = np.percentile(prices, 30)
    high_thr = np.percentile(prices, 70)

    soc = 0.0  # state of charge in MWh
    profit = 0.0

    rows = []
    for h, p in enumerate(prices):
        action = "idle"
        charge_mwh = 0.0
        discharge_mwh = 0.0

        # Charge decision
        if p <= low_thr and soc < capacity_mwh:
            # can charge up to power limit and remaining capacity
            charge_mwh = min(power_mw, capacity_mwh - soc)
            soc += charge_mwh
            profit -= charge_mwh * p  # pay price to buy energy
            action = "charge"

        # Discharge decision
        elif p >= high_thr and soc > 0:
            discharge_mwh = min(power_mw, soc)
            soc -= discharge_mwh
            delivered_mwh = discharge_mwh * rte
            profit += delivered_mwh * p
            action = "discharge"

        rows.append((h, float(p), action, soc, charge_mwh, discharge_mwh))

    # Format output as plain text (easy MVP)
    out = []
    out.append(f"Inputs: capacity={capacity_mwh:.1f} MWh, power={power_mw:.1f} MW, RTE={rte:.2f}, seed={seed}")
    out.append(f"Thresholds: charge<= {low_thr:.2f}, discharge>= {high_thr:.2f}")
    out.append(f"Total profit (toy): ${profit:,.2f}")
    out.append("")
    out.append("hr | price | action     | SOC(MWh) | chg(MWh) | dis(MWh)")
    out.append("---|-------|------------|----------|----------|---------")
    for h, p, action, soc, chg, dis in rows:
        out.append(f"{h:>2} | {p:>5.1f} | {action:<10} | {soc:>8.1f} | {chg:>8.1f} | {dis:>7.1f}")

    return "\n".join(out)