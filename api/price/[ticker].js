const axios = require('axios');
const cheerio = require('cheerio');

module.exports = async (req, res) => {
    const ticker = req.query.ticker?.toUpperCase();

    if (!ticker) {
        return res.status(400).json({ error: 'Ticker symbol is required' });
    }

    const url = `https://finance.yahoo.com/quote/${ticker}/`;

    try {
        const response = await axios.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        });
        const $ = cheerio.load(response.data);

        // Find price in fin-streamer element
        const priceElement = $(`fin-streamer[data-symbol="${ticker}"][data-field="regularMarketPrice"]`).first();

        if (priceElement.length && priceElement.text()) {
            const price = parseFloat(priceElement.text().replace(',', ''));
            console.log(`Debug: Found price for ${ticker}: ${price}`);
            return res.status(200).json({ price });
        } else {
            console.log(`Debug: Price element not found for ${ticker}`);
            // Fallback: Try alternative selector
            const altPriceElement = $('span[class*="price"]').first();
            if (altPriceElement.length && altPriceElement.text()) {
                const price = parseFloat(altPriceElement.text().replace(',', ''));
                console.log(`Debug: Found alternative price for ${ticker}: ${price}`);
                return res.status(200).json({ price });
            }
            return res.status(404).json({ price: null });
        }
    } catch (error) {
        console.error(`Error fetching data for ${ticker}:`, error.message);
        return res.status(500).json({ error: 'Failed to fetch price' });
    }
};