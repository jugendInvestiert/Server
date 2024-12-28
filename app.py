from flask import Flask, request, jsonify
import yfinance as yf
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS to allow frontend requests

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
            'price': round(latest['Close'], 2),
            'date': latest.name.strftime('%Y-%m-%d'),
            'time': latest.name.strftime('%H:%M:%S')
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_symbols():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    try:
        # Yahoo Finance Autocomplete API Endpoint
        url = 'https://autoc.finance.yahoo.com/autoc'
        params = {
            'query': query,
            'region': '1',
            'lang': 'en'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }

        response = requests.get(url, params=params, headers=headers)
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch data from Yahoo Finance'}), 500

        data = response.json()
        suggestions = data.get('ResultSet', {}).get('Result', [])

        # Extract relevant information
        results = []
        for item in suggestions:
            # Filter for equities (stocks)
            if item.get('type') == 'equity':
                results.append({
                    'symbol': item.get('symbol'),
                    'name': item.get('name'),
                    'exchDisp': item.get('exchDisp')
                })

        return jsonify({'suggestions': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
