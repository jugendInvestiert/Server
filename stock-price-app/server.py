# server.py

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yfinance as yf
import logging
import os

app = Flask(__name__, static_folder='.')  # Serve static files from current directory
CORS(app)  # Enable CORS to allow requests from the frontend

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/', methods=['GET'])
def serve_frontend():
    """
    Serve the simulator.html frontend.
    """
    return send_from_directory('.', 'simulator.html')

@app.route('/quote', methods=['GET'])
def get_stock_quote():
    """
    Fetch stock quote from Yahoo Finance.
    """
    symbol = request.args.get('symbol', '').upper()
    
    if not symbol:
        logger.error("No stock symbol provided.")
        return jsonify({"error": "Please provide a stock symbol."}), 400

    try:
        stock = yf.Ticker(symbol)
        data = stock.info

        if 'regularMarketPrice' not in data or data['regularMarketPrice'] is None:
            logger.warning(f"No data found for symbol: {symbol}")
            return jsonify({"error": "Invalid stock symbol or no data available."}), 404

        stock_quote = {
            "symbol": data.get("symbol", "N/A"),
            "shortName": data.get("shortName", "N/A"),
            "longName": data.get("longName", "N/A"),
            "price": data.get("regularMarketPrice", "N/A"),
            "currency": data.get("currency", "N/A"),
            "exchange": data.get("exchange", "N/A"),
            "timestamp": data.get("regularMarketTime", "N/A")
        }

        logger.info(f"Fetched data for {symbol}: {stock_quote}")
        return jsonify(stock_quote)
    
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return jsonify({"error": "An error occurred while fetching stock data."}), 500

if __name__ == '__main__':
    # Get the port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
