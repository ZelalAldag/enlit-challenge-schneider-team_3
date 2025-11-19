#!/usr/bin/env python
# coding: utf-8

# In[87]:


# app.py  – single-file ENLIT app (model + UI)

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, Dict
import requests
from prophet import Prophet  # pip install prophet

# =========================================================
# 0. LOAD INTERVAL DATA (YOUR ENLIT EXCEL)
# =========================================================

LOAD_FILE = "/Users/mainakde/Downloads/Enlit/LoadProfile_Final_ENLIT.xlsx"

def load_interval_data(
    path=LOAD_FILE,
    ts_col: str = "Date/Time",
    load_col: str = "L1 Site",
    freq_hint: str = "15min",
) -> pd.DataFrame:
    """
    Reads the industrial site's interval data and returns a clean dataframe:
      index: timestamp
      column: 'load_kw'
    """
    df = pd.read_excel(path)

    # Map case-insensitive column names
    cols_lower = {c.lower(): c for c in df.columns}
    if ts_col.lower() not in cols_lower:
        raise ValueError(
            f"Timestamp column '{ts_col}' not found. Available: {df.columns.tolist()}"
        )
    if load_col.lower() not in cols_lower:
        raise ValueError(
            f"Load column '{load_col}' not found. Available: {df.columns.tolist()}"
        )

    tcol = cols_lower[ts_col.lower()]   # e.g. "Date/Time"
    lcol = cols_lower[load_col.lower()] # e.g. "L1 Site"

    # Keep only time + load to avoid resampling non-numerics
    df = df[[tcol, lcol]].copy()

    # Parse timestamps – format matches "2024-01-01 00:15:00"
    df[tcol] = pd.to_datetime(
        df[tcol],
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce",
    )
    df = df.dropna(subset=[tcol])
    df = df.sort_values(tcol)
    df = df.set_index(tcol)

    # Normalize frequency – resample only numeric column
    if freq_hint:
        df = df.resample(freq_hint)[[lcol]].mean()

    # Standard name for downstream functions
    df = df.rename(columns={lcol: "load_kw"})
    return df

# =========================================================
# 1. TARIFF CONFIG
# =========================================================

@dataclass
class TariffConfig:
    name: str
    # Energy prices (€/MWh)
    price_peak: float
    price_offpeak: float

    # Demand charge (€/kW per month)
    demand_price_eur_per_kw_month: float

    # Regulated / ATR components (€/MWh)
    atr_eur_per_mwh: float = 0.0

    # Taxes as fraction of subtotal, e.g. 0.05 = 5%
    tax_rate: float = 0.0

    # Peak / off-peak hours (local time)
    peak_start_hour: int = 8   # 08:00
    peak_end_hour: int = 22    # 22:00

SPANISH_SAMPLE_TARIFF = TariffConfig(
    name="ES_Industrial_Placeholder",
    price_peak=100.0,          # €/MWh
    price_offpeak=60.0,        # €/MWh
    demand_price_eur_per_kw_month=8.0,
    atr_eur_per_mwh=10.0,
    tax_rate=0.05,
    peak_start_hour=8,
    peak_end_hour=22,
)

def is_peak_hour(ts, tariff: TariffConfig) -> bool:
    """Return True if timestamp is in peak hours under the given tariff."""
    h = ts.hour
    return (h >= tariff.peak_start_hour) and (h < tariff.peak_end_hour)

# =========================================================
# 2. COST ENGINE (ENERGY + DEMAND)
# =========================================================

