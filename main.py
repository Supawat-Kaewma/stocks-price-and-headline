import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from newsapi.newsapi_client import NewsApiClient
from datetime import datetime, timedelta
import os
import pytz
import csv

# Set page configuration
st.set_page_config(page_title="AAPL Stock Price Chart with News Headlines", layout="wide")

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

# Function to fetch AAPL stock data
@st.cache_data
def get_stock_data():
    try:
        ticker = yf.Ticker("AAPL")
        data = ticker.history(period="max")
        if data.empty:
            st.error("No data retrieved from yfinance. Please check your internet connection or try again later.")
            return None
        # Convert index to UTC
        data.index = data.index.tz_convert('UTC')
        return data
    except Exception as e:
        st.error(f"An error occurred while fetching stock data: {str(e)}")
        return None

# Function to fetch news headlines
@st.cache_data
def get_news_headlines(date):
    if date < datetime(2014, 1, 1).date():
        if date in historical_news_data:
            article = historical_news_data[date]
            return [{
                'title': article['title'],
                'description': article['description'],
                'publishedAt': date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'url': '#',  # No URL available for historical data
                'source': {'name': 'Historical Data (Pre-2014)'}
            }]
        else:
            st.info(f"No specific news available for {date}. Showing closest available news.")
            closest_date = min(historical_news_data.keys(), key=lambda d: abs(d - date))
            article = historical_news_data[closest_date]
            return [{
                'title': article['title'],
                'description': article['description'],
                'publishedAt': closest_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'url': '#',  # No URL available for historical data
                'source': {'name': f'Historical Data (Pre-2014, Closest: {closest_date})'}
            }]
    else:
        if not newsapi:
            st.warning("NewsAPI client is not initialized. Cannot fetch news headlines.")
            return []

        end_date = date + timedelta(days=1)
        try:
            headlines = newsapi.get_everything(q='Apple',
                                               from_param=date.strftime('%Y-%m-%d'),
                                               to=end_date.strftime('%Y-%m-%d'),
                                               language='en',
                                               sort_by='relevancy',
                                               page_size=5)
            st.success(f"Successfully fetched {len(headlines['articles'])} news headlines.")
            return [{
                'title': article['title'],
                'description': article['description'],
                'publishedAt': article['publishedAt'],
                'url': article['url'],
                'source': article['source']
            } for article in headlines['articles']]
        except Exception as e:
            st.error(f"An error occurred while fetching news headlines: {str(e)}")
            return []

# Main app
def main():
    st.title("AAPL Stock Price Chart with News Headlines")

    # Fetch stock data
    data = get_stock_data()

    if data is not None and not data.empty:
        # Show date range of the fetched data
        st.write(f"Data available from {min(data.index).date()} to {max(data.index).date()}")

        # Date range selector
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start date", max(data.index).date() - timedelta(days=365*40))
        with col2:
            end_date = st.date_input("End date", max(data.index).date())

        # Add error handling for date range selection
        if start_date > end_date:
            st.error("Start date cannot be after end date. Please adjust your selection.")
            return

        # Convert date inputs to UTC datetime
        start_datetime = pd.Timestamp(start_date).tz_localize('UTC')
        end_datetime = pd.Timestamp(end_date).tz_localize('UTC') + timedelta(days=1) - timedelta(seconds=1)

        # Filter data based on selected date range
        mask = (data.index >= start_datetime) & (data.index <= end_datetime)
        filtered_data = data.loc[mask]

        # Create interactive chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=filtered_data.index, y=filtered_data['Close'], mode='lines', name='Close Price'))
        fig.update_layout(title='AAPL Stock Price', xaxis_title='Date', yaxis_title='Price (USD)')

        # Display the chart
        st.plotly_chart(fig, use_container_width=True)

        # Stock data preview
        st.subheader("Stock Data Preview")
        st.dataframe(filtered_data.head())

        # Date selection for news headlines
        selected_date = st.date_input("Select a date to view news headlines", 
                                      value=max(filtered_data.index).date(),
                                      min_value=min(filtered_data.index).date(),
                                      max_value=max(filtered_data.index).date())

        # Fetch and display news headlines
        headlines = get_news_headlines(selected_date)
        st.subheader(f"News Headlines for {selected_date}")
        if headlines:
            for article in headlines:
                title = article['title']
                url = article.get('url', '#')
                published_at = article.get('publishedAt', 'N/A')
                if published_at != 'N/A':
                    published_at = datetime.strptime(published_at, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d %H:%M:%S')
                
                if url == '#':
                    st.markdown(f"**{title}**")
                    st.info("This is historical data (pre-2014). Original news link is not available.")
                else:
                    st.markdown(f"[**{title}**]({url})")
                
                st.write(f"Published on: {published_at}")
                st.write(article.get('description', 'No description available'))
                if 'source' in article and 'name' in article['source']:
                    st.write(f"Source: {article['source']['name']}")
                st.write("---")
        else:
            st.info("No news headlines available for the selected date.")
    else:
        st.error("Unable to display chart due to missing data.")

    # Debug information
    st.sidebar.subheader("Debug Information")
    st.sidebar.write(f"NEWS_API_KEY set: {'Yes' if NEWS_API_KEY else 'No'}")
    st.sidebar.write(f"NewsAPI client initialized: {'Yes' if newsapi else 'No'}")
    st.sidebar.write(f"yfinance version: {yf.__version__}")
    st.sidebar.write(f"pandas version: {pd.__version__}")
    st.sidebar.write(f"pytz version: {pytz.__version__}")

if __name__ == "__main__":
    main()
