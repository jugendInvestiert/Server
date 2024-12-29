from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import logging
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)

# Path to the NYSE Trading Units CSV file
CSV_FILE_PATH = os.getenv('CSV_FILE_PATH', 'nyse_trading_units.csv')

# Load symbols data from the CSV file with multiple encoding attempts
def load_symbols(file_path):
    encodings_to_try = ['utf-8-sig', 'utf-16', 'latin1']  # Add more encodings if needed
    for enc in encodings_to_try:
        try:
            df = pd.read_csv(file_path, encoding=enc)
            # Rename columns for consistency
            df.columns = ['Company Name', 'Symbol', 'Txn Code', 'Y/N', 'Tape']
            # Drop rows where Symbol is NaN
            df = df.dropna(subset=['Symbol'])
            # Convert to list of dictionaries
            symbols = df.to_dict(orient='records')
            app.logger.info(f"Loaded {len(symbols)} symbols from '{file_path}' using encoding '{enc}'.")
            return symbols
        except UnicodeDecodeError as e:
            app.logger.warning(f"UnicodeDecodeError with encoding '{enc}': {str(e)}")
        except pd.errors.ParserError as e:
            app.logger.error(f"ParserError while reading '{file_path}' with encoding '{enc}': {str(e)}")
            break  # If parsing fails, no point in trying other encodings
        except Exception as e:
            app.logger.error(f"Error loading symbols from '{file_path}' with encoding '{enc}': {str(e)}")
            break
    app.logger.error(f"Failed to load symbols from '{file_path}' with attempted encodings.")
    return []

# Load symbols at startup
SYMBOLS = load_symbols(CSV_FILE_PATH)

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
            'price': float(round(latest['Close'], 2)),  # Ensure float type
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

        if not top_matches:
            app.logger.info(f"Search query '{query}' returned no suggestions.")
            return jsonify({'message': 'No matching symbols found.'}), 404

        app.logger.info(f"Search query '{query}' returned {len(top_matches)} suggestions.")
        return jsonify({'suggestions': top_matches})
    except Exception as e:
        app.logger.error(f"Error in search_symbols: {str(e)}")
        return jsonify({'error': 'Internal server error.'}), 500

if __name__ == '__main__':
    # Ensure the CSV file exists
    if not os.path.exists(CSV_FILE_PATH):
        app.logger.error(f"CSV file '{CSV_FILE_PATH}' not found.")
    else:
        app.run(debug=True)