def add_energy_price_column(
    df: pd.DataFrame,
    tariff: TariffConfig = SPANISH_SAMPLE_TARIFF,
    spot_price_eur_mwh: pd.Series | None = None,
) -> pd.DataFrame:
    """
    Add:
      - is_peak (bool)
      - energy_price_eur_mwh  (€/MWh)

    If spot_price_eur_mwh is provided (Series indexed like df.index),
    it is used as the energy price. Otherwise we fall back to
    peak/off-peak prices from the tariff.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("add_energy_price_column expects a DatetimeIndex.")

    df = df.copy()

    # Always compute is_peak for info / scenarios
    df["is_peak"] = df.index.map(lambda ts: is_peak_hour(ts, tariff))

    if spot_price_eur_mwh is not None:
        # Align spot prices to df index (forward-fill)
        spot_aligned = (
            spot_price_eur_mwh
            .sort_index()
            .reindex(df.index, method="ffill")
        )
        df["energy_price_eur_mwh"] = spot_aligned.values
    else:
        # Classic TOU tariff
        df["energy_price_eur_mwh"] = np.where(
            df["is_peak"], tariff.price_peak, tariff.price_offpeak
        )

    return df

def compute_interval_costs(
    df: pd.DataFrame,
    tariff: TariffConfig = SPANISH_SAMPLE_TARIFF,
    spot_price_eur_mwh: pd.Series | None = None,
) -> pd.DataFrame:
    """
    From 'load_kw' and time index, build interval energy, energy cost, ATR, and taxes.
    Optionally uses a spot price time series instead of static peak/off-peak prices.
    """
    if "load_kw" not in df.columns:
        raise KeyError("compute_interval_costs expects 'load_kw' column.")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("compute_interval_costs expects DatetimeIndex.")

    df = df.copy()
    df = add_energy_price_column(df, tariff, spot_price_eur_mwh=spot_price_eur_mwh)

    # Interval duration in hours
    dt_minutes = df.index.to_series().diff().dt.total_seconds() / 60.0
    if dt_minutes.isna().all():
        raise ValueError("Could not infer interval length from index.")
    dt_minutes.iloc[0] = dt_minutes.median()
    hours = dt_minutes / 60.0

    # Interval energy in kWh and MWh
    df["energy_kwh_interval"] = df["load_kw"] * hours
    df["energy_mwh_interval"] = df["energy_kwh_interval"] / 1000.0

    # Energy cost (spot or TOU price)
    df["energy_cost_eur_interval"] = (
        df["energy_kwh_interval"] * df["energy_price_eur_mwh"] / 1000.0
    )

    # ATR cost
    df["atr_cost_eur_interval"] = (
        df["energy_kwh_interval"] * tariff.atr_eur_per_mwh / 1000.0
    )

    # Subtotal and taxes
    df["subtotal_eur_interval"] = (
        df["energy_cost_eur_interval"] + df["atr_cost_eur_interval"]
    )
    df["tax_eur_interval"] = df["subtotal_eur_interval"] * tariff.tax_rate

    # Energy-related total (before demand charges)
    df["total_energy_related_eur_interval"] = (
        df["subtotal_eur_interval"] + df["tax_eur_interval"]
    )

    # Demand-related columns (initialized; real values added later)
    df["monthly_peak_kw"] = 0.0
    df["demand_charge_eur_month"] = 0.0
    df["demand_charge_eur_interval"] = 0.0

    # Initial total cost (will be updated after demand charge calculation)
    df["total_cost_eur_interval"] = (
        df["total_energy_related_eur_interval"] + df["demand_charge_eur_interval"]
    )

    return df

def compute_monthly_demand_charge(
    df: pd.DataFrame,
    tariff: TariffConfig = SPANISH_SAMPLE_TARIFF
) -> pd.DataFrame:
    """
    Add monthly demand charges to an interval dataframe.

    Expects:
      - index: DatetimeIndex
      - 'load_kw' column
      - 'total_energy_related_eur_interval' from compute_interval_costs()
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("compute_monthly_demand_charge expects a DatetimeIndex.")
    if "load_kw" not in df.columns:
        raise KeyError("compute_monthly_demand_charge expects 'load_kw' column.")
    if "total_energy_related_eur_interval" not in df.columns:
        raise KeyError(
            "compute_monthly_demand_charge expects 'total_energy_related_eur_interval'. "
            "Run compute_interval_costs() first."
        )

    # 1️⃣ Build month period
    df["month"] = pd.PeriodIndex(df.index, freq="M")

    # 2️⃣ Monthly peak demand and demand charge per month
    monthly = (
        df.groupby("month")["load_kw"]
          .max()
          .to_frame(name="monthly_peak_kw")
    )

    if monthly.empty:
        df["demand_charge_eur_interval"] = 0.0
        df["total_cost_eur_interval"] = df["total_energy_related_eur_interval"]
        df.drop(columns=["month"], inplace=True)
        return df

    monthly["demand_charge_eur_month"] = (
        monthly["monthly_peak_kw"] * tariff.demand_price_eur_per_kw_month
    )

    # Drop old columns to avoid overlap on join
    df = df.drop(columns=["monthly_peak_kw", "demand_charge_eur_month"], errors="ignore")

    # 3️⃣ Join monthly data back on 'month'
    df = df.join(monthly, on="month")

    # 4️⃣ Spread demand charge equally over all intervals in each month
    intervals_per_month = df.groupby("month")["load_kw"].transform("size")
    df["demand_charge_eur_interval"] = (
        df["demand_charge_eur_month"] / intervals_per_month
    )

    # 5️⃣ Final total cost
    df["total_cost_eur_interval"] = (
        df["total_energy_related_eur_interval"] + df["demand_charge_eur_interval"]
    )

    df.drop(columns=["month"], inplace=True)
    return df

# =========================================================
# 3. BASELINE ANNUAL COST
# =========================================================

def compute_baseline_annual_cost(df: pd.DataFrame) -> float:
    """
    Compute total cost for the last 12 full months in the dataset.
    Avoids partial-year issues (e.g., only 1 day in 2025).
    """
    if "total_cost_eur_interval" not in df.columns:
        raise KeyError("Expected 'total_cost_eur_interval' in df.")

    end = df.index.max()
    start = end - pd.Timedelta(days=365)

    one_year_df = df.loc[start:end]
    return one_year_df["total_cost_eur_interval"].sum()

# =========================================================
# 4. OPTIMIZATION ACTIONS
# =========================================================

@dataclass
class ActionScenario:
    name: str
    description: str
    capex_eur: float   # investment
    savings_eur_per_year: float
    roi_simple_payback_years: float

def scenario_reduce_overall(
    df: pd.DataFrame,
    tariff: TariffConfig,
    reduction_pct: float,
    capex_eur: float,
) -> ActionScenario:
    """
    Reduce all loads by reduction_pct (0.05 = 5%).
    df is assumed to already have cost columns for the baseline.
    """
    s = 1.0 - reduction_pct
    df_red = df.copy()
    df_red["load_kw"] *= s
    df_red = compute_interval_costs(df_red, tariff)
    df_red = compute_monthly_demand_charge(df_red, tariff)

    baseline = compute_baseline_annual_cost(df)
    annual_cost = compute_baseline_annual_cost(df_red)
    savings = baseline - annual_cost
    payback = capex_eur / savings if savings > 0 else np.inf

    return ActionScenario(
        name=f"Reduce overall consumption by {reduction_pct*100:.0f}%",
        description="Efficiency measures, behavior change, better controls.",
        capex_eur=capex_eur,
        savings_eur_per_year=savings,
        roi_simple_payback_years=payback,
    )

