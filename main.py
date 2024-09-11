import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from newsapi.newsapi_client import NewsApiClient
from datetime import datetime, timedelta
import os
import csv
import requests
import numpy as np

# Initialize NewsApiClient
NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
if not NEWS_API_KEY:
    st.sidebar.error("NEWS_API_KEY is not set in the environment variables. Please set it to use the news feature.")
    newsapi = None
else:
    newsapi = NewsApiClient(api_key=NEWS_API_KEY)
    st.sidebar.success("NewsAPI client initialized successfully.")

# Load historical news data
@st.cache_data
def load_historical_news():
    historical_news = {}
    with open('apple_historical_news.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            date = datetime.strptime(row[0], '%Y-%m-%d').date()
            historical_news[date] = {'title': row[1], 'description': row[2]}
    return historical_news

historical_news_data = load_historical_news()

# Function to fetch stock data
@st.cache_data
def get_stock_data(symbols):
    data = {}
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            stock_data = ticker.history(period="max")
            if not stock_data.empty:
                stock_data.index = stock_data.index.tz_localize(None)
                data[symbol] = stock_data
            else:
                st.warning(f"No data retrieved for {symbol}.")
        except Exception as e:
            st.warning(f"Error fetching data for {symbol}: {str(e)}")
    return data

# Function to calculate CAGR
def calculate_cagr(start_value, end_value, num_years):
    if num_years <= 0:
        return 0
    if start_value <= 0 or end_value <= 0:
        return 0
    return (end_value / start_value) ** (1 / num_years) - 1

# Function to calculate annualized return for periods less than a year
def calculate_annualized_return(start_value, end_value, num_days):
    if num_days <= 0 or start_value <= 0 or end_value <= 0:
        return 0
    return ((end_value / start_value) ** (365.25 / num_days)) - 1

# Function to format market cap
def format_market_cap(value):
    if value >= 1e12:
        return f"{value / 1e12:.2f}T"
    elif value >= 1e9:
        return f"{value / 1e9:.2f}B"
    elif value >= 1e6:
        return f"{value / 1e6:.2f}M"
    else:
        return f"{value:.2f}"

# Function to get start date based on selected timeframe
def get_start_date(timeframe, end_date):
    if timeframe == '1 Day':
        return end_date - pd.Timedelta(days=1)
    elif timeframe == '7 Days':
        return end_date - pd.Timedelta(days=7)
    elif timeframe == 'MTD':
        return end_date.replace(day=1)
    elif timeframe == '6M':
        return end_date - pd.Timedelta(days=180)
    elif timeframe == 'YTD':
        return end_date.replace(month=1, day=1)
    elif timeframe == '1 Year':
        return end_date - pd.Timedelta(days=365)
    elif timeframe == '5 Years':
        return end_date - pd.Timedelta(days=365*5)
    elif timeframe == '10 Years':
        return end_date - pd.Timedelta(days=365*10)
    elif timeframe == '15 Years':
        return end_date - pd.Timedelta(days=365*15)
    elif timeframe == '20 Years':
        return end_date - pd.Timedelta(days=365*20)
    elif timeframe == 'Maximum':
        return None
    elif timeframe == 'Custom':
        custom_date = st.date_input("Select start date", value=end_date.date() - timedelta(days=365))
        return pd.Timestamp(custom_date)

# New function to calculate Simple Moving Average (SMA)
def calculate_sma(data, window):
    return data['Close'].rolling(window=window).mean()

# New function to calculate Exponential Moving Average (EMA)
def calculate_ema(data, window):
    return data['Close'].ewm(span=window, adjust=False).mean()

# New function to calculate Relative Strength Index (RSI)
def calculate_rsi(data, window):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Main app
def main():
    st.title("Stock Price Chart with News Headlines and Technical Indicators")

    # Stock symbol selection
    default_symbol = st.text_input("Enter the primary stock symbol", value='AAPL')
    default_symbols = [default_symbol]
    
    # Add a note to inform users about changing the primary stock
    st.info("To change the primary stock, enter a new stock symbol in the 'Enter the primary stock symbol' field and press Enter.")

    additional_symbols = st.multiselect(
        "Select additional stocks to compare (max 3):",
        [symbol for symbol in ['GOOGL', 'MSFT', 'AMZN', 'FB', 'TSLA'] if symbol != default_symbol],
        max_selections=3
    )
    selected_symbols = default_symbols + additional_symbols

    # Fetch stock data
    data = get_stock_data(selected_symbols)

    # Timeframe selection
    timeframes = ['1 Day', '7 Days', 'MTD', '6M', 'YTD', '1 Year', '5 Years', '10 Years', '15 Years', '20 Years', 'Maximum', 'Custom']
    selected_timeframe = st.selectbox("Select timeframe", timeframes)

    # Technical indicator selection
    indicators = st.multiselect("Select technical indicators", ["SMA", "EMA", "RSI"], default=["SMA"])

    if data:
        fig = go.Figure()
        for symbol in selected_symbols:
            if symbol in data:
                stock_data = data[symbol]
                end_date = stock_data.index[-1]
                start_date = get_start_date(selected_timeframe, end_date)
                
                if start_date:
                    filtered_data = stock_data.loc[start_date:]
                else:
                    filtered_data = stock_data

                fig.add_trace(go.Scatter(x=filtered_data.index, y=filtered_data['Close'], mode='lines', name=f'{symbol} Close Price'))

                # Calculate and add technical indicators
                if "SMA" in indicators:
                    sma_20 = calculate_sma(filtered_data, 20)
                    fig.add_trace(go.Scatter(x=filtered_data.index, y=sma_20, mode='lines', name=f'{symbol} 20-day SMA', line=dict(dash='dash')))

                if "EMA" in indicators:
                    ema_50 = calculate_ema(filtered_data, 50)
                    fig.add_trace(go.Scatter(x=filtered_data.index, y=ema_50, mode='lines', name=f'{symbol} 50-day EMA', line=dict(dash='dot')))

                if "RSI" in indicators:
                    rsi_14 = calculate_rsi(filtered_data, 14)
                    fig.add_trace(go.Scatter(x=filtered_data.index, y=rsi_14, mode='lines', name=f'{symbol} 14-day RSI', yaxis="y2"))

                # Calculate performance percentage
                start_price = filtered_data['Close'].iloc[0]
                end_price = filtered_data['Close'].iloc[-1]
                performance = ((end_price - start_price) / start_price) * 100

                # Add annotation for performance percentage
                fig.add_annotation(
                    x=filtered_data.index[-1],
                    y=end_price,
                    text=f"{symbol}: {performance:.2f}%",
                    showarrow=True,
                    arrowhead=4,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="#636363",
                    font=dict(size=12, color="green" if performance >= 0 else "red"),
                    align="left",
                    xanchor="right",
                    yanchor="bottom"
                )

        fig.update_layout(
            title=f'Stock Price Comparison ({selected_timeframe}) with Technical Indicators',
            xaxis_title='Date',
            yaxis_title='Price (USD)',
            yaxis2=dict(title='RSI', overlaying='y', side='right', range=[0, 100]) if "RSI" in indicators else None,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Data Section
        st.subheader("Data Section")
        for symbol in selected_symbols:
            if symbol in data:
                stock_data = data[symbol]
                end_date = stock_data.index[-1]
                start_date = get_start_date(selected_timeframe, end_date)
                
                if start_date:
                    filtered_data = stock_data.loc[start_date:]
                else:
                    filtered_data = stock_data

                current_price = filtered_data['Close'].iloc[-1]
                start_price = filtered_data['Close'].iloc[0]
                
                # Calculate price performance
                performance = ((current_price - start_price) / start_price) * 100
                
                # Calculate CAGR or Annualized Return
                start_date = filtered_data.index[0]
                end_date = filtered_data.index[-1]
                num_years = (end_date - start_date).days / 365.25
                
                if num_years < 1:
                    num_days = (end_date - start_date).days
                    annualized_return = calculate_annualized_return(start_price, current_price, num_days)
                    cagr_label = f"Annualized Return ({selected_timeframe})"
                    cagr_value = f"{annualized_return:.2%}"
                else:
                    cagr = calculate_cagr(start_price, current_price, num_years)
                    cagr_label = f"CAGR ({selected_timeframe})"
                    cagr_value = f"{cagr:.2%}"
                
                # Get market cap
                ticker = yf.Ticker(symbol)
                market_cap = ticker.info.get('marketCap', 0)
                formatted_market_cap = format_market_cap(market_cap)

                st.markdown(f"**{symbol}**")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(label="Current Price", value=f"${current_price:.2f}")
                with col2:
                    st.metric(label="Price Performance", value=f"{performance:.2f}%")
                with col3:
                    st.metric(label=cagr_label, value=cagr_value)
                with col4:
                    st.metric(label="Market Cap", value=formatted_market_cap)
                st.markdown("---")

        # Date selection for news headlines
        selected_date = st.date_input("Select a date to view news headlines", 
                                      value=datetime.now().date(),
                                      min_value=datetime.now().date() - timedelta(days=30),
                                      max_value=datetime.now().date())

        # Fetch and display news headlines
        st.subheader(f"News Headlines for {selected_date}")
        for symbol in selected_symbols:
            headlines = get_news_headlines(symbol, selected_date)
            if headlines:
                st.markdown(f"**{symbol} News:**")
                for article in headlines:
                    st.markdown(f"[{article['title']}]({article['url']})")
                    st.write(f"Published on: {article['publishedAt']}")
                    st.write(article['description'])
                    st.write("---")
            else:
                st.info(f"No news headlines available for {symbol} on the selected date.")

def get_news_headlines(symbol, date):
    if not newsapi:
        st.warning("NewsAPI client is not initialized. Cannot fetch news headlines.")
        return []

    end_date = date + timedelta(days=1)
    try:
        headlines = newsapi.get_everything(q=symbol,
                                           from_param=date.strftime('%Y-%m-%d'),
                                           to=end_date.strftime('%Y-%m-%d'),
                                           language='en',
                                           sort_by='relevancy',
                                           page_size=5)
        return headlines['articles']
    except requests.exceptions.HTTPError as e:
        st.error(f"HTTP Error occurred while fetching news for {symbol}: {e}")
        return []
    except Exception as e:
        st.error(f"An error occurred while fetching news headlines for {symbol}: {str(e)}")
        return []

if __name__ == "__main__":
    main()
