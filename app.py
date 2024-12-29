from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import pandas as pd
import csv
import re
from fuzzywuzzy import fuzz
from unidecode import unidecode
import numpy as np

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

CSV_FILE_PATH = os.getenv('CSV_FILE_PATH', 'nyse_trading_units.csv')
SYMBOLS = []

def load_symbols(file_path):
    """Load and preprocess symbols from the CSV file"""
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
        
        # Preprocess company names for better matching
        df['Search Name'] = df['Company Name'].apply(lambda x: preprocess_text(x))
        
        symbols = df.to_dict(orient='records')
        app.logger.info(f"Successfully loaded {len(symbols)} symbols from '{file_path}'.")
        return symbols
    except Exception as e:
        app.logger.error(f"Error loading symbols: {str(e)}")
        return []

def preprocess_text(text):
    """Preprocess text for better matching"""
    # Convert to ASCII, remove special characters
    text = unidecode(text)
    # Remove common company suffixes
    suffixes = [' INC', ' CORP', ' LTD', ' LLC', ' CO', ' CORPORATION', ' LIMITED']
    for suffix in suffixes:
        text = text.upper().replace(suffix, '')
    # Remove special characters and extra spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    return ' '.join(text.split())

def get_match_score(symbol_data, query):
    """Calculate match score based on multiple criteria"""
    query = query.upper()
    preprocessed_query = preprocess_text(query)
    
    symbol = symbol_data['Symbol'].upper()
    company = symbol_data['Company Name'].upper()
    search_name = symbol_data['Search Name']
    
    scores = {
        'exact_symbol': 100 if symbol == query else 0,
        'exact_name': 100 if company == query else 0,
        'symbol_starts': 90 if symbol.startswith(query) else 0,
        'name_starts': 85 if company.startswith(query) else 0,
        'symbol_contains': 80 if query in symbol else 0,
        'name_contains': 75 if query in company else 0,
        'fuzzy_symbol': fuzz.partial_ratio(symbol, query),
        'fuzzy_name': fuzz.partial_ratio(search_name, preprocessed_query),
        'token_sort': fuzz.token_sort_ratio(search_name, preprocessed_query)
    }
    
    # Weight the scores
    weights = {
        'exact_symbol': 1.0,
        'exact_name': 0.9,
        'symbol_starts': 0.8,
        'name_starts': 0.7,
        'symbol_contains': 0.6,
        'name_contains': 0.5,
        'fuzzy_symbol': 0.4,
        'fuzzy_name': 0.3,
        'token_sort': 0.2
    }
    
    final_score = sum(score * weights[key] for key, score in scores.items())
    return final_score

def bold_match(text, query):
    """Highlight matching parts of text with improved matching"""
    if not query:
        return text
    
    # Escape special regex characters in query
    query_escaped = re.escape(query)
    
    # Match whole words first
    whole_word_pattern = r'\b(' + query_escaped + r')\b'
    text = re.sub(whole_word_pattern, r'<b>\1</b>', text, flags=re.IGNORECASE)
    
    # Then match partial words
    partial_pattern = r'(' + query_escaped + r')'
    text = re.sub(partial_pattern, r'<b>\1</b>', text, flags=re.IGNORECASE)
    
    return text

@app.route('/api/search', methods=['GET'])
def search_symbols():
    """Enhanced search for symbols and company names"""
    global SYMBOLS

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    try:
        # Calculate scores for all symbols
        scored_matches = [
            {
                **symbol,
                'score': get_match_score(symbol, query)
            }
            for symbol in SYMBOLS
        ]
        
        # Filter out low-scoring matches and sort by score
        min_score = 30  # Minimum score threshold
        matches = [
            match for match in scored_matches
            if match['score'] > min_score
        ]
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        # Take top 5 matches
        top_matches = matches[:5]
        
        # Highlight matches and prepare response
        results = []
        for match in top_matches:
            results.append({
                'Symbol': bold_match(match['Symbol'], query),
                'Company Name': bold_match(match['Company Name'], query),
                'score': round(match['score'], 2)  # Include score for debugging
            })

        if not results:
            app.logger.info(f"Search query '{query}' returned no suggestions.")
            return jsonify({'message': 'No matching symbols found.'}), 404

        app.logger.info(f"Search query '{query}' returned {len(results)} suggestions.")
        return jsonify({'suggestions': results})
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