def scenario_reduce_peak(
    df: pd.DataFrame,
    tariff: TariffConfig,
    peak_reduction_kw: float,
    capex_eur: float,
) -> ActionScenario:
    """
    Approximate peak-shaving: reduce monthly peaks by a fixed kW.
    """
    df_red = df.copy()

    # Monthly peak threshold based on original profile (month-end 'ME')
    monthly_peak = df_red["load_kw"].resample("ME").transform("max")
    threshold = monthly_peak - peak_reduction_kw

    df_red["load_kw"] = np.where(
        df_red["load_kw"] > threshold, threshold, df_red["load_kw"]
    )

    df_red = compute_interval_costs(df_red, tariff)
    df_red = compute_monthly_demand_charge(df_red, tariff)

    baseline = compute_baseline_annual_cost(df)
    annual_cost = compute_baseline_annual_cost(df_red)
    savings = baseline - annual_cost
    payback = capex_eur / savings if savings > 0 else np.inf

    return ActionScenario(
        name=f"Reduce monthly peak by {peak_reduction_kw:.0f} kW",
        description="Demand management / peak-shaving battery / process scheduling.",
        capex_eur=capex_eur,
        savings_eur_per_year=savings,
        roi_simple_payback_years=payback,
    )

def scenario_shift_peak_energy(
    df: pd.DataFrame,
    tariff: TariffConfig,
    shift_fraction: float,
    capex_eur: float,
) -> ActionScenario:
    """
    Shift a fraction of peak-period kWh into off-peak (same total energy).
    Reduce peak kWh by fraction and add them to off-peak hours proportionally.
    """
    df_red = df.copy()
    df_red = add_energy_price_column(df_red, tariff)

    # Ensure energy_kwh_interval exists
    if "energy_kwh_interval" not in df_red.columns:
        dt_minutes = df_red.index.to_series().diff().dt.total_seconds() / 60.0
        dt_minutes.iloc[0] = dt_minutes.median()
        hours = dt_minutes / 60.0
        df_red["energy_kwh_interval"] = df_red["load_kw"] * hours

    energy_peak = df_red.loc[df_red["is_peak"], "energy_kwh_interval"]
    energy_off = df_red.loc[~df_red["is_peak"], "energy_kwh_interval"]

    shift_kwh = energy_peak.sum() * shift_fraction

    if shift_kwh <= 0 or energy_peak.sum() == 0 or energy_off.sum() == 0:
        savings = 0.0
        payback = np.inf
    else:
        # Reduce peak energy
        df_red.loc[df_red["is_peak"], "energy_kwh_interval"] *= (1 - shift_fraction)

        # Redistribute shifted kWh to off-peak proportionally
        off_weight = df_red.loc[~df_red["is_peak"], "energy_kwh_interval"]
        off_weight = off_weight / off_weight.sum()
        df_red.loc[~df_red["is_peak"], "energy_kwh_interval"] += off_weight * shift_kwh

        # Back-calculate load_kw from energy_kwh_interval
        dt_minutes = df_red.index.to_series().diff().dt.total_seconds() / 60.0
        dt_minutes.iloc[0] = dt_minutes.median()
        hours = dt_minutes / 60.0
        df_red["load_kw"] = df_red["energy_kwh_interval"] / hours

        # Re-run full cost engine
        df_red = compute_interval_costs(df_red, tariff)
        df_red = compute_monthly_demand_charge(df_red, tariff)

        baseline = compute_baseline_annual_cost(df)
        annual_cost = compute_baseline_annual_cost(df_red)
        savings = baseline - annual_cost
        payback = capex_eur / savings if savings > 0 else np.inf

    return ActionScenario(
        name=f"Shift {shift_fraction*100:.0f}% of peak energy to off-peak",
        description="Process rescheduling/storage to move load out of expensive hours.",
        capex_eur=capex_eur,
        savings_eur_per_year=savings,
        roi_simple_payback_years=payback,
    )

