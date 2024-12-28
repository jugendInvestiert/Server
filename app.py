from flask import Flask, request, jsonify
import yfinance as yf
from flask_cors import CORS
import json
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load symbols data from symbols.json
try:
    with open('symbols.json', 'r') as f:
        SYMBOLS = json.load(f)
    app.logger.info("Loaded symbols.json successfully.")
except Exception as e:
    app.logger.error(f"Error loading symbols.json: {str(e)}")
    SYMBOLS = []

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
        # Simple search: symbols or names containing the query
        results = [
            symbol for symbol in SYMBOLS
            if query in symbol['symbol'].lower() or query in symbol['name'].lower()
        ]

        # Limit the number of suggestions to prevent overwhelming the frontend
        limited_results = results[:10]

        app.logger.info(f"Search query '{query}' returned {len(limited_results)} suggestions.")
        return jsonify({'suggestions': limited_results})
    except Exception as e:
        app.logger.error(f"Error in search_symbols: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
