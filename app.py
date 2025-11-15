import streamlit as st
import pandas as pd
import plots
from datetime import datetime, timedelta
import numpy as np

# --- Schneider Electric Branding Colors ---
SCHNEIDER_GREEN = "#009E06"
SCHNEIDER_GRAY = "#3D3D3D"
LIGHT_GRAY = "#F4F4F4"
FONT_FAMILY = "'Segoe UI', 'Arial', sans-serif"

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="Schneider Energy Dashboard",
    layout="wide",
)

# --- Custom CSS for Branding ---


# --- Main Title ---
st.title("Schneider Electric | Real-time Energy Cost Management")


# --- Data Function ---
def get_data():
    np.random.seed(42)
    dates = pd.date_range(datetime.now() - timedelta(days=30), periods=720, freq="H")
    base_consumption = np.random.normal(500, 50, size=len(dates))
    chillers = base_consumption * np.random.uniform(0.25, 0.35, size=len(dates))
    compressors = base_consumption * np.random.uniform(0.20, 0.30, size=len(dates))
    polishing = base_consumption * np.random.uniform(0.10, 0.20, size=len(dates))
    cost_eur = base_consumption * np.random.uniform(0.12, 0.16, size=len(dates))
    reactive_power = base_consumption * np.random.uniform(0.15, 0.25, size=len(dates))
    df = pd.DataFrame(
        {
            "Timestamp": dates,
            "Consumption_kWh": base_consumption.round(2),
            "Cost_EUR": cost_eur.round(2),
            "Reactive_Power_kVARh": reactive_power.round(2),
            "Chillers_kWh": chillers.round(2),
            "Compressors_kWh": compressors.round(2),
            "Polishing_kWh": polishing.round(2),
        }
    )
    return df


data = get_data()

# --- Sidebar Controls ---
st.sidebar.title("Simulation Controls")
market_increase = st.sidebar.slider("Market Price % Increase", 0, 50, 10, step=1)
efficiency = st.sidebar.slider("Equipment Efficiency %", 80, 110, 100, step=1)

# --- Tabs ---
tabs = st.tabs(
    [
        "Cost & Consumption Breakdown",
        "Budget Forecast & Simulation",
        "Efficiency Actions",
    ]
)

# --- Tab 1: Breakdown ---
with tabs[0]:
    col1, col2 = st.columns([2, 1])
    with col1:
        fig1 = plots.create_line_chart(
            data,
            x="Timestamp",
            y="Cost_EUR",
            title="Energy Cost Over Time",
            y_label="Cost (EUR)",
            x_label="Time",
        )
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        machine_cols = ["Chillers_kWh", "Compressors_kWh", "Polishing_kWh"]
        machine_sums = data[machine_cols].sum()
        pie_df = pd.DataFrame(
            {"Machine": machine_cols, "Consumption": machine_sums.values}
        )
        fig2 = plots.create_pie_chart(
            pie_df,
            names="Machine",
            values="Consumption",
            title="Consumption Breakdown by Machine",
        )
        st.plotly_chart(fig2, use_container_width=True)
    col3, col4 = st.columns([2, 1])
    with col3:
        fig3 = plots.create_scatter_plot(
            data,
            x="Consumption_kWh",
            y="Reactive_Power_kVARh",
            title="Consumption vs. Reactive Power",
            y_label="Reactive Power (kVARh)",
            x_label="Consumption (kWh)",
        )
        st.plotly_chart(fig3, use_container_width=True)

# --- Tab 2: Forecast ---
with tabs[1]:
    # Calculate current and projected annual cost
    avg_hourly_cost = data["Cost_EUR"].mean()
    current_annual_cost = avg_hourly_cost * 24 * 365
    projected_annual_cost = (
        current_annual_cost * (1 + market_increase / 100) * (100 / efficiency)
    )
    st.metric("Current Annual Cost (EUR)", f"{current_annual_cost:,.0f}")
    st.metric("Projected Annual Cost (EUR)", f"{projected_annual_cost:,.0f}")
    # Historical vs. Forecasted Cost
    forecast_df = data.copy()
    forecast_df["Forecasted_Cost_EUR"] = (
        forecast_df["Cost_EUR"] * (1 + market_increase / 100) * (100 / efficiency)
    )
    fig4 = plots.create_line_chart(
        forecast_df,
        x="Timestamp",
        y=["Cost_EUR", "Forecasted_Cost_EUR"],
        title="Historical vs. Forecasted Cost",
        y_label="Cost (EUR)",
        x_label="Time",
    )
    st.plotly_chart(fig4, use_container_width=True)

# --- Tab 3: Actions ---
with tabs[2]:
    actions_df = pd.DataFrame(
        {
            "Action": [
                "Upgrade Chillers",
                "Install VFDs",
                "Optimize Scheduling",
                "Insulation Improvements",
                "Compressor Maintenance",
                "LED Lighting",
                "Energy Awareness Training",
            ],
            "Est_Annual_Savings_EUR": [12000, 9500, 8000, 7000, 6500, 4000, 2500],
            "Est_Cost_EUR": [30000, 18000, 5000, 12000, 4000, 2000, 1000],
            "ROI_Percent": [40, 53, 160, 58, 163, 200, 250],
            "Carbon_Reduction_tCO2": [30, 22, 18, 15, 12, 8, 5],
        }
    )
    top5 = actions_df.nlargest(5, "Est_Annual_Savings_EUR")
    fig5 = plots.create_bar_chart(
        top5,
        x="Action",
        y="Est_Annual_Savings_EUR",
        title="Top 5 Actions by Savings",
        y_label="Est. Annual Savings (EUR)",
        x_label="Action",
    )
    st.plotly_chart(fig5, use_container_width=True)
    st.dataframe(actions_df, use_container_width=True)