def scenario_peak_forecast_avoidance(
    df: pd.DataFrame,
    tariff: TariffConfig,
    flex_fraction: float,
    forecast_window_h: float,
    capex_eur: float,
) -> ActionScenario:
    """
    Forecast-based peak avoidance:
      - Look ahead forecast_window_h hours (rolling max)
      - If a high peak is predicted, reduce current flexible load fraction.
    flex_fraction in [0,1] = % of load that can be curtailed.
    """

    # Baseline
    baseline = compute_baseline_annual_cost(
        compute_monthly_demand_charge(
            compute_interval_costs(df, tariff),
            tariff,
        )
    )

    df_red = df.copy()

    # Find typical time step
    dt_hours_series = df.index.to_series().diff().dt.total_seconds() / 3600.0
    dt_hours_series.iloc[0] = dt_hours_series.median()
    dt_h = dt_hours_series.median()
    steps = max(int(round(forecast_window_h / max(dt_h, 1e-6))), 1)

    # Simple "forecast": rolling max ahead
    forecast_max = (
        df["load_kw"]
        .rolling(window=steps, min_periods=1)
        .max()
        .shift(-(steps - 1))
    )

    # Global peak as reference
    global_peak = df["load_kw"].max()
    threshold = 0.95 * global_peak  # avoid the top 5%

    # If predicted peak > threshold, curtail flexible part
    mask = forecast_max > threshold
    df_red.loc[mask, "load_kw"] *= (1.0 - flex_fraction)

    # Re-run cost engine
    df_red = compute_interval_costs(df_red, tariff)
    df_red = compute_monthly_demand_charge(df_red, tariff)
    annual_cost = compute_baseline_annual_cost(df_red)

    savings = baseline - annual_cost
    payback = capex_eur / savings if savings > 0 else np.inf

    return ActionScenario(
        name=f"Peak forecast avoidance ({flex_fraction*100:.0f}% flex)",
        description=(
            "Forecast-based control reduces flexible load ahead of predicted "
            "peaks to avoid high demand charges."
        ),
        capex_eur=capex_eur,
        savings_eur_per_year=savings,
        roi_simple_payback_years=payback,
    )

def scenario_co2_aware_shift(
    df: pd.DataFrame,
    tariff: TariffConfig,
    co2_intensity_kg_per_mwh: pd.Series,
    shift_fraction: float,
    lambda_co2: float,
    capex_eur: float,
) -> ActionScenario:
    """
    CO₂-aware shifting:
      - Combines price and CO₂ intensity into a single weight
      - Reduces a fraction of energy from high-weight intervals
      - Redistributes it to low-weight intervals.
    """

    # Baseline
    baseline_cost_df = compute_monthly_demand_charge(
        compute_interval_costs(df, tariff),
        tariff,
    )
    baseline = compute_baseline_annual_cost(baseline_cost_df)

    # Copy and add price + CO2
    df_red = df.copy()
    df_red = add_energy_price_column(df_red, tariff)

    # Align CO2 to index
    co2_aligned = (
        co2_intensity_kg_per_mwh.sort_index()
        .reindex(df_red.index, method="ffill")
    )
    df_red["co2_kg_per_mwh"] = co2_aligned

    # Interval duration
    dt_minutes = df_red.index.to_series().diff().dt.total_seconds() / 60.0
    dt_minutes.iloc[0] = dt_minutes.median()
    hours = dt_minutes / 60.0

    # Ensure energy_kwh_interval exists
    if "energy_kwh_interval" not in df_red.columns:
        df_red["energy_kwh_interval"] = df_red["load_kw"] * hours

    # Build combined weight
    price = df_red["energy_price_eur_mwh"]
    co2 = df_red["co2_kg_per_mwh"]

    def norm(x):
        return (x - x.min()) / (x.max() - x.min() + 1e-9)

    w_price = norm(price)
    w_co2 = norm(co2)
    weight = w_price + lambda_co2 * w_co2

    high_mask = weight >= weight.quantile(0.75)
    low_mask = ~high_mask

    energy = df_red["energy_kwh_interval"].copy()
    energy_high = energy[high_mask]
    energy_low = energy[low_mask]

    if energy_high.sum() == 0 or energy_low.sum() == 0:
        savings = 0.0
        payback = np.inf
    else:
        shift_kwh = energy_high.sum() * shift_fraction

        # Reduce energy in high-weight intervals
        df_red.loc[high_mask, "energy_kwh_interval"] *= (1.0 - shift_fraction)

        # Redistribute to low-weight intervals (inverse weight as preference)
        low_weight_inv = 1.0 / (weight[low_mask] + 1e-6)
        low_weight_inv /= low_weight_inv.sum()
        df_red.loc[low_mask, "energy_kwh_interval"] += low_weight_inv * shift_kwh

        # Back-calc load
        df_red["load_kw"] = df_red["energy_kwh_interval"] / hours

        # Re-run cost engine
        df_red = compute_interval_costs(df_red, tariff)
        df_red = compute_monthly_demand_charge(df_red, tariff)
        annual_cost = compute_baseline_annual_cost(df_red)

        savings = baseline - annual_cost
        payback = capex_eur / savings if savings > 0 else np.inf

    return ActionScenario(
        name=f"CO₂-aware shifting ({shift_fraction*100:.0f}%, λ={lambda_co2})",
        description=(
            "Shifts a fraction of energy away from high CO₂ + high-price "
            "intervals into low CO₂ + low-price intervals."
        ),
        capex_eur=capex_eur,
        savings_eur_per_year=savings,
        roi_simple_payback_years=payback,
    )

def scenario_rl_flex_control(
    df: pd.DataFrame,
    tariff: TariffConfig,
    learned_action_fraction: pd.Series,
    capex_eur: float,
) -> ActionScenario:
    """
    RL-inspired scenario:
      - learned_action_fraction[t] in [0,1] is fraction of flexible load
        to curtail at time t (provided by an RL agent trained offline).
    """

    # Baseline
    baseline = compute_baseline_annual_cost(
        compute_monthly_demand_charge(
            compute_interval_costs(df, tariff),
            tariff,
        )
    )

    # Align actions to index
    actions = (
        learned_action_fraction.sort_index()
        .reindex(df.index, method="ffill")
        .clip(lower=0.0, upper=1.0)
        .fillna(0.0)
    )

    df_red = df.copy()
    df_red["load_kw"] = df["load_kw"] * (1.0 - actions)

    df_red = compute_interval_costs(df_red, tariff)
    df_red = compute_monthly_demand_charge(df_red, tariff)
    annual_cost = compute_baseline_annual_cost(df_red)

    savings = baseline - annual_cost
    payback = capex_eur / savings if savings > 0 else np.inf

    return ActionScenario(
        name="RL-based flexible load control",
        description=(
            "Applies a learned (RL) control policy that curtails a fraction of "
            "flexible load each interval to minimize long-term cost."
        ),
        capex_eur=capex_eur,
        savings_eur_per_year=savings,
        roi_simple_payback_years=payback,
    )

