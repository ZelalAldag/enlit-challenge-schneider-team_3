import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

SCHNEIDER_GREEN = '#009E06'
SCHNEIDER_GRAY = '#3D3D3D'
FONT_FAMILY = "'Segoe UI', 'Arial', sans-serif"

# --- Line Chart ---
def create_line_chart(df, x, y, title, y_label, x_label, color=None):
    if isinstance(y, list) and len(y) > 1:
        fig = px.line(df, x=x, y=y, title=title, color_discrete_sequence=[SCHNEIDER_GREEN, SCHNEIDER_GRAY])
    else:
        fig = px.line(df, x=x, y=y, title=title, color_discrete_sequence=[SCHNEIDER_GREEN])
    fig.update_layout(
        template='plotly_white',
        font=dict(family=FONT_FAMILY, size=15, color=SCHNEIDER_GRAY),
        title_font=dict(size=20, color=SCHNEIDER_GREEN),
        xaxis_title=x_label,
        yaxis_title=y_label,
        legend_title_text='',
        margin=dict(l=20, r=20, t=60, b=40)
    )
    fig.update_traces(line=dict(width=3))
    return fig

# --- Bar Chart ---
def create_bar_chart(df, x, y, title, y_label, x_label):
    fig = px.bar(df, x=x, y=y, title=title, color_discrete_sequence=[SCHNEIDER_GREEN])
    fig.update_layout(
        template='plotly_white',
        font=dict(family=FONT_FAMILY, size=15, color=SCHNEIDER_GRAY),
        title_font=dict(size=20, color=SCHNEIDER_GREEN),
        xaxis_title=x_label,
        yaxis_title=y_label,
        margin=dict(l=20, r=20, t=60, b=40)
    )
    fig.update_traces(marker_line_color=SCHNEIDER_GRAY, marker_line_width=1.5)
    return fig

# --- Pie Chart ---
def create_pie_chart(df, names, values, title):
    fig = px.pie(df, names=names, values=values, title=title, color_discrete_sequence=[SCHNEIDER_GREEN, SCHNEIDER_GRAY])
    fig.update_traces(textinfo='percent+label', pull=[0.05, 0, 0], marker=dict(line=dict(color=SCHNEIDER_GRAY, width=2)))
    fig.update_layout(
        template='plotly_white',
        font=dict(family=FONT_FAMILY, size=15, color=SCHNEIDER_GRAY),
        title_font=dict(size=20, color=SCHNEIDER_GREEN),
        margin=dict(l=20, r=20, t=60, b=40)
    )
    return fig

# --- Scatter Plot ---
def create_scatter_plot(df, x, y, title, y_label, x_label, size=None, color=None):
    fig = px.scatter(
        df, x=x, y=y, size=size, color=color,
        title=title, color_discrete_sequence=[SCHNEIDER_GREEN]
    )
    fig.update_layout(
        template='plotly_white',
        font=dict(family=FONT_FAMILY, size=15, color=SCHNEIDER_GRAY),
        title_font=dict(size=20, color=SCHNEIDER_GREEN),
        xaxis_title=x_label,
        yaxis_title=y_label,
        margin=dict(l=20, r=20, t=60, b=40)
    )
    fig.update_traces(marker=dict(line=dict(width=1.5, color=SCHNEIDER_GRAY)))
    return fig
