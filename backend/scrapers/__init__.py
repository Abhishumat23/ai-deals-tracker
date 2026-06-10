"""
Scraper registry.
Add new scrapers here to include them in the monitoring cycle.
"""

from scrapers.openai_scraper import scrape as scrape_openai, TOOL_NAME as OPENAI_NAME
from scrapers.claude_scraper import scrape as scrape_claude, TOOL_NAME as CLAUDE_NAME
from scrapers.gemini_scraper import scrape as scrape_gemini, TOOL_NAME as GEMINI_NAME
from scrapers.perplexity_scraper import scrape as scrape_perplexity, TOOL_NAME as PERPLEXITY_NAME
from scrapers.cursor_scraper import scrape as scrape_cursor, TOOL_NAME as CURSOR_NAME

# Each entry: (tool_name, async_scrape_function)
# To add a new tool, create a new scraper module and add it here.
ALL_SCRAPERS = [
    (OPENAI_NAME, scrape_openai),
    (CLAUDE_NAME, scrape_claude),
    (GEMINI_NAME, scrape_gemini),
    (PERPLEXITY_NAME, scrape_perplexity),
    (CURSOR_NAME, scrape_cursor),
]
