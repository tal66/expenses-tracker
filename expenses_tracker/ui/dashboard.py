import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from expenses_tracker.config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

st.set_page_config(page_title="Expenses Dashboard", layout="wide")

config = Config()
INPUT_FILES_DIR = config.downloads_folder


def clean_amount(amount):
    """remove currency symbols and converting to float."""
    if isinstance(amount, str):
        return float(amount.replace('₪', '').replace(',', '').strip())
    return amount


def parse_date(date_str):
    if pd.isna(date_str):
        return None

    try:
        for fmt in ['%d-%m-%Y', '%Y-%m-%d %H:%M:%S']:
            try:
                return pd.to_datetime(date_str, format=fmt)
            except:
                continue
        return pd.to_datetime(date_str)
    except:
        return None


def load_transactions(file_path):
    """load and process transactions from markdown file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # split to regular and foreign transactions
    sections = content.split('## עסקאות חו"ל ומט"ח')

    def parse_markdown_table(section):
        lines = [line.strip() for line in section.split('\n') if line.strip()]
        header_idx = next(i for i, line in enumerate(lines) if 'תאריך עסקה' in line)
        headers = [col.strip() for col in lines[header_idx].split('|') if col.strip()]
        # print(f"headers: {headers}")

        data = []
        for line in lines[header_idx + 1:]:  # skip header
            if '|' not in line or 'סך הכל' in line:
                continue
            values = [val.strip() for val in line.split('|') if val.strip()]
            if len(values) == len(headers):
                data.append(dict(zip(headers, values)))

        return pd.DataFrame(data)

    # parse
    regular_df = parse_markdown_table(sections[0])
    foreign_df = parse_markdown_table(sections[1]) if len(sections) > 1 else pd.DataFrame()

    # combine and clean data
    df = pd.concat([regular_df, foreign_df], ignore_index=True)
    df = df[df['תאריך עסקה'] != 'NaN']
    df = df[df['סכום חיוב'] != 'NaN']

    if not df.empty:
        df['סכום חיוב'] = df['סכום חיוב'].apply(clean_amount)
        df['תאריך עסקה'] = df['תאריך עסקה'].apply(parse_date)
        df['תאריך חיוב'] = df['תאריך חיוב'].apply(parse_date)
        df['חודש חיוב'] = df['תאריך חיוב'].apply(lambda x: f"{x.month}/{x.year}" if isinstance(x, datetime) else None)

    return df


def categories_tab(filtered_df, tab1):
    with tab1:
        # Add description
        # st.markdown("""
        #     Analyze expenses across different categories.
        #     Toggle between charts.
        # """)

        category_data = (filtered_df.groupby('קטגוריה')['סכום חיוב']
                         .sum()
                         .reset_index()
                         .sort_values('סכום חיוב', ascending=True))

        # 2 columns for controls
        col1, col2 = st.columns([2, 3])
        with col1:
            # radio buttons
            st.markdown("""
                <style>
                    div.row-widget.stRadio > div[role="radiogroup"] > label input[type="radio"] {
                        accent-color: #3B7DDD;
                    }
                </style>
            """, unsafe_allow_html=True)

            chart_type = st.radio(
                "Select Visualization",
                ["Bar Chart", "Pie Chart"],
                horizontal=True,
                help="Choose how to visualize your category distribution"
            )

        with col2:
            # min amount filter
            min_amount = st.slider(
                "Minimum Amount (₪)",
                min_value=0,
                max_value=int(category_data['סכום חיוב'].max()),
                value=0,
                help="Filter categories by minimum expense amount"
            )

        # filter data based on minimum amount
        category_data = category_data[category_data['סכום חיוב'] >= min_amount]

        # visualizations
        if chart_type == "Bar Chart":
            fig = go.Figure(data=[
                go.Bar(
                    x=category_data['סכום חיוב'],
                    y=category_data['קטגוריה'],
                    orientation='h',
                    marker=dict(
                        color=['black', ],
                        opacity=0.8
                    ),
                    text=[f'{x:,.1f}' for x in category_data['סכום חיוב']],
                    textposition='auto',
                    textfont=dict(size=14 if len(category_data) < 10 else 12),
                )
            ])

            fig.update_layout(
                height=max(500, len(category_data) * 30),  # Dynamic height based on categories
                xaxis_title="Amount (₪)",
                yaxis_title="Category",
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False,
                hoverlabel=dict(bgcolor="white"),
                margin=dict(l=10, r=10, t=10, b=10)
            )

        else:  # pie chart
            fig = go.Figure(data=[
                go.Pie(
                    labels=category_data['קטגוריה'],
                    values=category_data['סכום חיוב'],
                    hole=0.3,
                    textinfo='label+percent',
                    hovertemplate="Category: %{label}<br>Amount: ₪%{value:,.2f}<extra></extra>",
                    marker=dict(
                        line=dict(color='white', width=2)
                    )
                )
            ])

            fig.update_layout(
                height=500,
                template='seaborn',
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="auto",
                    # y=-1.1,
                    xanchor="center",
                    x=0.5
                ),
                margin=dict(l=10, r=10, t=10, b=10),
            )

        # container for the chart with styling
        chart_container = st.container()
        with chart_container:
            st.plotly_chart(fig, use_container_width=True)

        # summary statistics below the chart
        total_expenses = category_data['סכום חיוב'].sum()
        num_categories = len(category_data)

        st.markdown("""---""")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Expenses", f"₪{total_expenses:,.2f}")
        with col2:
            st.metric("Number of Categories", num_categories)


def transactions_table_tab(filtered_df, tab3):
    with tab3:
        st.subheader("Transactions")

        # Display transactions table with formatting
        display_cols = ['תאריך עסקה', 'שם בית העסק', 'קטגוריה', 'סוג עסקה', 'סכום חיוב', 'תאריך חיוב',
                        '4 ספרות אחרונות של כרטיס האשראי']
        formatted_df = filtered_df[display_cols].copy()
        formatted_df['סכום חיוב'] = formatted_df['סכום חיוב'].apply(lambda x: f'₪{x:,.2f}')

        st.dataframe(
            formatted_df,
            column_config={
                'תאריך עסקה': st.column_config.DateColumn('Date', format="DD-MM-YYYY"),
                'שם בית העסק': st.column_config.TextColumn('Business'),
                'קטגוריה': st.column_config.TextColumn('Category'),
                'סוג עסקה': st.column_config.TextColumn('Type'),
                'סכום חיוב': st.column_config.TextColumn('Amount'),
                'תאריך חיוב': st.column_config.DateColumn('Charge Date', format="DD-MM-YYYY"),
                '4 ספרות אחרונות של כרטיס האשראי': st.column_config.TextColumn('Credit Card')
            },
            hide_index=True,
            use_container_width=True,
            height=700 if len(formatted_df) > 10 else None

        )


def monthly_bar_tab(df, tab2):
    with tab2:
        st.subheader("Monthly Expenses")

        # Monthly totals
        monthly_data = df.groupby('חודש חיוב')['סכום חיוב'].sum().reset_index()
        monthly_data = monthly_data.sort_values('חודש חיוב')

        monthly_data['Previous'] = monthly_data['סכום חיוב'].shift(1)
        monthly_data['Change'] = (monthly_data['סכום חיוב'] - monthly_data['Previous'])
        monthly_data['Change_Pct'] = (monthly_data['Change'] / monthly_data['Previous'] * 100).round(1)

        fig = go.Figure(data=[
            go.Bar(
                x=monthly_data['חודש חיוב'],
                y=monthly_data['סכום חיוב'],
                text=monthly_data.apply(
                    lambda row: f'₪{row["סכום חיוב"]:,.2f}<br>' +
                                (f'{row["Change_Pct"]:+.1f}%' if pd.notnull(row["Change_Pct"]) else ""),
                    axis=1
                ),
                textposition='auto',
                width=0.5,  # This sets the width of the bars (0-1)
                marker_color='#82ca9d'  # color for the bars
            )
        ])

        fig.update_layout(
            height=500,
            xaxis_title="Month",
            yaxis_title="Amount (₪)",
            uniformtext_minsize=12,
            uniformtext_mode='hide',
            bargap=0.7  # This adds space between bars (0-1)
        )

        st.plotly_chart(fig, use_container_width=True)


def main():
    st.title("📊 Expenses Dashboard")

    # find md files

    files = list(Path(INPUT_FILES_DIR).glob('*transactions*.md'))
    logger.info(f"found {len(files)} markdown files.")

    df = pd.DataFrame()
    for file in files:
        try:
            transactions = load_transactions(file)
            logger.info(f"file: {Path(file).name}, transactions: {transactions.shape[0]}")
            df = pd.concat([df, transactions], ignore_index=True)
        except Exception as e:
            st.error(f"Error loading data: {e}")

    if df.empty:
        st.error("No data found.")
        return

    logger.debug(f"df size: {df.shape}")
    logger.debug(sorted(df['חודש חיוב'].unique().tolist()))

    # print(df.head())
    # print(sorted(df['חודש חיוב'].unique().tolist()))

    # filters in sidebar
    st.sidebar.header("Filters")

    # Month filter
    available_months = ['All'] + sorted(df['חודש חיוב'].unique().tolist(), reverse=True)
    selected_month = st.sidebar.selectbox("Select Month", available_months)

    # Filter data based on selection
    if selected_month != 'All':
        filtered_df = df[df['חודש חיוב'] == selected_month]
    else:
        filtered_df = df

    # summary metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Expenses", f"₪{filtered_df['סכום חיוב'].sum():,.2f}")
    with col2:
        st.metric("Number of Transactions", len(filtered_df))

    # tabs
    tab1, tab2, tab3 = st.tabs(["Categories", "Monthly Trends", "Transactions"])
    categories_tab(filtered_df, tab1)
    monthly_bar_tab(df, tab2)
    transactions_table_tab(filtered_df, tab3)


if __name__ == "__main__":
    main()
