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

def main():
    st.set_page_config(layout="wide")
    st.title("Interactive Stock Price Chart with News Headlines")

    # Sidebar
    st.sidebar.header("Stock Selection")
    default_symbol = st.sidebar.text_input("Enter primary stock symbol", value="AAPL")
    additional_symbols = st.sidebar.text_input("Enter additional stock symbols (comma-separated)", value="GOOGL,MSFT,AMZN").split(',')
    selected_symbols = [default_symbol] + [symbol.strip() for symbol in additional_symbols if symbol.strip()]

    # Date range selection
    st.sidebar.header("Date Range")
    date_ranges = ['1D', '5D', 'MTD', '6M', 'YTD', '1 Year', '5 Years', '10 Years', '15 Years', '20 Years', '30 Years', 'Maximum', 'Custom']
    selected_range = st.sidebar.selectbox("Select Date Range", date_ranges)

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
    for symbol in selected_symbols:
        try:
            stock_data = yf.download(symbol, start=start_date, end=end_date)
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

    # Technical indicators
    st.sidebar.header("Technical Indicators")
    indicators = st.sidebar.multiselect("Select technical indicators:", ["SMA", "EMA", "RSI"])

    # Chart customization options
    st.sidebar.header("Chart Customization")
    color_options = {symbol: generate_random_color() for symbol in selected_symbols}
    chart_bg_color = st.sidebar.color_picker("Select chart background color", "#FFFFFF")
    grid_color = st.sidebar.color_picker("Select grid color", "#E0E0E0")
    font_size = st.sidebar.slider("Select font size for chart title and axes labels", 10, 24, 16)

    if data:
        fig = go.Figure()
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
            
            trace = go.Scatter(
                x=stock_data.index,
                y=y_values,
                mode='lines',
                name=f'{symbol}',
                line=dict(color=color_options[symbol])
            )
            fig.add_trace(trace)

            # Calculate CAGR for the timeframe
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
                arrowcolor=color_options[symbol],
                font=dict(size=10, color=color_options[symbol]),
                align="right",
                xanchor="left",
                yanchor="middle"
            )

            # Add technical indicators
            if "SMA" in indicators:
                sma = stock_data['Close'].rolling(window=20).mean()
                fig.add_trace(go.Scatter(x=stock_data.index, y=sma, mode='lines', name=f'{symbol} SMA (20)', line=dict(color=color_options[symbol], dash='dash')))

            if "EMA" in indicators:
                ema = stock_data['Close'].ewm(span=20, adjust=False).mean()
                fig.add_trace(go.Scatter(x=stock_data.index, y=ema, mode='lines', name=f'{symbol} EMA (20)', line=dict(color=color_options[symbol], dash='dot')))

            if "RSI" in indicators:
                delta = stock_data['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                fig.add_trace(go.Scatter(x=stock_data.index, y=rsi, mode='lines', name=f'{symbol} RSI', yaxis="y2", line=dict(color=color_options[symbol], width=1)))

        # Update layout with custom colors and new customization options
        fig.update_layout(
            title=dict(
                text=f'Stock Price Comparison with Technical Indicators',
                font=dict(size=font_size + 4, color='black')
            ),
            xaxis_title=dict(text='Date', font=dict(size=font_size, color='black')),
            yaxis_title=dict(text=y_axis_title, font=dict(size=font_size, color='black')),
            yaxis2=dict(title='RSI', overlaying='y', side='right', range=[0, 100], titlefont=dict(color='black', size=font_size)) if "RSI" in indicators else None,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=font_size - 2, color='black')),
            plot_bgcolor=chart_bg_color,
            paper_bgcolor='#f0f0f0',
            font=dict(color='black')
        )

        # Update axes
        fig.update_xaxes(showgrid=True, gridcolor=grid_color, tickfont=dict(size=font_size - 2, color='black'))
        fig.update_yaxes(showgrid=True, gridcolor=grid_color, tickfont=dict(size=font_size - 2, color='black'))

        st.plotly_chart(fig, use_container_width=True)

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
            end_date = historical_news_date + timedelta(days=1)
            url = f"https://api.nytimes.com/svc/search/v2/articlesearch.json"
            params = {
                "q": default_symbol,
                "begin_date": historical_news_date.strftime('%Y%m%d'),
                "end_date": end_date.strftime('%Y%m%d'),
                "api-key": NYT_API_KEY,
                "sort": "relevance"
            }
            response = requests.get(url, params=params)
            if response.status_code != 200:
                st.error(f"Error fetching news: {response.status_code} - {response.text}")
                return
            data = response.json()
            
            print(f"Debug - API Response: {data}")

            if 'response' in data and 'docs' in data['response']:
                articles = data['response']['docs']
                if articles:
                    for article in articles[:5]:  # Display up to 5 articles
                        headline = article['headline']['main'] if 'headline' in article and 'main' in article['headline'] else 'No headline available'
                        st.write(f"**{headline}**")
                        st.write(f"Source: The New York Times")
                        st.write(f"Published at: {article.get('pub_date', 'Date not available')}")
                        st.write(article.get('abstract', 'No abstract available'))
                        st.write(f"[Read more]({article.get('web_url', '#')})")
                        st.write("---")
                else:
                    st.info(f"No news found for {default_symbol} on {historical_news_date}")
            else:
                st.error(f"Unexpected API response format: {data}")
        except Exception as e:
            st.error(f"Error fetching historical news: {str(e)}")
    else:
        st.warning("No data available to display the chart.")

if __name__ == "__main__":
    main()
