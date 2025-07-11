import streamlit as st
import pandas as pd
from datetime import datetime
from utils.variables import SGT
from graphs.weekly_session_popularity import weekly_session_popularity_chart
from graphs.piano_groups import create_piano_group_pie_chart


st.markdown(
    """
    <style>
        .stMainBlockContainer {
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 1200px;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# Load data
df_sessions = pd.read_csv('../data/all_bookings.csv')
df_piano_groups = pd.read_csv('../data/piano_groups.csv')

# Convert dates early for filtering
df_sessions['date'] = pd.to_datetime(df_sessions['date'])

# Get list of AYs from data
available_ays = sorted(df_sessions['AY'].unique(), reverse=True)

# Sidebar filter: AY selector
selected_ays = st.sidebar.multiselect(
    "Select Academic Year(s)",
    options=available_ays,
    default=[available_ays[0]]
)

# Sidebar filter — Date range
min_date = df_sessions['date'].min().date()
max_date = df_sessions['date'].max().date()

start_date, end_date = st.sidebar.slider(
    "Select Date Range",
    value=(min_date, max_date),
    format="YYYY-MM-DD",
    min_value=min_date,
    max_value=max_date
)

start_date = datetime.combine(start_date, datetime.min.time())
end_date = datetime.combine(end_date, datetime.max.time())


col1, col2 = st.columns([1, 1])

with col1:
    fig = create_piano_group_pie_chart(df_piano_groups)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with col2:
    fig = weekly_session_popularity_chart(df_sessions, selected_ays, (start_date, end_date))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})