# =========================================================
# 5. WEATHER – REAL MADRID TEMPERATURE + FUTURE CLIMATOLOGY
# =========================================================

def add_madrid_temperature(load_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 'temperature_C' using Open-Meteo for historical dates (<= today).
    For future dates (> today), reuse last year's temperature pattern
    (day-of-year mapping). This avoids 400 errors from the archive API.
    """
    if not isinstance(load_df.index, pd.DatetimeIndex):
        raise ValueError("add_madrid_temperature: index must be DatetimeIndex")

    df = load_df.copy()
    today = pd.Timestamp.today().normalize()

    hist_mask = df.index <= today
    future_mask = df.index > today

    # ---- 1) HISTORICAL TEMPERATURE FROM OPEN-METEO ----
    if hist_mask.any():
        s = df.index[hist_mask].min().date().isoformat()
        e = df.index[hist_mask].max().date().isoformat()

        try:
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": 40.4168,
                "longitude": -3.7038,
                "hourly": "temperature_2m",
                "start_date": s,
                "end_date": e,
                "timezone": "Europe/Madrid",
            }
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()

            data = resp.json()
            temp_df = pd.DataFrame({
                "time": pd.to_datetime(data["hourly"]["time"]),
                "temperature_C": data["hourly"]["temperature_2m"],
            }).set_index("time")

            df.loc[hist_mask, "temperature_C"] = temp_df["temperature_C"].reindex(
                df.index[hist_mask], method="ffill"
            )

            print("✅ Real Madrid temperature applied for historical period.")

        except Exception as e:
            print(f"⚠️ Failed to fetch historical temperature ({e}). Using synthetic.")
            hist_idx = df.index[hist_mask]
            doy = hist_idx.dayofyear
            base = 20 + 10 * np.sin(2*np.pi*(doy-30)/365)
            noise = np.random.normal(0, 1.5, size=len(hist_idx))
            df.loc[hist_mask, "temperature_C"] = base + noise

    # ---- 2) FUTURE DATES – CLIMATOLOGY FROM LAST YEAR ----
    if future_mask.any():
        hist_temp = df.loc[hist_mask, "temperature_C"].dropna()
        future_idx = df.index[future_mask]

        if not hist_temp.empty:
            print("🌡️ Using last year's Madrid temperature pattern for future dates.")
            # Map by day-of-year (wrap around if > 365)
            hist_by_doy = hist_temp.groupby(hist_temp.index.dayofyear).mean()
            doy = future_idx.dayofyear
            wrapped_doy = (doy - 1) % len(hist_by_doy) + 1
            mapped = hist_by_doy.reindex(wrapped_doy).values
            df.loc[future_mask, "temperature_C"] = mapped
        else:
            # fallback synthetic seasonal curve
            doy = future_idx.dayofyear
            base = 20 + 10 * np.sin(2*np.pi*(doy-30)/365)
            noise = np.random.normal(0, 1.5, size=len(future_idx))
            df.loc[future_mask, "temperature_C"] = base + noise
            print("⚠️ Future temperature using synthetic seasonal model.")

    return df

# =========================================================
# 6. ADVANCED FORECASTING — PROPHET WITH WEATHER
# =========================================================

def forecast_load_and_cost_prophet(
    df_hist: pd.DataFrame,
    tariff: TariffConfig,
    start: str,
    end: str,
    scenario_multiplier: float = 1.0,
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Forecast load using Prophet with Madrid temperature as regressor.

    We model log(load_kw) so forecasts are strictly positive, and
    we use growth="flat" to avoid fake long-term drift to zero.
    """

    # --- 1. Prepare dataframe for Prophet (history) ---
    df = df_hist.copy()
    df = add_madrid_temperature(df)

    # make sure load_kw is numeric float
    eps = 1e-3  # to avoid log(0)
    load_series = pd.to_numeric(df["load_kw"], errors="coerce").fillna(0.0)
    log_y = np.log(load_series.clip(lower=eps).astype("float64"))

    df_prophet = pd.DataFrame({
        "ds": df.index,
        "y": log_y,                  # log-load
        "temp": df["temperature_C"],
    })

    # --- 2. Build and fit Prophet model ---
    m = Prophet(
        growth="flat",               # no big linear trend
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=True,
        changepoint_prior_scale=0.05,
    )
    m.add_regressor("temp")

    m.fit(df_prophet)

    # --- 3. Build future dataframe covering [start, end) ---
    freq = pd.infer_freq(df_hist.index) or "15min"
    horizon_idx = pd.date_range(start=start, end=end, freq=freq, inclusive="left")

    future = m.make_future_dataframe(
        periods=len(horizon_idx),
        freq=freq,
    )

    # --- 4. Attach temperature to future dates ---
    future_temp_df = add_madrid_temperature(pd.DataFrame(index=future["ds"]))
    future["temp"] = future_temp_df["temperature_C"].values

    # --- 5. Predict log-load and convert back to kW ---
    forecast = m.predict(future)

    mask = (forecast["ds"] >= start) & (forecast["ds"] < end)
    fdf = forecast.loc[mask].copy()
    fdf.index = pd.to_datetime(fdf["ds"])

    # yhat is log(load); convert back, enforce non-negative numerically
    load_forecast = np.exp(fdf["yhat"].astype("float64"))
    fdf["load_kw"] = load_forecast * scenario_multiplier
    fdf["load_kw"] = fdf["load_kw"].clip(lower=0)

    # --- 6. Cost calculation ---
    fdf = compute_interval_costs(fdf[["load_kw"]], tariff)
    fdf = compute_monthly_demand_charge(fdf, tariff)

    # --- 7. Summary ---
    total_energy_mwh = fdf["energy_mwh_interval"].sum()
    total_cost_eur = fdf["total_cost_eur_interval"].sum()

    summary = {
        "period_start": fdf.index.min(),
        "period_end": fdf.index.max(),
        "total_energy_mwh": total_energy_mwh,
        "total_cost_eur": total_cost_eur,
        "avg_cost_eur_per_mwh": (
            total_cost_eur / total_energy_mwh if total_energy_mwh > 0 else np.nan
        ),
    }

    return fdf, summary

# =========================================================
# 7. STREAMLIT UI
# =========================================================

st.set_page_config(
    page_title="ENLIT – Real-time Energy Cost & Forecast",
    layout="wide",
)

st.title("🔌 ENLIT – Real-time Energy Cost & Forecast (Prophet + Weather)")
st.caption("Historical 2024 analysis + 2025 load forecasting with Prophet & Madrid temperature.")

# =========================================================
# 1. SIDEBAR – DATA & TARIFF
# =========================================================

st.sidebar.header("1. Interval data")

uploaded = st.sidebar.file_uploader(
    "Upload interval Excel (optional)",
    type=["xlsx", "xls"],
    help="If empty, the default ENLIT file path in app.py is used.",
)

if uploaded is not None:
    load_df = load_interval_data(path=uploaded)
else:
    st.sidebar.info(f"Using default file:\n{LOAD_FILE}")
    load_df = load_interval_data()

st.sidebar.markdown("---")
st.sidebar.header("2. Tariff configuration")

use_sample = st.sidebar.checkbox(
    "Use sample Spanish tariff", value=True,
    help="Uncheck to customise prices and charges."
)

if use_sample:
    tariff = SPANISH_SAMPLE_TARIFF
else:
    name = st.sidebar.text_input("Tariff name", value="Custom ES tariff")

    peak = st.sidebar.number_input("Peak energy price [€/MWh]", value=100.0, step=5.0)
    offpeak = st.sidebar.number_input("Off-peak energy price [€/MWh]", value=60.0, step=5.0)
    demand_price = st.sidebar.number_input("Demand charge [€/kW·month]", value=8.0, step=1.0)
    atr = st.sidebar.number_input("ATR component [€/MWh]", value=10.0, step=1.0)
    tax = st.sidebar.number_input("Tax rate [%]", value=5.0, step=0.5) / 100.0

    peak_start = st.sidebar.number_input("Peak start hour", value=8, min_value=0, max_value=23)
    peak_end = st.sidebar.number_input("Peak end hour", value=22, min_value=1, max_value=24)

    tariff = TariffConfig(
        name=name,
        price_peak=float(peak),
        price_offpeak=float(offpeak),
        demand_price_eur_per_kw_month=float(demand_price),
        atr_eur_per_mwh=float(atr),
        tax_rate=float(tax),
        peak_start_hour=int(peak_start),
        peak_end_hour=int(peak_end),
    )

# =========================================================
# 2. BASELINE COST ENGINE
# =========================================================

cost_df = compute_interval_costs(load_df, tariff)
cost_df = compute_monthly_demand_charge(cost_df, tariff)

total_kwh = cost_df["energy_kwh_interval"].sum()
total_mwh = total_kwh / 1000.0
total_cost = cost_df["total_cost_eur_interval"].sum()
eff_price = total_cost / total_mwh if total_mwh > 0 else float("nan")

baseline_annual_cost = compute_baseline_annual_cost(cost_df)

st.subheader("Baseline – historical billing")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total energy (dataset)", f"{total_mwh:,.1f} MWh")
col2.metric("Total cost (dataset)", f"{total_cost:,.0f} €")
col3.metric("Effective price", f"{eff_price:,.1f} €/MWh")
col4.metric("Baseline annual cost (last 12 months)", f"{baseline_annual_cost:,.0f} €")

st.write(
    f"**Data range:** {cost_df.index.min().date()} → {cost_df.index.max().date()}  "
    f"(**{len(cost_df):,} intervals**)."
)

# =========================================================
# 3. TABS
# =========================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Monthly cost breakdown",
    "📅 Daily load & cost",
    "🔮 2025 Forecast (Prophet)",
    "💡 Optimization scenarios",
])

