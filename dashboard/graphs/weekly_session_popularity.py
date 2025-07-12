import plotly.graph_objects as go
import pandas as pd


def weekly_session_popularity_chart(df_sessions, selected_ays, date_range):

    # Convert dates
    df_sessions = df_sessions[df_sessions['AY'].isin(selected_ays)]
    df_sessions['date'] = pd.to_datetime(df_sessions['date'])

    # Filter by selected date range
    start_date, end_date = date_range
    mask = (df_sessions['date'] >= start_date) & (df_sessions['date'] <= end_date)
    df_filtered = df_sessions[mask]

    # Group and pivot
    grouped = df_filtered.groupby(['date', 'room']).size().reset_index(name='registrants')
    pivot_df = grouped.pivot(index='date', columns='room', values='registrants').fillna(0)

    end_month_last_day = pd.to_datetime(end_date).replace(day=1) + pd.offsets.MonthEnd(0)

    label_colors = {
        "PR9": "#102542",
        "PR10": "#1f7a8c"
    }

    fig = go.Figure()

    for room in pivot_df.columns:
        fig.add_trace(go.Scatter(
            x=pivot_df.index,
            y=pivot_df[room],
            mode='lines+markers',
            name=str(room),
            line=dict(color=label_colors.get(room)),
            hovertemplate=(
                'Date: %{x|%Y-%m-%d}<br>'
                f'<span style="color:{label_colors.get(room)}">'
                'Registrants: %{y}</span>'
                '<extra></extra>'
            )
        ))

    fig.update_layout(
        title=f"Trends in Room Registrations",
        title_x=0,
        plot_bgcolor='white',
        dragmode=False,
        legend=dict(
            orientation='h',
            y=1.12,
            yanchor='top',
            x=1.0,
            xanchor='right',
            bgcolor='rgba(0,0,0,0)',
            borderwidth=0
        ),
        xaxis=dict(
            range=[start_date, end_month_last_day],
            dtick="M1",
            tickformat="%b",
            fixedrange=True,
            showgrid=True,
            gridcolor="lightgray",
            griddash="dash",
            ticklabelmode="period",
        ),
        yaxis=dict(
            dtick=2,
            fixedrange=True,
            showgrid=True,
            gridcolor="lightgray",
            griddash="dot",
            rangemode="tozero",
        )
    )
    return fig