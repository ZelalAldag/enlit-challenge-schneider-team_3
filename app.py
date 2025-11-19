import streamlit as st
import pandas as pd
import plots
from datetime import datetime, timedelta
import numpy as np
import plotly.graph_objects as go
import chatbot

# --- Schneider Electric Branding Colors ---
SCHNEIDER_GREEN = "#009E06"
SCHNEIDER_GRAY = "#3D3D3D"
LIGHT_GRAY = "#F4F4F4"
FONT_FAMILY = "'Segoe UI', 'Arial', sans-serif"

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="Energy Dashboard",
    layout="wide",
)


# --- Data Function ---
def get_data():
    np.random.seed(42)
    dates = pd.date_range(datetime.now() - timedelta(days=30), periods=720, freq="h")
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


# --- Load Data ---
data = get_data()

# --- SIDEBAR: Global Simulation Parameters ---
st.sidebar.title("⚙️ Simulation Controls")
st.sidebar.markdown("---")

# Date Range Filter
st.sidebar.subheader("📅 Date Range")
min_date = data["Timestamp"].min().date()
max_date = data["Timestamp"].max().date()
start_date = st.sidebar.date_input(
    "Start date",
    value=min_date,
    min_value=min_date,
    max_value=max_date,
    format="YYYY-MM-DD",
    key="start_date_selector",
)
end_date = st.sidebar.date_input(
    "End date",
    value=max_date,
    min_value=min_date,
    max_value=max_date,
    format="YYYY-MM-DD",
    key="end_date_selector",
)

# Ensure start_date <= end_date
if start_date > end_date:
    st.sidebar.error("Start date must be before or equal to end date.")

filtered_df = data[
    (data["Timestamp"].dt.date >= start_date) & (data["Timestamp"].dt.date <= end_date)
]

# Market & Efficiency Sliders
st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Market & Efficiency")
market_increase = st.sidebar.slider("Market Price % Increase", 0, 50, 10, step=1)
efficiency = st.sidebar.slider("Equipment Efficiency %", 80, 110, 100, step=1)

# --- MAIN CONTENT AREA ---

# Header
st.markdown(
    f"<h1 style='color: {SCHNEIDER_GREEN};'> Real-time Energy Cost Management</h1>",
    unsafe_allow_html=True,
)


# --- ROW 3: Tabbed Content ---
tabs = st.tabs(
    [
        "🔍 Real-Time Monitor",
        "📈 Cost & Forecast",
        "✅ Optimization Actions",
        "🏭 Industrial Site Map",
    ]
)

