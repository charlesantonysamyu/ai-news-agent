"""
Loads configuration from environment variables (.env file).
Copy .env.example to .env and fill in your real values before running.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# --- Core ---
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
MODEL_NAME = _get("MODEL_NAME", "claude-sonnet-5")

# --- Telegram ---
TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _get("TELEGRAM_CHAT_ID")

# --- X / Twitter ---
X_API_KEY = _get("X_API_KEY")
X_API_SECRET = _get("X_API_SECRET")
X_ACCESS_TOKEN = _get("X_ACCESS_TOKEN")
X_ACCESS_SECRET = _get("X_ACCESS_SECRET")

# --- WhatsApp Cloud API (Meta) ---
WHATSAPP_TOKEN = _get("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = _get("WHATSAPP_PHONE_ID")
WHATSAPP_RECIPIENT = _get("WHATSAPP_RECIPIENT")

# --- Blog ---
# Where finished articles get written as Markdown files.
# Point this at a folder inside your static-site repo (Hugo/Astro/Jekyll)
# if you want them to show up on your blog automatically after a git push.
BLOG_OUTPUT_DIR = _get("BLOG_OUTPUT_DIR", "./blog_posts")

# --- Local state DB (dedup + history) ---
DB_PATH = _get("DB_PATH", "./agent_state.db")

# --- RSS sources the agent is allowed to search ---
# Verified reachable/valid as of setup. Anthropic doesn't currently publish
# an RSS feed for its newsroom, so it's not in this list - check
# anthropic.com/news manually, or add it back if that changes.
RSS_FEEDS = [
    "https://openai.com/news/rss.xml",
    "https://blog.google/innovation-and-ai/technology/ai/rss/",
    "https://aws.amazon.com/blogs/machine-learning/feed/",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://news.ycombinator.com/rss",
]
