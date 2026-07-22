# AI News Agent

An autonomous agent (not a fixed script) that researches recent AI news,
writes a short article about the most significant story, and publishes it to
your blog, Telegram, X, and WhatsApp. The LLM decides what to cover, whether
a story is a duplicate, how to phrase each channel's post, and how to handle
a failed post — that decision loop is what makes this an agent.

## How it works

- `agent.py` — the control loop. Sends the goal + tool list to Claude, runs
  whatever tools it asks for, feeds results back, repeats until it's done.
- `tools.py` — the 7 tools the agent can call: search news, check duplicate,
  post to blog, post to Telegram, post to WhatsApp, post to X, mark as posted.
- `db.py` — a local SQLite file that remembers what's already been covered,
  so the same story doesn't get posted twice.
- `config.py` — reads all settings from `.env`.

## Setup

```bash
cd ai_news_agent   # or wherever you put these files
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then fill in `.env`. You don't need every credential to start — the agent
will just skip a channel it isn't configured for and keep going.

### 1. Anthropic API key (required)
Get one at console.anthropic.com. Without this, nothing runs.

### 2. Telegram (do this one first — fastest, no approval wait)
1. Message **@BotFather** on Telegram → `/newbot` → follow the prompts.
2. Copy the token into `TELEGRAM_BOT_TOKEN`.
3. Add the bot as an admin of your channel.
4. If your channel is public, `TELEGRAM_CHAT_ID` is `@yourchannelname`.

### 3. X / Twitter
1. developer.x.com → create a project + app.
2. Set app permissions to **Read and Write**.
3. Generate API key/secret and access token/secret, put them in `.env`.
4. Approval for basic posting access is usually fast (often same day).

### 4. WhatsApp (start this one early — it's the slowest)
1. developers.facebook.com → create an app → add the **WhatsApp** product.
2. Business verification can take several days. Kick this off now; the
   agent will simply skip WhatsApp posting until it's configured.
3. Once approved, grab the phone number ID and access token into `.env`.

### 5. Blog
By default the agent writes each article as a Markdown file (with
frontmatter) into `BLOG_OUTPUT_DIR`. If that folder is inside a static site
repo (Hugo/Astro/Jekyll), a `git add . && git commit && git push` after each
run publishes it. If you're on WordPress/Ghost instead, swap the body of
`post_to_blog()` in `tools.py` for a call to that platform's REST API — the
tool's name and arguments can stay the same, nothing else needs to change.

## Run it

```bash
python agent.py
```

Watch the console — it logs every tool call and result as it goes, so you
can see exactly what the agent decided to do.

## Deploying on your DigitalOcean droplet

Keep this fully separate from your SaaS app so it can never affect it:

1. Put this project in its own folder (or its own Docker container).
2. Use its own venv and its own `agent_state.db` — don't touch your SaaS DB.
3. Restrict `.env` permissions: `chmod 600 .env`.
4. Schedule it with cron:
   ```bash
   crontab -e
   # add:
   0 8 * * * /full/path/to/ai_news_agent/run_daily.sh >> /full/path/to/ai_news_agent/run.log 2>&1
   ```
5. If you want it fully isolated, run it in a Docker container with capped
   memory/CPU instead of directly on the host — optional but safer once this
   is running unattended long-term.

## Notes / limits (be upfront about these when you demo it)

- News sourcing is RSS-based for v1 — reliable and free, but limited to the
  feeds listed in `config.py`. Add more feeds any time.
- `max_turns = 20` in `agent.py` is a safety cap so a confused run can't loop
  forever or burn API credits — increase only if needed.
- WhatsApp will fail until Meta approval clears; that's expected, not a bug.
- This is intentionally a single agent with several tools, not the
  multi-agent (Collector/Summarizer/Review) design from the full roadmap doc.
  That's a good "phase 2" upgrade once this version proves the concept.