# ---------------------- TAB 1: Monthly cost ----------------------
with tab1:
    st.subheader("Monthly cost breakdown – baseline")

    monthly = cost_df.resample("ME").agg({
        "energy_cost_eur_interval": "sum",
        "atr_cost_eur_interval": "sum",
        "demand_charge_eur_interval": "sum"
    }).rename(columns={
        "energy_cost_eur_interval": "energy_cost_eur",
        "atr_cost_eur_interval": "atr_cost_eur",
        "demand_charge_eur_interval": "demand_charge_eur",
    })

    fig, ax = plt.subplots(figsize=(10, 4))
    x = monthly.index
    width = 20  # days

    ax.bar(x, monthly["energy_cost_eur"], width=width, label="Energy [€]")
    ax.bar(
        x, monthly["atr_cost_eur"], width=width,
        bottom=monthly["energy_cost_eur"],
        label="ATR [€]",
    )
    ax.bar(
        x, monthly["demand_charge_eur"], width=width,
        bottom=monthly["energy_cost_eur"] + monthly["atr_cost_eur"],
        label="Demand charge [€]",
    )

    ax.set_ylabel("Cost [€]")
    ax.set_xlabel("Month")
    ax.legend()
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    st.pyplot(fig)

# ---------------------- TAB 2: Daily view ----------------------
with tab2:
    st.subheader("Daily load & cost")

    default_day = cost_df.index.min().date()
    chosen_day = st.date_input(
        "Select day",
        value=default_day,
        min_value=cost_df.index.min().date(),
        max_value=cost_df.index.max().date(),
    )

    day_str = chosen_day.strftime("%Y-%m-%d")
    if day_str in cost_df.index.strftime("%Y-%m-%d").values:
        day = cost_df.loc[day_str]

        fig, ax1 = plt.subplots(figsize=(10, 3))
        l1 = ax1.plot(day.index, day["load_kw"], label="Load [kW]")
        ax1.set_ylabel("Load [kW]")
        ax1.set_xlabel("Time")

        ax2 = ax1.twinx()
        l2 = ax2.plot(day.index, day["total_cost_eur_interval"],
                      label="Cost per interval [€]", linestyle="--")
        ax2.set_ylabel("Cost per interval [€]")

        lines = l1 + l2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc="upper left")

        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.info("No data for the selected day.")

