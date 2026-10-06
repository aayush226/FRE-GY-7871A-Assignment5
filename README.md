# FRE-GY 7871A: Assignment 5, US Midterms: Issues, Sentiment, Prediction Markets and Stocks

Studies Aug 1 - Oct 5, 2026 ahead of the Nov 3, 2026 midterms. The notebook:

1. finds the issues voters care about with topic modeling (NMF) and an issue lexicon on news and forum text,
2. builds a daily sentiment index for those issues and relates it to the Polymarket probability of a Democratic sweep (correlations and Granger tests),
3. builds a "midterm basket" of stocks and relates the sentiment index to its market-adjusted returns.

## Files

```
.
├── midterm_sentiment_analysis.ipynb   # main notebook (outputs saved)
├── collect_news.py                    # Guardian + Google News + Hacker News -> cache/news_all.csv
├── collect_markets.py                 # Polymarket (and Kalshi) prices -> cache/polymarket_prices.csv
├── requirements.txt
├── .env.example                       # copy to .env and add your Guardian key
├── .gitignore
├── cache/                             # cached data and prices
└── outputs/                           # tables (CSV), figures and the scored documents
```

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env            # add GUARDIAN_API_KEY
python collect_news.py          # about 15 minutes, results are cached
python collect_markets.py
```

Then open the notebook and Run All. Stock prices come from Yahoo Finance (`yfinance`) and are cached after the first run. `.env` is in `.gitignore`, so keys are never committed.