# --- TAB 1: Real-Time Monitor ---
with tabs[0]:
    left_col, right_col = st.columns([2, 1])

    with left_col:
        # --- ZONE 1: Permanent Alert Banner (Critical Anomaly Detector) ---

        # Define current and forecast loads
        current_load = 1250  # kW (placeholder)
        forecast_load = 1100  # kW (placeholder)

        # Calculate variance
        variance_percent = ((current_load - forecast_load) / forecast_load) * 100

        # Display alert based on variance threshold
        if variance_percent > 10:
            st.error(
                f"⚠️ **CRITICAL ANOMALY:** Total Site Consumption is **{variance_percent:.1f}% above forecast**. "
                f"Predicted cost impact: +€450/day."
            )
        else:
            st.success(
                "✅ **System Normal:** Real-time consumption within predicted range."
            )

        # --- SECTION: Currently Executed Actions & Recomputed Forecasts ---
        st.markdown("---")
        st.markdown("### Executed Actions & Updated Forecasts")

        # Initialize session state for executed actions if not exists
        if "executed_actions" not in st.session_state:
            st.session_state.executed_actions = []

        # Get executed actions from session state (these come from Tab 3 when user executes)
        executed_actions_list = st.session_state.executed_actions

        st.markdown("#### Executed Actions")

        if executed_actions_list:
            # Display executed actions in cards
            for idx, action in enumerate(executed_actions_list):
                st.markdown(
                    f"""
                    <div style='background-color: {LIGHT_GRAY}; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 10px;'>
                        <h4 style='color: {SCHNEIDER_GRAY}; margin: 0;'>{action["name"]}</h4>
                        <p style='color: {SCHNEIDER_GREEN}; margin: 10px 0 5px 0; font-size: 14px;'>Savings: €{action["savings"]:,}</p>
                        <p style='color: {SCHNEIDER_GREEN}; margin: 0; font-size: 12px;'>Status: Active</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("---")

            # Calculate recomputed forecasts with executed actions
            st.markdown("#### 📊 Recomputed Optimization Values")

            # Use the encapsulated forecast comparison plot helper
            import forecast_comparison_plot as fcp

            fig_pi, baseline_month, actual_cost_month, efficiency_gain = (
                fcp.build_forecast_comparison_plot(
                    executed_actions_list,
                    market_increase,
                    SCHNEIDER_GREEN,
                    SCHNEIDER_GRAY,
                )
            )

            st.plotly_chart(fig_pi, width="stretch")

            metric_col1, metric_col2, metric_col3 = st.columns(3)

            with metric_col1:
                st.metric(
                    label="💰 Previous Baseline (Month)",
                    value=f"€{baseline_month:,.0f}",
                    delta="Before actions",
                )

            with metric_col2:
                st.metric(
                    label="📉 Recomputed Cost (Month)",
                    value=f"€{actual_cost_month:,.0f}",
                    delta=f"€{baseline_month - actual_cost_month:,.0f} saved",
                    delta_color="inverse",
                )

            with metric_col3:
                st.metric(
                    label="⚡ Efficiency Gain",
                    value=f"{efficiency_gain:.1f}%",
                    delta="From executed actions",
                )
        else:
            st.info(
                "📌 No actions executed yet. Go to Tab 3 to execute optimization actions."
            )

    with right_col:
        chatbot.render_chatbot()

        # st.markdown(
        #     f"""
        #     <div style='background-color: {LIGHT_GRAY}; padding: 20px; border-radius: 8px; border: 2px solid {SCHNEIDER_GREEN}; height: 380px; overflow-y: auto;'>
        #         <h4 style='color: {SCHNEIDER_GREEN}; margin: 0 0 15px 0;'>Energy Optimization Bot</h4>
        #         <div style='background-color: white; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>
        #             <p style='color: {SCHNEIDER_GRAY}; margin: 0; font-size: 13px;'>👋 Hi! I'm your Energy Optimization Assistant. Ask me about:</p>
        #             <ul style='color: {SCHNEIDER_GRAY}; font-size: 12px; margin: 10px 0 0 0;'>
        #                 <li>Cost reduction strategies</li>
        #                 <li>Equipment efficiency tips</li>
        #                 <li>Action recommendations</li>
        #                 <li>Alert analysis</li>
        #             </ul>
        #         </div>
        #         <div style='text-align: center; padding: 20px;'>
        #             <p style='color: {SCHNEIDER_GRAY}; font-size: 12px;'>Chat feature ready for integration</p>
        #         </div>
        #     </div>
        #     """,
        #     unsafe_allow_html=True,
        # )


# --- TAB 2: Cost & Forecast ---
with tabs[1]:
    st.subheader("Budget Forecast & Simulation")

    # Prepare forecast data with three scenarios
    forecast_df = filtered_df.copy()

    if not forecast_df.empty:
        # Historical Cost (baseline)
        forecast_df["Historical_Cost_EUR"] = forecast_df["Cost_EUR"]

        # Baseline Forecast (applies market price increase only)
        forecast_df["Baseline_Forecast_EUR"] = forecast_df["Cost_EUR"] * (
            1 + market_increase / 100
        )

        # Optimized Forecast (applies both market and efficiency gains)
        forecast_df["Optimized_Forecast_EUR"] = (
            forecast_df["Cost_EUR"] * (1 + market_increase / 100) * (100 / efficiency)
        )

    # Create line chart with three scenarios
    fig4 = plots.create_line_chart(
        forecast_df,
        x="Timestamp",
        y=["Historical_Cost_EUR", "Baseline_Forecast_EUR", "Optimized_Forecast_EUR"],
        title="Cost Scenarios: Historical vs. Baseline vs. Optimized",
        y_label="Cost (EUR)",
        x_label="Time",
    )
    st.plotly_chart(fig4, width="stretch")

    st.markdown("---")

    # Calculate month-end projections (30 days)
    if not forecast_df.empty:
        baseline_daily_avg = forecast_df["Baseline_Forecast_EUR"].sum() / max(
            1, len(forecast_df)
        )
        optimized_daily_avg = forecast_df["Optimized_Forecast_EUR"].sum() / max(
            1, len(forecast_df)
        )

        baseline_month_end = baseline_daily_avg * 30
        optimized_month_end = optimized_daily_avg * 30
    else:
        baseline_month_end = 45000
        optimized_month_end = 38000

    # Display month-end metrics
    metric_col1, metric_col2 = st.columns(2)

    with metric_col1:
        st.metric(
            label="Baseline Projected Month-End Cost ()",
            value=f"€{baseline_month_end:,.0f}",
            delta=f"{market_increase}% market increase",
        )

    with metric_col2:
        savings = baseline_month_end - optimized_month_end
        st.metric(
            label="Optimized Projected Month-End Cost",
            value=f"€{optimized_month_end:,.0f}",
            delta=f"Save €{savings:,.0f}",
            delta_color="inverse",
        )

# --- TAB 3: Optimization Actions ---
with tabs[2]:
    st.subheader("Optimization Actions - Direct Response to Alert")

    # Interactive Checklist for Optimization Actions
    st.markdown("### Recommended Actions (Select to Apply)")

    # Create optimization actions with actionable data
    optimization_actions = pd.DataFrame(
        {
            "Apply?": [False, False],
            "Action Name": [
                "Shift Polishing to P6 (Off-Peak)",
                "Fix Chiller Valve",
            ],
            "Investment": ["€0", "€500"],
            "Savings/Yr": ["€5,200", "€2,100"],
            "ROI": ["Immediate", "400%"],
        }
    )

    # Create editable data editor
    edited_actions = st.data_editor(
        optimization_actions,
        hide_index=True,
        use_container_width=True,
        key="optimization_editor",
    )

    # Calculate total savings based on checked items
    total_savings = 0
    for idx, row in edited_actions.iterrows():
        if row["Apply?"]:
            # Extract numeric value from savings string
            savings_str = row["Savings/Yr"].replace("€", "").replace(",", "")
            try:
                savings_value = float(savings_str)
                total_savings += savings_value
            except ValueError:
                pass

    st.markdown("---")

    # Display potential savings metric
    st.metric(
        label="Potential Savings (Selected Actions)",
        value=f"€{total_savings:,.0f}",
        delta="From checked actions",
    )

    st.markdown("---")

    # Execute button
    if st.button(
        "🚀 EXECUTE OPTIMIZATION PLAN",
        type="primary",
        use_container_width=True,
    ):
        # Extract and store executed actions
        executed_actions_list = []
        for idx, row in edited_actions.iterrows():
            if row["Apply?"]:
                savings_str = row["Savings/Yr"].replace("€", "").replace(",", "")
                try:
                    savings_value = float(savings_str)
                    executed_actions_list.append(
                        {"name": row["Action Name"], "savings": savings_value}
                    )
                except ValueError:
                    pass

        # Store in session state
        st.session_state.executed_actions = executed_actions_list

        st.toast("✅ Optimization commands sent to PLCs!", icon="✅")
        st.success(
            f"**Optimization Plan Activated!**\n\n"
            f"- Actions applied: {edited_actions['Apply?'].sum()}\n"
            f"- Expected annual savings: €{total_savings:,.0f}\n"
            f"- Estimated execution time: 2-4 hours"
        )

    st.markdown("---")
    st.markdown("### Extended Action Catalog")

    # Extended actions catalog
    extended_actions_df = pd.DataFrame(
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

    st.dataframe(extended_actions_df, width="stretch", use_container_width=True)

# --- TAB 4: Industrial Site Map ---
with tabs[3]:
    st.subheader("Industrial Site Map - Component Monitoring")

    # Charts Section (moved from Tab 1)
    st.markdown("### 📊 Consumption Breakdown & Analysis")

    # Local Control: Resample Period
    resample_map = {
        "15 min": "15T",
        "Hourly": "h",
        "Daily": "D",
        "Weekly": "W",
        "Monthly": "M",
    }
    resample_period = st.selectbox(
        "📊 Resample Period",
        options=list(resample_map.keys()),
        index=1,
        help="Affects the line chart. Pie and scatter use raw filtered data.",
        key="resample_tab4",
    )

    # Resample for line chart only
    if not filtered_df.empty:
        df_line = (
            filtered_df.set_index("Timestamp")
            .resample(resample_map[resample_period])
            .sum(numeric_only=True)
            .reset_index()
        )
    else:
        df_line = filtered_df.copy()

    col1, col2 = st.columns([2, 2])

    with col1:
        fig1 = plots.create_line_chart(
            df_line,
            x="Timestamp",
            y="Consumption_kWh",
            title="📈 Energy Consumption Over Time",
            y_label="Consumption (kWh)",
            x_label="Time",
        )
        st.plotly_chart(fig1, width="stretch")

    with col2:
        machine_cols = ["Chillers_kWh", "Compressors_kWh", "Polishing_kWh"]
        machine_sums = filtered_df[machine_cols].sum()
        pie_df = pd.DataFrame(
            {"Machine": machine_cols, "Consumption": machine_sums.values}
        )
        fig2 = plots.create_pie_chart(
            pie_df,
            names="Machine",
            values="Consumption",
            title="⚙️ Historical Breakdown",
        )
        st.plotly_chart(fig2, width="stretch")

    # Initialize session state for components if not exists
    if "components" not in st.session_state:
        st.session_state.components = {
            "Chillers": {
                "value": 245.50,
                "unit": "kW",
                "efficiency": "92%",
                "year": 2019,
            },
            "Compressors": {
                "value": 156.75,
                "unit": "kW",
                "efficiency": "85%",
                "year": 2018,
            },
            "Polishing": {
                "value": 98.25,
                "unit": "kW",
                "efficiency": "88%",
                "year": 2020,
            },
        }

    st.markdown("---")

    # Display Industrial Site Diagram
    st.markdown("### 📊 Real-Time Industrial Site Diagram")

    # Calculate total load
    total_load = sum(comp["value"] for comp in st.session_state.components.values())

    # Create component boxes and diagram
    diagram_col = st.columns(1)[0]

    with diagram_col:
        # Component Cards in a grid
        num_cols = min(3, len(st.session_state.components))
        component_cols = st.columns(num_cols)

        for idx, (comp_name, comp_data) in enumerate(
            st.session_state.components.items()
        ):
            col_idx = idx % num_cols
            with component_cols[col_idx]:
                st.markdown(
                    f"""
                    <div style='background-color: {SCHNEIDER_GREEN}; padding: 15px; border-radius: 8px; border: 2px solid {SCHNEIDER_GRAY};'>
                        <h4 style='color: white; margin: 0;'>{comp_name}</h4>
                        <p style='color: white; margin: 10px 0 5px 0; font-size: 24px; font-weight: bold;'>{comp_data["value"]:.2f} {comp_data["unit"]}</p>
                        <p style='color: white; margin: 5px 0; font-size: 12px;'>Efficiency: {comp_data["efficiency"]}</p>
                        <p style='color: white; margin: 0; font-size: 12px;'>Year: {comp_data["year"]}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Arrow/connector visualization
        st.markdown(
            f"""
            <div style='text-align: center; margin: 20px 0;'>
                <h3 style='color: {SCHNEIDER_GRAY}; margin: 0;'>⬇️ ⬇️ ⬇️</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Total Load Box
        st.markdown(
            f"""
            <div style='background-color: #FF6B6B; padding: 20px; border-radius: 8px; border: 3px solid {SCHNEIDER_GRAY}; text-align: center;'>
                <h3 style='color: white; margin: 0;'>⚡ Total Site Load</h3>
                <p style='color: white; margin: 10px 0 0 0; font-size: 32px; font-weight: bold;'>{total_load:.2f} kW</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Component Management Section
    st.markdown("### Component Management")

    # Editable components table
    components_df = pd.DataFrame(
        [
            {
                "Component": name,
                "Power (kW)": data["value"],
                "Efficiency": data["efficiency"],
                "Year": data["year"],
                "% of Total": (
                    f"{(data['value'] / total_load * 100):.1f}%"
                    if total_load > 0
                    else "0%"
                ),
            }
            for name, data in st.session_state.components.items()
        ]
    )

    st.dataframe(components_df, width="stretch", use_container_width=True)

    # Add component form
    col_add1, col_add2, col_add3, col_add4, col_add5 = st.columns([2, 1, 1, 1, 1])

    with col_add1:
        new_component_name = st.text_input(
            "Component Name",
            placeholder="e.g., Pump, Motor, Lighting",
            key="new_comp_name",
        )

    with col_add2:
        new_component_value = st.number_input(
            "Power (kW)", min_value=0.0, value=50.0, step=1.0, key="new_comp_value"
        )

    with col_add3:
        new_component_value_efficiency = st.text_input(
            "Efficiency", value="90%", key="new_comp_efficiency"
        )

    with col_add4:
        new_component_value_year = st.number_input(
            "Year",
            min_value=2000,
            max_value=datetime.now().year,
            value=2022,
            step=1,
            key="new_comp_year",
        )

    with col_add5:
        st.text("")
        if st.button("➕ Add Component", use_container_width=True):
            if (
                new_component_name
                and new_component_name not in st.session_state.components
            ):
                st.session_state.components[new_component_name] = {
                    "value": new_component_value,
                    "unit": "kW",
                    "efficiency": new_component_value_efficiency,
                    "year": new_component_value_year,
                }
                st.toast(f"✅ {new_component_name} added successfully!")
                st.rerun()
            elif new_component_name in st.session_state.components:
                st.warning("Component already exists!")
