import re
from backend.utils import extract_price_mentions, convert_to_inr

texts = [
    "Pro $20 per month",
    "$20/mo",
    "₹ 1,950 INR / महीना",
    "$20 billed annually",
    "$16.66 / mo billed yearly"
]

for t in texts:
    print(f"Original: {t}")
    print(f"Extracted: {extract_price_mentions(t)}")
    print("---")
