// server.js
require('dotenv').config();
const express = require('express');
const axios = require('axios');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Endpoint for autocomplete suggestions
app.get('/api/search', async (req, res) => {
    const query = req.query.q;
    if (!query) {
        return res.status(400).json({ error: 'Query parameter "q" is required.' });
    }

    try {
        const response = await axios.get('https://autoc.finance.yahoo.com/autoc', {
            params: {
                query: query,
                region: 1,
                lang: 'en',
            },
            headers: {
                'User-Agent': 'Mozilla/5.0',
            },
        });

        const suggestions = response.data.ResultSet.Result.map(item => ({
            symbol: item.symbol,
            name: item.name,
            exchDisp: item.exchDisp,
            typeDisp: item.typeDisp,
        }));

        res.json(suggestions);
    } catch (error) {
        console.error(error.message);
        res.status(500).json({ error: 'Failed to fetch data from Yahoo Finance.' });
    }
});

// Endpoint to get stock data
app.get('/api/stock', async (req, res) => {
    const symbol = req.query.symbol;
    if (!symbol) {
        return res.status(400).json({ error: 'Query parameter "symbol" is required.' });
    }

    try {
        const response = await axios.get(`https://query1.finance.yahoo.com/v7/finance/quote`, {
            params: {
                symbols: symbol,
            },
            headers: {
                'User-Agent': 'Mozilla/5.0',
            },
        });

        const quote = response.data.quoteResponse.result[0];
        if (!quote) {
            return res.status(404).json({ error: 'Stock data not found.' });
        }

        const stockData = {
            symbol: quote.symbol,
            shortName: quote.shortName,
            longName: quote.longName,
            regularMarketPrice: quote.regularMarketPrice,
            regularMarketOpen: quote.regularMarketOpen,
            regularMarketDayHigh: quote.regularMarketDayHigh,
            regularMarketDayLow: quote.regularMarketDayLow,
            regularMarketVolume: quote.regularMarketVolume,
            regularMarketPreviousClose: quote.regularMarketPreviousClose,
            regularMarketChange: quote.regularMarketChange,
            regularMarketChangePercent: quote.regularMarketChangePercent,
            regularMarketTime: quote.regularMarketTime,
            currency: quote.currency,
            exchangeName: quote.fullExchangeName,
            marketState: quote.marketState,
        };

        res.json(stockData);
    } catch (error) {
        console.error(error.message);
        res.status(500).json({ error: 'Failed to fetch stock data from Yahoo Finance.' });
    }
});

// Root Endpoint
app.get('/', (req, res) => {
    res.send('Stock Backend API is running.');
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
