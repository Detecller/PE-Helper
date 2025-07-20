import streamlit as st
import pandas as pd
from datetime import datetime
from utils.variables import SGT
from graphs.weekly_session_popularity import weekly_session_popularity_chart
from graphs.piano_groups import create_piano_group_pie_chart


st.set_page_config(
    page_title="PE Dashboard",
    page_icon="images/piano_ensemble_logo.png"
)


st.markdown(
    """
    <style>
        .stMainBlockContainer {
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 1200px;
        }
        .st-emotion-cache-1dp5vir {
            background-image: none;
        }
        #MainMenu {
            display: none;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Load data
df_sessions = pd.read_csv('../data/all_bookings.csv')
df_piano_groups = pd.read_csv('../data/piano_groups.csv')
df_summary_numbers = pd.read_csv('../data/summary_numbers.csv')

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

if selected_ays:
    filtered = df_summary_numbers[df_summary_numbers['AY'].isin(selected_ays)]
    members = filtered['members_num'].sum()
    alumni = filtered['alumni_num'].sum()
    new_members = df_summary_numbers.loc[df_summary_numbers['AY'].idxmax()]['new_members_num']
else:
    members = alumni = new_members = 0

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


# UI
st.header("Summary")

card1, card2, card3 = st.columns(3)
with card1:
    st.markdown(f"""
    <div style="
        background-color: #fbfbfb;
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
        margin-bottom: 1.5rem;
    ">
        <div style="font-size: 0.95rem; color: #666; font-weight: 600;">Total Members</div>
        <div style="font-size: 2rem; font-weight: bold; margin-top: 0.2rem; color: #0072B1;">
            {members:,}
        </div>
    </div>
    """, unsafe_allow_html=True)

with card2:
    st.markdown(f"""
    <div style="
        background-color: #fbfbfb;
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
        margin-bottom: 1.5rem;
    ">
        <div style="font-size: 0.95rem; color: #666; font-weight: 600;">Total Alumni</div>
        <div style="font-size: 2rem; font-weight: bold; margin-top: 0.2rem; color: #0072B1;">
            {alumni:,}
        </div>
    </div>
    """, unsafe_allow_html=True)

with card3:
    st.markdown(f"""
    <div style="
        background-color: #fbfbfb;
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
        margin-bottom: 1.5rem;
    ">
        <div style="font-size: 0.95rem; color: #666; font-weight: 600;">Newcomers (this AY)</div>
        <div style="font-size: 2rem; font-weight: bold; margin-top: 0.2rem; color: #0072B1;">
            {new_members:,}
        </div>
    </div>
    """, unsafe_allow_html=True)


col1, spacer, col2 = st.columns([1, 0.005, 1])

with col1:
    st.header("Piano-Playing Groups")
    tab1, tab2 = st.tabs(["Graph", "Description"])
    with tab1:
        fig = create_piano_group_pie_chart(df_piano_groups)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with tab2:
        st.markdown("""
        <div style='text-align: justify'>
        <p>The pie chart shows the proportion of members across different piano-playing groups.</p>

        <p>Generally, members fall under the following subgroups:</p>

        <p style='color: #a5be00'><strong>Foundational</strong></p>
        <ul>
        <li>No experience in piano playing</li>
        </ul>

        <p style='color: #679436'><strong>Novice</strong></p>
        <ul>
        <li>Some music background or limited experience in piano playing</li>
        </ul>

        <p style='color: #427aa1'><strong>Intermediate</strong></p>
        <ul>
        <li>Has experience but cannot yet master complex pieces</li>
        </ul>

        <p style='color: #05668d'><strong>Advanced</strong></p>
        <ul>
        <li>Able to master complex pieces</li>
        </ul>

        <p>Having this information helps the EXCO determine the general needs of members and thus, better structure weekly sessions based on their goals and plan events targeted towards the varying sub-groups.</p>
        </div>
        """, unsafe_allow_html=True)


with col2:
    st.header("Weekly Sessions")
    tab1, tab2 = st.tabs(["Graph", "Description"])
    with tab1:
        fig = weekly_session_popularity_chart(df_sessions, selected_ays, (start_date, end_date))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with tab2:
        st.markdown("""
        <div style='text-align: justify'>
        <p>The line chart displays the number of registrations for each room over time.</p>
                    
        <p>This information helps the EXCO determine whether certain rooms are consistently more popular,
            identify periods of peak demand, and make informed decisions about room scheduling
            (e.g. increasing/decreasing number of time slots based on demand).
        </p>

        <p>
            As PR9 is equipped with two baby grand pianos (a Yamaha and a K. Kawai),
            while PR10 houses three to four Yamaha P-125 digital pianos and one upright Yamaha piano,
            the EXCO commonly regulates room usage based on members' piano-playing groups as follows:
        </p>
        
        <p style='color: #102542'><strong>PR9</strong></p>
        <ul>
        <li style='color: #427aa1'>Intermediate</li>
        <li style='color: #05668d'>Advanced</li>
        </ul>
                    
        <p style='color: #1f7a8c'><strong>PR10</strong></p>
        <ul>
        <li style='color: #a5be00'>Foundational</li>
        <li style='color: #679436'>Novice</li>
        </ul>
                    
        <p>
            <strong>Rationale:</strong>
            <br>
            As piano pieces become more advanced and require greater sensitivity to touch,
            access to weighted keys—such as those found on grand and upright pianos—offers a more realistic and effective environment for developing proper technique.
            Conversely, members with limited experience may benefit more from unweighted or semi-weighted digital pianos,
            which are easier to play and better suited for building basic skills and finger strength.
        </p>

        </div>
        """, unsafe_allow_html=True)