from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import logging
import os
import csv
from difflib import SequenceMatcher

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

CSV_FILE_PATH = os.getenv('CSV_FILE_PATH', 'nyse_trading_units.csv')

# Initialize SYMBOLS as a global variable
SYMBOLS = []

def calculate_similarity(query, text):
    """Calculate similarity ratio between query and text"""
    return SequenceMatcher(None, query.lower(), text.lower()).ratio()

def load_symbols(file_path):
    """Load symbols from CSV file and return them"""
    encodings_to_try = ['utf-8', 'utf-8-sig', 'iso-8859-1', 'latin1', 'cp1252']
    for enc in encodings_to_try:
        try:
            if not os.path.exists(file_path):
                app.logger.error(f"CSV file not found at path: {file_path}")
                return []
                
            df = pd.read_csv(
                file_path,
                encoding=enc,
                sep='\t',
                quoting=csv.QUOTE_NONE,
                escapechar='\\',
                on_bad_lines='skip'
            )
            
            df.columns = [col.strip() for col in df.columns]
            
            column_mapping = {
                'Company': 'Company Name',
                'Symbol': 'Symbol',
                'TU/TXN': 'Txn Code',
                'Auction': 'Y/N',
                'Tape': 'Tape'
            }
            df = df.rename(columns=column_mapping)
            
            df = df.dropna(subset=['Symbol'])
            df['Symbol'] = df['Symbol'].str.strip()
            df['Company Name'] = df['Company Name'].str.strip()
            
            symbols = df.to_dict(orient='records')
            app.logger.info(f"Successfully loaded {len(symbols)} symbols from '{file_path}' using encoding '{enc}'.")
            return symbols
            
        except Exception as e:
            app.logger.error(f"Error loading symbols with encoding '{enc}': {str(e)}")
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    first_lines = [next(f) for _ in range(5)]
                app.logger.error(f"First 5 lines of file:\n{''.join(first_lines)}")
            except Exception as read_error:
                app.logger.error(f"Could not read file for debugging: {str(read_error)}")
            continue
    
    app.logger.error(f"Failed to load symbols from '{file_path}' with all attempted encodings.")
    return []

# Load symbols immediately
try:
    SYMBOLS = load_symbols(CSV_FILE_PATH)
    app.logger.info(f"Initially loaded {len(SYMBOLS)} symbols")
except Exception as e:
    app.logger.error(f"Failed to load initial symbols: {str(e)}")

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
    global SYMBOLS
    
    if not SYMBOLS:
        SYMBOLS = load_symbols(CSV_FILE_PATH)
        app.logger.info(f"Reloaded {len(SYMBOLS)} symbols on demand")
    
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    try:
        # Calculate similarity scores for symbols and company names
        matched_symbols = []
        for symbol in SYMBOLS:
            symbol_similarity = calculate_similarity(query, symbol['Symbol'])
            company_similarity = calculate_similarity(query, symbol['Company Name'])
            
            # Check for exact matches at the start
            symbol_starts_with = symbol['Symbol'].lower().startswith(query.lower())
            company_starts_with = symbol['Company Name'].lower().startswith(query.lower())
            
            # Calculate final score (prioritize exact matches and symbols over company names)
            final_score = max(
                symbol_similarity * 2 if symbol_starts_with else symbol_similarity,
                company_similarity if company_starts_with else company_similarity * 0.5
            )
            
            if final_score > 0.1:  # Only include if there's some similarity
                matched_symbols.append({
                    **symbol,
                    'score': final_score
                })

        # Sort by score and take top 5
        top_matches = sorted(matched_symbols, key=lambda x: x['score'], reverse=True)[:5]
        
        # Remove score from final output
        for match in top_matches:
            match.pop('score', None)

        if not top_matches:
            app.logger.info(f"Search query '{query}' returned no suggestions.")
            return jsonify({'message': 'No matching symbols found.'}), 404

        app.logger.info(f"Search query '{query}' returned {len(top_matches)} suggestions.")
        return jsonify({'suggestions': top_matches})
    except Exception as e:
        app.logger.error(f"Error in search_symbols: {str(e)}")
        return jsonify({'error': 'Internal server error.'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'symbols_loaded': len(SYMBOLS)
    })

if __name__ == '__main__':
    if not os.path.exists(CSV_FILE_PATH):
        app.logger.error(f"CSV file '{CSV_FILE_PATH}' not found.")
    else:
        app.run(debug=True)