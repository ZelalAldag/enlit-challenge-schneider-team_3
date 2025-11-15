# enlit-challenge-schneider-team_3

INNOENERGY CAREER IMPACT CHALLENGE - Schneider Electric: Real-time Energy Cost Management - Monetize interval data and drive strategic energy investments

## Overview

This project is a modular Streamlit dashboard for the INNOENERGY CAREER IMPACT CHALLENGE - Schneider Electric: Real-time Energy Cost Management. The dashboard visualizes energy consumption, costs, forecasts, and recommended efficiency actions, using professional Schneider Electric branding and interactive Plotly charts.

## Features
- **Three interactive tabs:**
	- **Cost & Consumption Breakdown:** Line, pie, and scatter charts for cost and energy breakdowns.
	- **Budget Forecast & Simulation:** Simulate market price and efficiency changes, see projected costs.
	- **Efficiency Actions:** View and analyze top actions for savings and carbon reduction.
- **Modular code:** Plotting logic is separated in `plots.py`.
- **Easy data integration:** Replace the `get_data()` function in `app.py` to use your real data.

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

- **To use real data:**
	- Replace the `get_data()` function in `app.py` with your data import logic.
- **Branding:**
	- Colors and fonts are set for Schneider Electric, but can be changed in the CSS section of `app.py`.

## License
For hackathon/demo use only. Not for production.
