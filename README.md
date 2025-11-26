# enlit-challenge-schneider-team_3

INNOENERGY CAREER IMPACT CHALLENGE - Schneider Electric: Real-time Energy Cost Management - Monetize interval data and drive strategic energy investments

## Overview

This project is a modular Streamlit dashboard for the INNOENERGY CAREER IMPACT CHALLENGE - Schneider Electric: Real-time Energy Cost Management. The dashboard visualizes energy consumption, costs, forecasts, and recommended efficiency actions, using professional Schneider Electric branding and interactive Plotly charts.

## Features

### Dashboard Layout
- **Fixed Header + Tabbed Content:** Professional, clean UI optimized for energy cost management.
- **Sidebar Controls:** Global date range filter, market price simulation, and equipment efficiency adjustment.
- **Executive KPIs (Row 1):** Total Cost (Period), Total Load (kWh), Estimated CO₂.
- **ZONE 1 - Alert Banner (Row 2):** Real-time critical anomaly detector with variance analysis and cost impact predictions.
- **Three Interactive Tabs (Row 3):**
  - **🔍 Real-Time Monitor:** Live consumption trends, equipment breakdown (pie chart), and consumption vs. reactive power correlation.
  - **📈 Cost & Forecast:** Budget metrics, current vs. projected annual costs, and historical vs. forecasted trend lines.
  - **✅ Optimization Actions:** Top 5 efficiency improvements by savings, ROI analysis, and carbon reduction potential.

### Technical Features
- **Modular code:** Plotting logic separated in `plots.py` for reusability and maintainability.
- **Responsive charts:** Interactive Plotly visualizations with professional Schneider Electric branding (Green #009E06).
- **Configurable theme:** Streamlit theme settings in `.streamlit/config.toml` for consistent branding.
- **Easy data integration:** Replace the `get_data()` function in `app.py` to connect your real data source.

## Quickstart

### 1. Clone the repository
```bash
git clone <repo-url>
cd enlit-challenge-schneider-team_3
```

### 2. Create and activate a virtual environment (.venv)
```bash
# Create virtual environment in .venv folder
python -m venv .venv

# Activate on Windows (bash)
source .venv/Scripts/activate
# Or, if using Command Prompt:
.venv\Scripts\activate.bat
```

### 3. Install requirements
```bash
pip install -r requirements.txt
```

### 4. Run the Streamlit dashboard
```bash
streamlit run app.py
```

The dashboard will open in your browser. Use the sidebar to simulate market and efficiency changes.

## Project Structure

- `app.py` — Main Streamlit app, layout, logic, and data function
- `plots.py` — Reusable Plotly chart functions (line, bar, pie, scatter)
- `requirements.txt` — Python dependencies
- `data/` — (Optional) Place for your real data files

## Customization

### Connecting Real Data
- Replace the `get_data()` function in `app.py` with your data import logic (CSV, database, API, etc.).
- Ensure your DataFrame contains: `Timestamp`, `Consumption_kWh`, `Cost_EUR`, `Reactive_Power_kVARh`, and equipment-specific columns.

### Critical Anomaly Detection (ZONE 1)
- Modify `current_load` and `forecast_load` values in the alert banner section to reflect your system's real-time and forecasted loads.
- Adjust the `10%` variance threshold as needed for your operations.

### Branding & Theme
- Colors and fonts are configured in `.streamlit/config.toml` (Primary Green: `#009E06`, Secondary Gray: `#3D3D3D`).
- To customize further, edit the Streamlit theme file or modify the color constants in `app.py`.

### Chart Resample Periods
- In the **Real-Time Monitor** tab, users can select resample periods: 15 min, Hourly, Daily, Weekly, Monthly.
- This affects only the line chart; pie and scatter plots use raw filtered data for accuracy.

## License
For hackathon/demo use only. Not for production.
