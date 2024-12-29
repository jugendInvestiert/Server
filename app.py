from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import logging
import os
import csv

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

CSV_FILE_PATH = os.getenv('CSV_FILE_PATH', 'nyse_trading_units.csv')

def load_symbols(file_path):
    encodings_to_try = ['utf-8', 'utf-8-sig', 'iso-8859-1', 'latin1', 'cp1252']
    for enc in encodings_to_try:
        try:
            # Add specific separator and quoting parameters
            df = pd.read_csv(
                file_path,
                encoding=enc,
                sep='\t',  # Use tab as separator
                quoting=csv.QUOTE_NONE,  # Use csv.QUOTE_NONE instead of pd.io.common.QUOTE_NONE
                escapechar='\\',  # Add escape character for handling special characters
                on_bad_lines='skip'  # Skip problematic lines
            )
            
            # Clean column names by stripping whitespace
            df.columns = [col.strip() for col in df.columns]
            
            # Rename columns to match expected format
            column_mapping = {
                'Company': 'Company Name',
                'Symbol': 'Symbol',
                'TU/TXN': 'Txn Code',
                'Auction': 'Y/N',
                'Tape': 'Tape'
            }
            df = df.rename(columns=column_mapping)
            
            # Clean data
            df = df.dropna(subset=['Symbol'])
            df['Symbol'] = df['Symbol'].str.strip()
            df['Company Name'] = df['Company Name'].str.strip()
            
            # Convert to list of dictionaries
            symbols = df.to_dict(orient='records')
            app.logger.info(f"Successfully loaded {len(symbols)} symbols from '{file_path}' using encoding '{enc}'.")
            return symbols
        except UnicodeDecodeError as e:
            app.logger.warning(f"UnicodeDecodeError with encoding '{enc}': {str(e)}")
        except pd.errors.ParserError as e:
            app.logger.error(f"ParserError while reading '{file_path}' with encoding '{enc}': {str(e)}")
        except Exception as e:
            app.logger.error(f"Error loading symbols from '{file_path}' with encoding '{enc}': {str(e)}")
            
            # Add more detailed error logging
            app.logger.error(f"Full error details: {type(e).__name__}: {str(e)}")
            
            # Try to read and log the first few lines of the file for debugging
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    first_lines = [next(f) for _ in range(5)]
                app.logger.error(f"First 5 lines of file:\n{''.join(first_lines)}")
            except Exception as read_error:
                app.logger.error(f"Could not read file for debugging: {str(read_error)}")
    
    app.logger.error(f"Failed to load symbols from '{file_path}' with attempted encodings.")
    return []

# Rest of the code remains the same...

@app.route('/api/stock', methods=['GET'])
def get_stock_price():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({'error': 'No stock symbol provided'}), 400

    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d")
        if data.empty:
            return jsonify({'error': 'Invalid stock symbol or no data found'}), 404

        latest = data.iloc[-1]
        response = {
            'symbol': symbol.upper(),
            'price': float(round(latest['Close'], 2)),
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
        return jsonify({'error': 'No query provided'}), 400

    try:
        matched_symbols = [
            symbol for symbol in SYMBOLS
            if query in symbol['Symbol'].lower() or query in symbol['Company Name'].lower()
        ]

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
    if not os.path.exists(CSV_FILE_PATH):
        app.logger.error(f"CSV file '{CSV_FILE_PATH}' not found.")
    else:
        app.run(debug=True)