# ---------------------- TAB 3: Forecast ----------------------
with tab3:
    st.subheader("2025 Load Forecast – Prophet + Madrid Temperature")

    colA, colB = st.columns(2)
    with colA:
        start = st.date_input("Forecast start date", value=pd.to_datetime("2025-01-01")).strftime("%Y-%m-%d")
    with colB:
        end = st.date_input("Forecast end date (exclusive)", value=pd.to_datetime("2026-01-01")).strftime("%Y-%m-%d")

    scen_mult = st.slider(
        "Scenario multiplier on forecasted load (e.g. +10% demand = 1.1)",
        min_value=0.5, max_value=1.5, step=0.05, value=1.0,
    )

    run_forecast = st.button("Run Prophet forecast")

    if run_forecast:
        with st.spinner("Running Prophet with weather regressors…"):
            forecast_df, forecast_summary = forecast_load_and_cost_prophet(
                load_df,
                tariff,
                start=start,
                end=end,
                scenario_multiplier=scen_mult,
            )

        st.success("Forecast completed.")

        col1f, col2f, col3f = st.columns(3)
        col1f.metric("Forecast period energy", f"{forecast_summary['total_energy_mwh']:,.1f} MWh")
        col2f.metric("Forecast period cost", f"{forecast_summary['total_cost_eur']:,.0f} €")
        col3f.metric("Avg forecast price", f"{forecast_summary['avg_cost_eur_per_mwh']:,.1f} €/MWh")

        # Plot 2024 vs 2025 (or whatever forecast year) overlay
        st.markdown("#### Historical 2024 vs forecasted 2025 load")

        # Slice 2024 history
        hist_mask = (
            (load_df.index >= "2024-01-01") &
            (load_df.index < "2025-01-01")
        )
        hist_2024 = load_df.loc[hist_mask]

        fig, ax = plt.subplots(figsize=(16, 3.5))
        if not hist_2024.empty:
            ax.plot(hist_2024.index, hist_2024["load_kw"], label="Historical 2024 [kW]", linewidth=1)

        ax.plot(forecast_df.index, forecast_df["load_kw"], label="Forecast 2025 [kW]", linewidth=1)

        ax.set_xlabel("Time")
        ax.set_ylabel("Load [kW]")
        ax.set_title("Historical 2024 vs Forecast 2025 – Load")
        ax.legend()
        ax.grid(True, linestyle=":", linewidth=0.5)
        plt.tight_layout()
        st.pyplot(fig)

        st.caption(
            "Note: Prophet is fit on 2024 data with Madrid temperature as a regressor. "
            "Future temperatures reuse last year's pattern (day-of-year climatology)."
        )

