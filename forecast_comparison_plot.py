import pandas as pd
import numpy as np
import plotly.graph_objects as go


def build_forecast_comparison_plot(
    executed_actions_list, market_increase, schneider_green, schneider_gray
):
    """Builds a Plotly figure comparing a previous baseline forecast (historical window)
    with an updated forecast (future window) and a simple prediction interval.

    Previous Baseline: 2025-11-01 -> 2025-11-19 (inclusive)
    Updated Forecast:   2025-11-19 -> 2026-11-01 (inclusive)

    Returns: (fig, baseline_month, actual_cost_month, efficiency_gain)
    """

    # Compute total executed savings
    total_executed_savings = sum(
        action.get("savings", 0) for action in executed_actions_list
    )

    # Per-hour saving (distribute annual savings evenly across hours)
    per_hour_saving = (
        total_executed_savings / (365 * 24) if total_executed_savings else 0
    )

    # Define baseline and updated windows
    baseline_start = pd.Timestamp("2025-11-01")
    baseline_end = pd.Timestamp("2025-11-19")
    updated_start = pd.Timestamp("2025-11-19")
    updated_end = pd.Timestamp("2026-11-01")

    # Prepare baseline dataframe (hourly) using a synthetic random series
    # NOTE: intentionally do NOT use `filtered_df` here — create a reproducible
    # synthetic baseline between baseline_start and baseline_end.
    np.random.seed(42)
    idx = pd.date_range(baseline_start, baseline_end, freq="h")
    # Generate a realistic-looking cost series (mean=100, std=10) and clip to positive
    cost_vals = np.random.normal(loc=100.0, scale=10.0, size=len(idx))
    cost_vals = np.clip(cost_vals, a_min=1.0, a_max=None)
    df_base = pd.DataFrame({"Timestamp": idx, "Cost_EUR": np.round(cost_vals, 2)})

    # Resample baseline hourly (ensure index aligned)
    df_base = (
        df_base.set_index("Timestamp")
        .resample("h")
        .sum(numeric_only=True)
        .reset_index()
    )

    # Baseline series adjusted by market increase
    baseline_series = df_base["Cost_EUR"] * (1 + market_increase / 100)

    # Rolling std on raw cost for a simple PI estimate
    rolling_std = df_base["Cost_EUR"].rolling(window=24, min_periods=1).std().fillna(0)
    pred_upper = baseline_series + 1.96 * rolling_std
    pred_lower = baseline_series - 1.96 * rolling_std

    # Build updated (future) index and series using baseline mean as anchor
    baseline_hourly_mean = (
        baseline_series.mean() if not baseline_series.empty else 100.0
    )
    updated_index = pd.date_range(updated_start, updated_end, freq="h")
    # Simple updated forecast: baseline hourly mean minus per-hour saving
    updated_vals = np.full(len(updated_index), baseline_hourly_mean - per_hour_saving)
    updated_series = pd.Series(updated_vals, index=updated_index)

    # Create the figure
    fig = go.Figure()

    # Add PI shading (over baseline window)
    if not df_base.empty:
        fig.add_trace(
            go.Scatter(
                x=df_base["Timestamp"],
                y=pred_upper,
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                name="PI Upper",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df_base["Timestamp"],
                y=pred_lower,
                mode="lines",
                fill="tonexty",
                fillcolor="rgba(150,150,150,0.2)",
                line=dict(width=0),
                showlegend=False,
                name="PI Lower",
            )
        )

    # Baseline trace (extend historical baseline into the future window)
    # Create a continuous baseline that shows historical baseline values
    # and extends into the future up to updated_end using the baseline hourly mean.
    baseline_hourly_mean = (
        baseline_series.mean() if not baseline_series.empty else 100.0
    )
    updated_index = pd.date_range(updated_start, updated_end, freq="h")

    # Build concatenated x/y for the baseline full line
    x_baseline_full = list(df_base["Timestamp"]) + list(updated_index)
    y_baseline_full = list(baseline_series.values) + list(
        np.full(len(updated_index), baseline_hourly_mean)
    )

    fig.add_trace(
        go.Scatter(
            x=x_baseline_full,
            y=y_baseline_full,
            mode="lines",
            name="Previous Forecast (Baseline)",
            line=dict(color=schneider_gray, width=2, dash="dash"),
        )
    )

    # Updated forecast (future period)
    fig.add_trace(
        go.Scatter(
            x=updated_index,
            y=updated_series,
            mode="lines",
            name="Updated Forecast (After Actions)",
            line=dict(color=schneider_green, width=3),
        )
    )

    # Determine exceedance relative to baseline PI (use mean upper bound)
    if not df_base.empty:
        pred_upper_threshold = pred_upper.mean()
    else:
        pred_upper_threshold = baseline_hourly_mean + 1.96 * rolling_std.mean()

    exceed_mask = updated_series > pred_upper_threshold
    if exceed_mask.any():
        first_idx = exceed_mask.idxmax()
        x_val = updated_series.index[first_idx]
        y_val = updated_series.iloc[first_idx]
        fig.add_trace(
            go.Scatter(
                x=[x_val],
                y=[y_val],
                mode="markers+text",
                marker=dict(color="#FF6B6B", size=10),
                text=["Exceeds PI"],
                textposition="top center",
                name="Exceedance",
            )
        )

    fig.update_layout(
        template="plotly_white",
        title="Recomputed Forecast vs Previous Forecast (with Prediction Interval)",
        xaxis_title="Time",
        yaxis_title="Cost (EUR)",
        hovermode="x unified",
    )

    # Compute summary metrics
    if not df_base.empty:
        baseline_daily = df_base["Cost_EUR"].sum() / max(1, len(df_base))
        baseline_month = baseline_daily * 30
        actual_savings_daily = total_executed_savings / 365
        actual_cost_daily = baseline_daily - actual_savings_daily
        actual_cost_month = actual_cost_daily * 30
        efficiency_gain = (
            total_executed_savings / (baseline_month * 12) * 100
            if baseline_month * 12 > 0
            else 0
        )
    else:
        baseline_month = 45000
        actual_cost_month = baseline_month - (total_executed_savings / 12)
        efficiency_gain = 0

    return fig, baseline_month, actual_cost_month, efficiency_gain
