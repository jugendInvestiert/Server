from flask import Flask, request, jsonify
import yfinance as yf
from flask_cors import CORS
import pandas as pd
import logging
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)

# Path to the NYSE Trading Units Excel file
EXCEL_FILE_PATH = 'nyse_trading_units.xls'

# Load symbols data from the Excel file
def load_symbols(file_path):
    try:
        df = pd.read_excel(file_path, engine='xlrd')
        # Assuming the Excel columns are: Company Name, Symbol, Txn Code, Y/N, Tape
        # Rename columns for consistency
        df.columns = ['Company Name', 'Symbol', 'Txn Code', 'Y/N', 'Tape']
        # Drop rows where Symbol is NaN
        df = df.dropna(subset=['Symbol'])
        # Convert to list of dictionaries
        symbols = df.to_dict(orient='records')
        app.logger.info(f"Loaded {len(symbols)} symbols from {file_path}.")
        return symbols
    except Exception as e:
        app.logger.error(f"Error loading symbols from {file_path}: {str(e)}")
        return []

# Load symbols at startup
SYMBOLS = load_symbols(EXCEL_FILE_PATH)

@app.route('/api/stock', methods=['GET'])
def get_stock_price():
    symbol = request.args.get('symbol')
    if not symbol:
        app.logger.debug("No stock symbol provided.")
        return jsonify({'error': 'No stock symbol provided'}), 400

    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d")
        if data.empty:
            app.logger.debug(f"Invalid stock symbol or no data found for {symbol}.")
            return jsonify({'error': 'Invalid stock symbol or no data found'}), 404

        latest = data.iloc[-1]
        response = {
            'symbol': symbol.upper(),
            'price': round(latest['Close'], 2),
            'date': latest.name.strftime('%Y-%m-%d'),
            'time': latest.name.strftime('%H:%M:%S')
        }
        app.logger.info(f"Fetched stock price for {symbol}: {response}")
        return jsonify(response)
    except Exception as e:
        app.logger.error(f"Error fetching stock price: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_symbols():
    query = request.args.get('q', '').strip().lower()
    if not query:
        app.logger.debug("No query provided for search.")
        return jsonify({'error': 'No query provided'}), 400

    try:
        # Find symbols where the query is a substring of the Symbol or Company Name
        matched_symbols = [
            symbol for symbol in SYMBOLS
            if query in symbol['Symbol'].lower() or query in symbol['Company Name'].lower()
        ]

        # Limit to top 10 matches
        top_matches = matched_symbols[:10]

        app.logger.info(f"Search query '{query}' returned {len(top_matches)} suggestions.")
        return jsonify({'suggestions': top_matches})
    except Exception as e:
        app.logger.error(f"Error in search_symbols: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Ensure the Excel file exists
    if not os.path.exists(EXCEL_FILE_PATH):
        app.logger.error(f"Excel file '{EXCEL_FILE_PATH}' not found.")
    else:
        app.run(debug=True)
