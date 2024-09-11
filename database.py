import yfinance as yf

def search_stocks(query):
    try:
        ticker = yf.Ticker(query)
        info = ticker.info
        if info:
            return [{
                'symbol': info['symbol'],
                'name': info.get('longName', 'N/A'),
                'exchange': info.get('exchange', 'N/A')
            }]
        else:
            return []
    except Exception as e:
        print(f"Error searching for {query}: {str(e)}")
        return []