# ---------------------- TAB 4: Optimization scenarios ----------------------
with tab4:
    st.subheader("💡 Optimization scenarios – CAPEX vs yearly savings")

    st.markdown(
        """
        This tab runs several **what-if actions** on the historical profile:
        - Overall efficiency improvement (kWh ↓)
        - Peak-shaving (kW ↓)
        - Peak → off-peak shifting
        - Forecast-based peak avoidance
        - CO₂-aware shifting (price + CO₂)
        - RL-style flexible load control
        """
    )

    colA, colB = st.columns(2)
    with colA:
        reduction_pct = st.slider("Overall consumption reduction [%]", 0.0, 20.0, 5.0, 1.0) / 100.0
        peak_reduction_kw = st.number_input("Peak shaving amount [kW]", 0.0, 1000.0, 200.0, 10.0)
        shift_fraction = st.slider("Peak → off-peak shifted energy [%]", 0.0, 50.0, 15.0, 1.0) / 100.0
    with colB:
        flex_fraction = st.slider("Forecast-based flexible load [%]", 0.0, 50.0, 20.0, 1.0) / 100.0
        forecast_window_h = st.slider("Forecast window [hours]", 1.0, 24.0, 4.0, 1.0)
        lambda_co2 = st.slider("CO₂ weight λ (price vs CO₂)", 0.0, 3.0, 1.0, 0.1)

    st.markdown("**CAPEX assumptions** (you can tune as you like):")
    colC, colD, colE = st.columns(3)
    with colC:
        capex_eff = st.number_input("CAPEX – efficiency [€]", 0.0, 1_000_000.0, 30_000.0, 1_000.0)
        capex_peak = st.number_input("CAPEX – peak-shaving [€]", 0.0, 1_000_000.0, 80_000.0, 1_000.0)
    with colD:
        capex_shift = st.number_input("CAPEX – peak → off-peak [€]", 0.0, 1_000_000.0, 10_000.0, 1_000.0)
        capex_forecast = st.number_input("CAPEX – forecast control [€]", 0.0, 1_000_000.0, 50_000.0, 1_000.0)
    with colE:
        capex_co2 = st.number_input("CAPEX – CO₂-aware [€]", 0.0, 1_000_000.0, 60_000.0, 1_000.0)
        capex_rl = st.number_input("CAPEX – RL control [€]", 0.0, 1_000_000.0, 70_000.0, 1_000.0)

    run_opt = st.button("Run optimization scenarios")

    if run_opt:
        with st.spinner("Evaluating action scenarios…"):
            actions = []

            # 1) Overall reduction
            actions.append(
                scenario_reduce_overall(
                    cost_df, tariff,
                    reduction_pct=reduction_pct,
                    capex_eur=capex_eff,
                )
            )

            # 2) Peak shaving
            actions.append(
                scenario_reduce_peak(
                    cost_df, tariff,
                    peak_reduction_kw=peak_reduction_kw,
                    capex_eur=capex_peak,
                )
            )

            # 3) Peak → off-peak shifting
            actions.append(
                scenario_shift_peak_energy(
                    cost_df, tariff,
                    shift_fraction=shift_fraction,
                    capex_eur=capex_shift,
                )
            )

            # Build synthetic CO₂ and RL actions for advanced scenarios
            energy_mwh = cost_df["energy_mwh_interval"].astype(float)
            energy_mwh = energy_mwh.where(energy_mwh != 0, np.nan)

            price_eur_mwh = (cost_df["energy_cost_eur_interval"] / energy_mwh).astype(float)
            price_eur_mwh = price_eur_mwh.ffill().bfill()

            co2_norm = (price_eur_mwh - price_eur_mwh.min()) / (
                price_eur_mwh.max() - price_eur_mwh.min() + 1e-9
            )
            co2_intensity = 200 + 200 * co2_norm  # 200–400 kgCO2/MWh

            high_price_thresh = price_eur_mwh.quantile(0.8)
            rl_actions = pd.Series(
                np.where(price_eur_mwh > high_price_thresh, 0.3, 0.0),
                index=cost_df.index,
            )

            # 4) Forecast-based peak avoidance
            actions.append(
                scenario_peak_forecast_avoidance(
                    cost_df, tariff,
                    flex_fraction=flex_fraction,
                    forecast_window_h=forecast_window_h,
                    capex_eur=capex_forecast,
                )
            )

            # 5) CO₂-aware shifting
            actions.append(
                scenario_co2_aware_shift(
                    cost_df, tariff,
                    co2_intensity_kg_per_mwh=co2_intensity,
                    shift_fraction=shift_fraction,
                    lambda_co2=lambda_co2,
                    capex_eur=capex_co2,
                )
            )

            # 6) RL-based control
            actions.append(
                scenario_rl_flex_control(
                    cost_df, tariff,
                    learned_action_fraction=rl_actions,
                    capex_eur=capex_rl,
                )
            )

            # Build dataframe for display
            actions_df = pd.DataFrame([a.__dict__ for a in actions])
            actions_df["roi_simple_payback_years"] = actions_df["roi_simple_payback_years"].replace(
                [np.inf, -np.inf], np.nan
            )

        st.success("Scenarios evaluated.")

        st.markdown("### Scenario comparison")

        # Highlight best payback (lowest positive)
        best_idx = actions_df["roi_simple_payback_years"].replace(0, np.nan).idxmin()

        styled = (
            actions_df.style
            .format({
                "capex_eur": "{:,.0f}",
                "savings_eur_per_year": "{:,.0f}",
                "roi_simple_payback_years": "{:,.1f}",
            })
            .highlight_min("roi_simple_payback_years", color="#c7f5d9")
        )

        st.dataframe(styled, use_container_width=True)

        st.caption(
            "Simple payback = CAPEX / annual savings, based on the last 12 months of data. "
            "Values with no savings show as blank (∞ payback)."
        )


# In[ ]:




