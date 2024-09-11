import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from database import search_stocks
import random
import os
import requests
import time
import io

NYT_API_KEY = os.environ.get('NYT_API_KEY')

def calculate_returns(data, start_date, end_date):
    start_date = data.index[data.index >= pd.Timestamp(start_date)][0]
    end_date = data.index[data.index <= pd.Timestamp(end_date)][-1]
    start_price = data.loc[start_date, 'Close']
    end_price = data.loc[end_date, 'Close']
    total_return = (end_price - start_price) / start_price
    years = (end_date - start_date).days / 365.25
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    return total_return, cagr

def generate_random_color():
    return f"#{random.randint(0, 0xFFFFFF):06x}"

def export_to_csv(df):
    csv = df.to_csv(index=True)
    return csv

def export_news_to_csv(news_data):
    df = pd.DataFrame(news_data, columns=['Headline', 'Published Date', 'Abstract', 'URL', 'Relevance'])
    csv = df.to_csv(index=False)
    return csv

def get_company_name(symbol):
    try:
        ticker = yf.Ticker(symbol)
        return ticker.info.get('longName', symbol)
    except:
        return symbol

def main():
    st.set_page_config(layout="wide")
    st.title("Interactive Stock Price Chart with News Headlines")

    # Debug toggle and container
    show_debug = st.sidebar.checkbox("Show Debug Information", value=False)
    debug_container = st.empty()

    # Sidebar
    st.sidebar.header("Stock Selection")
    default_symbol = st.sidebar.text_input("Enter primary stock symbol", value="AAPL")
    additional_symbols = st.sidebar.text_input("Enter additional stock symbols (comma-separated)", value="").split(',')
    selected_symbols = [default_symbol] + [symbol.strip() for symbol in additional_symbols if symbol.strip()]

    # Date range selection
    st.sidebar.header("Date Range")
    date_ranges = ['1D', '5D', 'MTD', '6M', 'YTD', '1 Year', '5 Years', '10 Years', '15 Years', '20 Years', '30 Years', 'Maximum', 'Custom']
    selected_range = st.sidebar.selectbox("Select Date Range", date_ranges, index=date_ranges.index('YTD'))

    def get_date_range(selected_range):
        end_date = datetime.now().date()
        if selected_range == '1D':
            start_date = end_date - timedelta(days=1)
        elif selected_range == '5D':
            start_date = end_date - timedelta(days=5)
        elif selected_range == 'MTD':
            start_date = end_date.replace(day=1)
        elif selected_range == '6M':
            start_date = end_date - timedelta(days=180)
        elif selected_range == 'YTD':
            start_date = end_date.replace(month=1, day=1)
        elif selected_range == '1 Year':
            start_date = end_date - timedelta(days=365)
        elif selected_range == '5 Years':
            start_date = end_date - timedelta(days=365*5)
        elif selected_range == '10 Years':
            start_date = end_date - timedelta(days=365*10)
        elif selected_range == '15 Years':
            start_date = end_date - timedelta(days=365*15)
        elif selected_range == '20 Years':
            start_date = end_date - timedelta(days=365*20)
        elif selected_range == '30 Years':
            start_date = end_date - timedelta(days=365*30)
        elif selected_range == 'Maximum':
            start_date = None
        else:  # Custom
            start_date = st.sidebar.date_input("Start date", end_date - timedelta(days=365))
            end_date = st.sidebar.date_input("End date", end_date)
        return start_date, end_date

    start_date, end_date = get_date_range(selected_range)

    # Fetch stock data
    data = {}
    with st.spinner('Fetching stock data...'):
        for symbol in selected_symbols:
            try:
                if show_debug:
                    with debug_container.container():
                        st.text(f"Fetching data for {symbol}...")
                start_time = time.time()
                stock_data = yf.download(symbol, start=start_date, end=end_date)
                end_time = time.time()
                if show_debug:
                    with debug_container.container():
                        st.text(f"Fetched data for {symbol} in {end_time - start_time:.2f} seconds")
                if not stock_data.empty:
                    data[symbol] = stock_data
                else:
                    st.warning(f"No data available for {symbol} in the selected date range.")
            except Exception as e:
                st.error(f"Error fetching data for {symbol}: {str(e)}")

    # Remove symbols with no data
    selected_symbols = [symbol for symbol in selected_symbols if symbol in data]

    if not data:
        st.error("Unable to fetch data for any of the selected symbols. Please try again later or choose different symbols.")
        return

    company_name = get_company_name(default_symbol)

    # Create and display the chart
    if data:
        with st.spinner('Creating chart...'):
            start_time = time.time()
            fig = go.Figure()
            base_symbol = selected_symbols[0]
            base_data = data[base_symbol]
            base_start_price = base_data['Close'].iloc[0]

            for symbol in selected_symbols:
                stock_data = data[symbol]
                start_price = stock_data['Close'].iloc[0]

                if len(selected_symbols) > 1:
                    # Calculate percentage change relative to the starting point
                    y_values = ((stock_data['Close'] - start_price) / start_price) * 100
                    y_axis_title = "Percentage Change (%)"
                else:
                    y_values = stock_data['Close']
                    y_axis_title = "Price (USD)"

                fig.add_trace(go.Scatter(x=stock_data.index, y=y_values, mode='lines', name=f'{symbol}'))

                # Calculate CAGR for the timeframe
                start_price = stock_data['Close'].iloc[0]
                end_price = stock_data['Close'].iloc[-1]
                years = (stock_data.index[-1] - stock_data.index[0]).days / 365.25
                cagr = ((end_price / start_price) ** (1 / years) - 1) * 100 if years > 0 else 0
                
                # Add annotation for CAGR at the end of the line
                fig.add_annotation(
                    x=stock_data.index[-1],
                    y=y_values.iloc[-1],
                    text=f"CAGR: {cagr:.2f}%",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="#FFFFFF",
                    font=dict(size=14, color="#FFFFFF", family="Arial Black"),
                    align="right",
                    xanchor="left",
                    yanchor="middle",
                    bgcolor="rgba(0,0,0,0.8)",
                    bordercolor="#FFFFFF",
                    borderwidth=2,
                    borderpad=4,
                    opacity=0.8
                )

            # Update the layout to use the new y_axis_title
            fig.update_layout(title='Stock Price Comparison',
                              xaxis_title='Date',
                              yaxis_title=y_axis_title)

            end_time = time.time()
            if show_debug:
                with debug_container.container():
                    st.text(f"Chart created in {end_time - start_time:.2f} seconds")
            st.plotly_chart(fig, use_container_width=True)

        # Export chart data
        st.subheader("Export Chart Data")
        for symbol in selected_symbols:
            csv = export_to_csv(data[symbol])
            st.download_button(
                label=f"Download {symbol} Data",
                data=csv,
                file_name=f"{symbol}_stock_data.csv",
                mime="text/csv",
            )

    # Calculate and display returns
    st.subheader("Returns and Key Metrics")
    for symbol in selected_symbols:
        try:
            stock_data = data[symbol]
            current_price = stock_data['Close'].iloc[-1]
            total_return, cagr = calculate_returns(stock_data, start_date, end_date)
            
            # Get market cap
            ticker = yf.Ticker(symbol)
            market_cap = ticker.info.get('marketCap', 0)
            if market_cap >= 1e12:
                formatted_market_cap = f"{market_cap/1e12:.2f}T"
            elif market_cap >= 1e9:
                formatted_market_cap = f"{market_cap/1e9:.2f}B"
            elif market_cap >= 1e6:
                formatted_market_cap = f"{market_cap/1e6:.2f}M"
            else:
                formatted_market_cap = f"{market_cap:.2f}"

            st.markdown(f"**{symbol}**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Current Price", f"${current_price:.2f}")
            with col2:
                st.metric("Price Performance", f"{total_return:.2%}")
            with col3:
                st.metric(f"CAGR ({selected_range})", f"{cagr:.2%}")
            with col4:
                st.metric("Market Cap", formatted_market_cap)
        except Exception as e:
            st.write(f"Error calculating metrics for {symbol}: {str(e)}")

    # Historical News Headlines
    st.subheader("Historical News Headlines")
    historical_news_date = st.date_input("Select a date for historical news", 
                                         min_value=datetime(1980, 1, 1).date(), 
                                         max_value=datetime.now().date(), 
                                         value=start_date if isinstance(start_date, datetime) else datetime.now().date())

    try:
        with st.spinner('Fetching news headlines...'):
            url = f"https://api.nytimes.com/svc/search/v2/articlesearch.json"
            params = {
                "api-key": NYT_API_KEY,
                "q": company_name,
                "begin_date": historical_news_date.strftime('%Y%m%d'),
                "end_date": (historical_news_date + timedelta(days=1)).strftime('%Y%m%d'),
                "sort": "relevance",
                "fq": f"headline:({company_name}) OR body:({company_name})"
            }
            response = requests.get(url, params=params)
            if response.status_code != 200:
                st.error(f"Error fetching news: {response.status_code} - {response.text}")
                return
            data = response.json()
            
            if show_debug:
                with debug_container.container():
                    st.text(f"Debug - API Response: {data}")

            if 'response' in data and 'docs' in data['response']:
                articles = data['response']['docs']
                if articles:
                    news_data = []
                    for article in articles[:5]:  # Display up to 5 articles
                        headline = article['headline']['main'] if 'headline' in article and 'main' in article['headline'] else 'No headline available'
                        st.write(f"**{headline}**")
                        st.write(f"Relevance: {article.get('_score', 'N/A')}")
                        st.write(f"Source: The New York Times")
                        st.write(f"Published at: {article.get('pub_date', 'Date not available')}")
                        st.write(article.get('abstract', 'No abstract available'))
                        st.write(f"[Read more]({article.get('web_url', '#')})")
                        st.write("---")
                        news_data.append([headline, article.get('pub_date', 'Date not available'), article.get('abstract', 'No abstract available'), article.get('web_url', '#'), article.get('_score', 'N/A')])
                    
                    # Export news data
                    st.subheader("Export News Data")
                    csv = export_news_to_csv(news_data)
                    st.download_button(
                        label="Download News Data",
                        data=csv,
                        file_name=f"news_data_{historical_news_date}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info(f"No news found for {company_name} on {historical_news_date}. Try adjusting the date or check if the stock symbol is correct.")
            else:
                st.error(f"Unexpected API response format: {data}")
    except Exception as e:
        st.error(f"Error fetching historical news: {str(e)}")

if __name__ == "__main__":
    main()
