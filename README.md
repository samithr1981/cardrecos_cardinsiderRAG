# Credit Card Recommendation Engine (India)

A data-driven recommendation system that analyzes your spending patterns across 311+ Indian credit cards and identifies the best cards to maximize rewards, cashback, and travel benefits.

## Overview

With over 300 credit cards available in India, choosing the right one is overwhelming. Cards differ in:
- Reward structures (cashback, points, miles)
- Category-specific multipliers
- Annual fees and waiver conditions
- Caps, limits, and exclusions

**This engine simplifies the process** by automatically evaluating cards against your spending behavior and ranking them by net annual benefit.

## How It Works

### 1. Input Your Spending
Provide your typical monthly spending across categories:
- Groceries
- Dining & Entertainment
- Travel & Flights
- Fuel
- Online Shopping
- Utilities
- Other

### 2. Card Feature Analysis
The system evaluates each of the 311 cards based on:
- Category-wise reward rates
- Bonus multipliers
- Annual fees and waiver conditions
- Spending caps and exclusions
- Welcome bonuses

### 3. Calculate Net Benefit
```
Expected Annual Rewards - Annual Fee = Net Annual Benefit
```
Cards are ranked by highest net value to your specific spend profile.

## Features

✅ **Category-level optimization** - Matches spending patterns to card rewards  
✅ **Net benefit ranking** - Shows real financial advantage after fees  
✅ **Primary + secondary recommendations** - Best card + good alternatives  
✅ **311+ Indian credit cards** - Comprehensive coverage  
✅ **Transparent calculations** - See exactly how each card scores  

## Quick Start

### Installation
```bash
pip install pandas numpy
```

### Basic Usage
```python
from Card_recommender import recommend_card

user_spend = {
    "groceries": 15000,
    "dining": 10000,
    "travel": 20000,
    "fuel": 5000,
    "online": 12000,
    "utilities": 3000,
    "other": 8000
}

best_cards = recommend_card(user_spend)
print(best_cards)
```

### Example Output
| Rank | Card Name | Net Annual Benefit | Annual Fee | Effective Reward % |
|------|-----------|-------------------|-----------|-------------------|
| 1 | XYZ Card | ₹48,500 | ₹5,000 | 4.8% |
| 2 | ABC Card | ₹42,300 | ₹2,500 | 4.2% |

## Project Structure
```
.
├── Card_recommender.py          # Main recommendation engine
├── data/
│   └── card_features.csv        # Card database (311+ cards)
├── notebooks/
│   └── analysis.ipynb           # Analysis & experimentation
└── README.md
```

## Tech Stack
- **Python** - Core language
- **Pandas & NumPy** - Data processing
- **Rule-based engine** - Deterministic reward calculations

## Roadmap

- 🧠 ML-based personalization
- 📊 User segmentation & clustering
- 💰 Risk-adjusted recommendations
- 🪙 Real points-to-cash conversion rates
- 🌐 Web API & Streamlit dashboard
- 🤖 GenAI explanations ("Why this card for you?")

## Disclaimer

⚠️ **Important**: This tool provides analytical recommendations based on structured card data. Actual rewards may vary due to:
- Bank policy changes
- Spending exclusions and exceptions
- Reward caps and limits
- Limited-time promotional offers

**Always verify recommendations with official bank terms and conditions before applying.**

## Contributing

We welcome contributions! Here's how to help:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/your-feature`)
3. **Commit** your changes (`git commit -m 'Add your feature'`)
4. **Push** to the branch (`git push origin feature/your-feature`)
5. **Open** a Pull Request

Contributions welcome for:
- New card datasets
- Additional card features
- Algorithm improvements
- Bug fixes

## License

[Add your license here - e.g., MIT, Apache 2.0]

## Support

Have questions or found an issue? Please open a GitHub Issue with details.

---

**Last Updated**: 2026-02-21 12:24:23