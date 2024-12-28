from flask import Flask, request, jsonify
import yfinance as yf
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS to allow requests from the frontend

# Endpoint to fetch stock suggestions
@app.route("/search", methods=["GET"])
def search_stocks():
    query = request.args.get("query", "").upper()
    if not query:
        return jsonify([])  # Return empty list if no query

    # Mock stock data (replace with a dynamic list if needed)
    stock_data = [
        {"symbol": "AAPL", "name": "Apple Inc."},
        {"symbol": "GOOGL", "name": "Alphabet Inc."},
        {"symbol": "MSFT", "name": "Microsoft Corporation"},
        {"symbol": "AMZN", "name": "Amazon.com Inc."},
        {"symbol": "TSLA", "name": "Tesla Inc."},
        {"symbol": "META", "name": "Meta Platforms Inc."}
    ]

    # Filter suggestions based on query
    suggestions = [
        stock for stock in stock_data
        if query in stock["symbol"].upper() or query in stock["name"].upper()
    ][:5]  # Limit to 5 results

    return jsonify(suggestions)

# Endpoint to fetch the latest stock price
@app.route("/stock", methods=["GET"])
def get_stock_price():
    ticker = request.args.get("ticker", "").upper()
    if not ticker:
        return jsonify({"error": "No ticker symbol provided."}), 400

    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")
        if not data.empty:
            price = round(data['Close'].iloc[-1], 2)
            return jsonify({"price": price})
        else:
            return jsonify({"error": "Invalid stock ticker or no data available."}), 404
    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
