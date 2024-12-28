from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
from yahoo_fin import stock_info as si
import threading
import json
import os
import logging
import time
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)  # Enable CORS to allow requests from the frontend

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to cache stock data
CACHE_FILE = 'stock_data.json'

# Global stock data list
stock_data = []

def fetch_nyse_tickers():
    """
    Scrape NYSE tickers from Wikipedia.
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"  # Example source
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'constituents'})
        nyse_tickers = []
        if table:
            rows = table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cols = row.find_all('td')
                symbol = cols[0].text.strip().replace('.', '-')
                name = cols[1].text.strip()
                nyse_tickers.append({"symbol": symbol, "name": name})
            logger.info(f"Scraped {len(nyse_tickers)} NYSE tickers from Wikipedia.")
        else:
            logger.warning("Could not find the NYSE tickers table on Wikipedia.")
        return nyse_tickers
    except Exception as e:
        logger.error(f"Error scraping NYSE tickers: {e}")
        return []

def load_stock_data():
    """
    Load stock symbols and company names dynamically from Yahoo Finance.
    Caches the data in a local JSON file to avoid redundant API calls.
    """
    global stock_data

    if os.path.exists(CACHE_FILE):
        logger.info(f"Loading stock data from cache: {CACHE_FILE}")
        with open(CACHE_FILE, 'r') as f:
            stock_data = json.load(f)
        logger.info(f"Loaded {len(stock_data)} stocks from cache.")
    else:
        logger.info("Cache file not found. Fetching stock data from Yahoo Finance...")
        stock_data = fetch_and_cache_stock_data()
        logger.info(f"Fetched and cached {len(stock_data)} stocks.")

def fetch_and_cache_stock_data():
    """
    Fetch stock symbols from multiple exchanges and retrieve their company names.
    Caches the data into a JSON file.
    """
    exchanges = {
        'NASDAQ': si.tickers_nasdaq(),
        'AMEX': si.tickers_amex(),
        'SP500': si.tickers_sp500(),
        'DOW': si.tickers_dow(),
        # 'NYSE': si.tickers_nyse(),  # Removed due to AttributeError
        # Add more exchanges if needed
    }

    # Use a set to avoid duplicate symbols
    all_symbols = set()
    for exchange, symbols in exchanges.items():
        logger.info(f"Fetching symbols from {exchange}...")
        all_symbols.update(symbols)
        time.sleep(1)  # Sleep to avoid hitting rate limits

    # Fetch NYSE tickers via scraping
    nyse_tickers = fetch_nyse_tickers()
    for stock in nyse_tickers:
        all_symbols.add(stock['symbol'])

    logger.info(f"Total unique symbols fetched (including NYSE): {len(all_symbols)}")

    stock_list = []
    lock = threading.Lock()

    def fetch_name(symbol):
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            name = info.get('shortName') or info.get('longName') or 'N/A'
            with lock:
                stock_list.append({
                    'symbol': symbol.upper(),
                    'name': name,
                    'exchange': 'Multiple'  # Simplified for demonstration
                })
            logger.info(f"Fetched name for {symbol}: {name}")
        except Exception as e:
            logger.error(f"Error fetching name for {symbol}: {e}")

    threads = []
    for symbol in all_symbols:
        thread = threading.Thread(target=fetch_name, args=(symbol,))
        threads.append(thread)
        thread.start()
        # To prevent too many threads, limit active threads
        if len(threads) >= 50:
            for t in threads:
                t.join()
            threads = []

    # Join any remaining threads
    for t in threads:
        t.join()

    logger.info(f"Total stocks fetched with names: {len(stock_list)}")

    # Save to cache
    with open(CACHE_FILE, 'w') as f:
        json.dump(stock_list, f, indent=4)
    logger.info(f"Stock data cached to {CACHE_FILE}")

    return stock_list

# Load stock data on startup
load_stock_data()

# Endpoint to fetch stock suggestions
@app.route("/search", methods=["GET"])
def search_stocks():
    query = request.args.get("query", "").upper()
    if not query:
        return jsonify([])  # Return empty list if no query

    # Filter suggestions based on query
    suggestions = [
        stock for stock in stock_data
        if query in stock["symbol"].upper() or query in stock["name"].upper()
    ][:5]  # Limit to 5 results

    return jsonify(suggestions)

# Endpoint to fetch stock symbols based on exchange
@app.route("/stock/symbol", methods=["GET"])
def get_stock_symbols():
    exchange = request.args.get("exchange", "").upper()
    if not exchange:
        logger.error("No exchange provided.")
        return jsonify({"error": "No exchange provided."}), 400

    # Filter stock symbols based on exchange
    if exchange == 'ALL':
        symbols = [
            {"symbol": stock["symbol"], "name": stock["name"]}
            for stock in stock_data
        ]
    else:
        symbols = [
            {"symbol": stock["symbol"], "name": stock["name"]}
            for stock in stock_data
            if exchange in stock["exchange"].upper() or stock["exchange"].upper() == 'MULTIPLE'
        ]

    if not symbols:
        logger.warning(f"No symbols found for exchange: {exchange}")
        return jsonify({"error": f"No symbols found for exchange: {exchange}"}), 404

    return jsonify(symbols)

# Endpoint to fetch the latest stock price
@app.route("/quote", methods=["GET"])
def get_stock_quote():
    symbol = request.args.get("symbol", "").upper()
    if not symbol:
        logger.error("No stock symbol provided.")
        return jsonify({"error": "No stock symbol provided."}), 400

    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d")
        if not data.empty:
            current_price = round(data['Close'].iloc[-1], 2)
            return jsonify({"c": current_price})  # 'c' as per frontend expectation
        else:
            logger.warning(f"No data found for symbol: {symbol}")
            return jsonify({"error": "Invalid stock symbol or no data available."}), 404
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        return jsonify({"error": f"An error occurred: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
