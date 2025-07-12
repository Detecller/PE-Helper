import plotly.graph_objects as go


def create_piano_group_pie_chart(df_piano_groups):

    labels = ["Foundational", "Novice", "Intermediate", "Advanced"]
    values = [int(df_piano_groups.at[0, label]) for label in labels]

    label_colors = {
        "Advanced": "#05668d",
        "Intermediate": "#427aa1",
        "Novice": "#679436",
        "Foundational": "#a5be00"
    }

    # Build pie chart
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=[label_colors[label] for label in labels]),
        textinfo='value+percent',
        sort=False,
        hoverinfo='none'
    )])

    fig.update_layout(
        title="Piano-Playing Groups of Current Members",
        title_x=0,
        legend=dict(
            orientation="v",
            x=-0.1,
            y=0.5,
            xanchor="right",
            yanchor="middle"
        ),
        showlegend=True
    )

    return fig