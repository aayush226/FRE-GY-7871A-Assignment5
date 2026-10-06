# AI Use Disclosure

Author: Aayush Shah

This project used Claude (Anthropic) as a coding and research assistant
throughout development, working interactively in a chat session, the same
way as the earlier assignments.

## What AI was used for

- Planning the project from the assignment prompt: the choice of sources
  (Guardian, Google News RSS, Hacker News, Polymarket, Yahoo Finance), the
  topic model plus issue lexicon design, the daily sentiment indices, the
  correlation and Granger tests against the prediction market, and the
  midterm basket with sub-baskets and a sign check against the market.
- Editing the code: the notebook, `collect_news.py`, `collect_markets.py`
  and the source check script, including the hand-coded Granger F-test
  that is cross-checked against statsmodels and the permutation p-value.
- Debugging real problems found while running things, including: Reddit and
  Bluesky blocking requests (so they were dropped); GDELT's rate limit being
  too slow for a day-by-day pull (so it was switched off); finding that the
  Polymarket market called "Democratic sweep?" was the resolved 2025
  contract and using the 2026 "D Senate, D House" contract instead; Kalshi
  returning prices in a text field; and several smaller notebook bugs.
- Reading the topic model output and assigning the topic labels and issue
  lexicon, choosing the hypothesised sign for each stock in the basket, and
  drafting the Findings, the report text and tables from the notebook's
  actual outputs. One early guess of mine about what drove the basket
  (oil prices) turned out to be wrong when the per-stock returns came back,
  and the report was corrected.

## What was NOT AI-generated / required my own judgment

- Getting the Guardian API key and keeping it out of the repository with
  an env file, and deciding to drop Twitter, Reddit and Bluesky.
- Drafting and running the collection scripts and the notebook on my own machine,
  pasting back the outputs, and checking that the notebook had saved
  outputs before the results were written up.
- Checking the numbers in the report against the notebook outputs, and the
  decision to report the results as "no detectable effect" because of the
  short window and noisy news data instead of claiming a finding.
- All final review, editing, and submission of the report, this disclosure
  and the notebook.

## Model

Claude (Anthropic), configured as Sonnet 5.5, via claude.ai over multiple
sessions ending October 6, 2026. The model serving a given turn may have
differed from the configured one.
