"""
The agent's toolbox.

Each function here is a capability the LLM can choose to call. The LLM decides
WHEN and WHETHER to call each one, and in what order, based on the system
prompt in agent.py — that decision-making is what makes this an agent rather
than a fixed script.

TOOL_SCHEMAS is what gets sent to the Anthropic API so the model knows what
tools exist and what arguments they take. TOOL_DISPATCH maps each tool name
to the Python function that actually runs it.
"""
import os
import time
import re
import requests
import feedparser

import config
import db

# ---------------------------------------------------------------------------
# 1. search_ai_news
# ---------------------------------------------------------------------------
def search_ai_news(max_results: int = 10) -> dict:
    """Pull recent entries from the configured RSS feeds."""
    items = []
    for feed_url in config.RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
            source_name = parsed.feed.get("title", feed_url)
            for entry in parsed.entries[:5]:
                items.append(
                    {
                        "title": entry.get("title", "").strip(),
                        "url": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "summary": re.sub(
                            "<[^<]+?>", "", entry.get("summary", "")
                        )[:500],
                        "source": source_name,
                    }
                )
        except Exception as e:
            items.append({"error": f"Failed to read {feed_url}: {e}"})

    # newest-ish first isn't guaranteed by feed order, but good enough for v1
    return {"items": items[:max_results]}


# ---------------------------------------------------------------------------
# 2. check_duplicate
# ---------------------------------------------------------------------------
def check_duplicate(title: str, url: str = "") -> dict:
    """Check whether this story has already been covered in a previous run."""
    dup = db.is_duplicate(title, url)
    return {"is_duplicate": dup}


# ---------------------------------------------------------------------------
# 3. post_to_blog
# ---------------------------------------------------------------------------
def post_to_blog(title: str, content_markdown: str, tags: str = "") -> dict:
    """
    Writes the article as a Markdown file with frontmatter into BLOG_OUTPUT_DIR.
    Works out of the box with Hugo / Astro / Jekyll style static sites.

    If you're on WordPress/Ghost instead, replace the body of this function
    with a call to that platform's REST API - the tool interface (name,
    arguments, return shape) can stay exactly the same.
    """
    os.makedirs(config.BLOG_OUTPUT_DIR, exist_ok=True)
    slug = re.sub(r"[^a-z0-9-]+", "-", title.lower()).strip("-")[:80]
    date_str = time.strftime("%Y-%m-%d")
    filename = f"{date_str}-{slug}.md"
    path = os.path.join(config.BLOG_OUTPUT_DIR, filename)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    frontmatter = (
        "---\n"
        f'title: "{title}"\n'
        f"date: {date_str}\n"
        f"tags: {tag_list}\n"
        "---\n\n"
    )

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(frontmatter + content_markdown)
        return {"success": True, "path": path}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 4. post_to_telegram
# ---------------------------------------------------------------------------
def post_to_telegram(message: str) -> dict:
    """Sends a message to your Telegram channel via the Bot API."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return {"success": False, "error": "Telegram bot token/chat id not configured"}

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
        ok = resp.status_code == 200 and resp.json().get("ok", False)
        return {"success": ok, "response": resp.text[:300]}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 5. post_to_whatsapp
# ---------------------------------------------------------------------------
def post_to_whatsapp(message: str) -> dict:
    """
    Sends a text message via the Meta WhatsApp Cloud API.
    Requires an approved WhatsApp Business account + phone number id.
    This is almost always the slowest piece to get approved, so it's
    normal for this tool to fail until that approval comes through.
    """
    if not all([config.WHATSAPP_TOKEN, config.WHATSAPP_PHONE_ID, config.WHATSAPP_RECIPIENT]):
        return {"success": False, "error": "WhatsApp Cloud API not configured yet"}

    url = f"https://graph.facebook.com/v19.0/{config.WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": config.WHATSAPP_RECIPIENT,
        "type": "text",
        "text": {"body": message},
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        return {"success": resp.status_code == 200, "response": resp.text[:300]}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 6. post_to_x
# ---------------------------------------------------------------------------
def post_to_x(message: str) -> dict:
    """Posts a tweet via the X API v2 using OAuth1 user context."""
    if not all(
        [config.X_API_KEY, config.X_API_SECRET, config.X_ACCESS_TOKEN, config.X_ACCESS_SECRET]
    ):
        return {"success": False, "error": "X/Twitter API keys not configured"}

    try:
        import tweepy

        client = tweepy.Client(
            consumer_key=config.X_API_KEY,
            consumer_secret=config.X_API_SECRET,
            access_token=config.X_ACCESS_TOKEN,
            access_token_secret=config.X_ACCESS_SECRET,
        )
        # X caps tweets at 280 chars - trim politely if the model runs long.
        text = message if len(message) <= 280 else message[:277] + "..."
        resp = client.create_tweet(text=text)
        return {"success": True, "response": str(resp.data)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 7. mark_as_posted
# ---------------------------------------------------------------------------
def mark_as_posted(title: str, url: str = "") -> dict:
    """Call this once the article is fully handled, so it's never re-posted."""
    db.mark_seen(title, url)
    return {"success": True}


# ---------------------------------------------------------------------------
# Anthropic tool schemas
# ---------------------------------------------------------------------------
TOOL_SCHEMAS = [
    {
        "name": "search_ai_news",
        "description": "Fetch recent AI news items from configured RSS sources.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Max items to return."}
            },
        },
    },
    {
        "name": "check_duplicate",
        "description": "Check if a story (by title/url) has already been covered in a previous run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "url": {"type": "string"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "post_to_blog",
        "description": "Publish the finished article to the blog as a Markdown file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content_markdown": {"type": "string"},
                "tags": {"type": "string", "description": "Comma-separated tags."},
            },
            "required": ["title", "content_markdown"],
        },
    },
    {
        "name": "post_to_telegram",
        "description": "Send a message to the configured Telegram channel.",
        "input_schema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    },
    {
        "name": "post_to_whatsapp",
        "description": "Send a message via the WhatsApp Cloud API.",
        "input_schema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    },
    {
        "name": "post_to_x",
        "description": "Post a tweet/post to X (Twitter). Max 280 characters; will be trimmed if longer.",
        "input_schema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    },
    {
        "name": "mark_as_posted",
        "description": "Record that an article has been fully published, to prevent duplicate posting in future runs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "url": {"type": "string"},
            },
            "required": ["title"],
        },
    },
]

TOOL_DISPATCH = {
    "search_ai_news": search_ai_news,
    "check_duplicate": check_duplicate,
    "post_to_blog": post_to_blog,
    "post_to_telegram": post_to_telegram,
    "post_to_whatsapp": post_to_whatsapp,
    "post_to_x": post_to_x,
    "mark_as_posted": mark_as_posted,
}
