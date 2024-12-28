from flask import Flask, request, jsonify
import yfinance as yf
from flask_cors import CORS

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

if __name__ == '__main__':
    app.run(debug=True)
