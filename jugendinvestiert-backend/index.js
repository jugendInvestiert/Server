// At the top of your file, add:
const express = require('express');
const cors = require('cors');
const yahooFinance = require('yahoo-finance2').default;

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());

// Endpoint to fetch stock symbols
app.get('/stock/symbol', async (req, res) => {
    // Since Yahoo Finance doesn't provide a complete list, we'll use a static list
    const symbols = [
        { symbol: 'AAPL', name: 'Apple Inc.' },
        { symbol: 'GOOGL', name: 'Alphabet Inc.' },
        { symbol: 'MSFT', name: 'Microsoft Corporation' },
        { symbol: 'AMZN', name: 'Amazon.com, Inc.' },
        { symbol: 'TSLA', name: 'Tesla, Inc.' },
        // Add more symbols as needed
    ];
    res.json(symbols);
});

// Endpoint to fetch quote for a symbol
app.get('/quote', async (req, res) => {
    const symbol = req.query.symbol;
    if (!symbol) {
        return res.status(400).json({ error: 'Symbol parameter "symbol" is required.' });
    }

    try {
        const quote = await yahooFinance.quote(symbol);
        if (!quote || typeof quote.regularMarketPrice !== 'number') {
            return res.status(404).json({ error: 'Quote not found for the provided symbol.' });
        }

        res.json({
            c: quote.regularMarketPrice
            // You can add more fields if needed
        });
    } catch (error) {
        console.error(`Error fetching quote for ${symbol}:`, error);
        res.status(500).json({ error: `Error fetching quote for symbol: ${symbol}` });
    }
});

app.listen(PORT, () => {
    console.log(`Backend server is running on port ${PORT}`);
});
