from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import pandas as pd
import csv
import re

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

CSV_FILE_PATH = os.getenv('CSV_FILE_PATH', 'nyse_trading_units.csv')

SYMBOLS = []

def load_symbols(file_path):
    """Load symbols from the CSV file"""
    try:
        if not os.path.exists(file_path):
            app.logger.error(f"CSV file not found at path: {file_path}")
            return []

        df = pd.read_csv(
            file_path,
            encoding='utf-8',
            sep=',',
            quoting=csv.QUOTE_MINIMAL
        )

        df.columns = [col.strip() for col in df.columns]
        df = df.dropna(subset=['Symbol', 'Company Name'])
        df['Symbol'] = df['Symbol'].str.strip()
        df['Company Name'] = df['Company Name'].str.strip()

        symbols = df.to_dict(orient='records')
        app.logger.info(f"Successfully loaded {len(symbols)} symbols from '{file_path}'.")
        return symbols
    except Exception as e:
        app.logger.error(f"Error loading symbols: {str(e)}")
        return []

def bold_match(text, query):
    """Highlight matching parts of text"""
    regex = re.compile(f"({re.escape(query)})", re.IGNORECASE)
    return regex.sub(r"<b>\1</b>", text)

@app.route('/api/search', methods=['GET'])
def search_symbols():
    """Search for symbols and descriptions"""
    global SYMBOLS

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    try:
        query_upper = query.upper()

        # Matching logic
        exact_matches = [
            symbol for symbol in SYMBOLS
            if symbol['Symbol'].upper() == query_upper or symbol['Company Name'].upper() == query_upper
        ]
        starts_with_matches = [
            symbol for symbol in SYMBOLS
            if (symbol['Symbol'].upper().startswith(query_upper) or symbol['Company Name'].upper().startswith(query_upper))
            and symbol not in exact_matches
        ]
        includes_matches = [
            symbol for symbol in SYMBOLS
            if (query_upper in symbol['Symbol'].upper() or query_upper in symbol['Company Name'].upper())
            and symbol not in exact_matches
            and symbol not in starts_with_matches
        ]

        # Combine results and limit to top 5 suggestions
        combined = exact_matches + starts_with_matches + includes_matches
        unique_combined = []
        seen = set()
        for symbol in combined:
            if symbol['Symbol'] not in seen:
                seen.add(symbol['Symbol'])
                unique_combined.append(symbol)

        top_matches = unique_combined[:5]

        # Highlight matches
        for match in top_matches:
            match['Symbol'] = bold_match(match['Symbol'], query)
            match['Company Name'] = bold_match(match['Company Name'], query)

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
    SYMBOLS = load_symbols(CSV_FILE_PATH)
    if not SYMBOLS:
        app.logger.error("Failed to load symbols from the CSV file.")
    else:
        app.run(debug=True)
