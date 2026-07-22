"""
The AI agent's control loop.

This is the piece that makes it an *agent* rather than a script: we hand the
LLM a goal and a set of tools, and it decides for itself which tools to call,
in what order, and how to react to the results (e.g. skip a duplicate story,
retry, or continue posting to the remaining channels if one fails).

Run manually:
    python agent.py

Run daily via cron (see run_daily.sh / README.md for the DigitalOcean setup).
"""
import sys
import json
import anthropic

import config
import db
from tools import TOOL_SCHEMAS, TOOL_DISPATCH

SYSTEM_PROMPT = """You are an autonomous AI news agent for a personal tech blog.

Your job, once per run:
1. Search for recent AI news using search_ai_news.
2. Pick the SINGLE most significant, genuinely newsworthy story from the results
   (prefer product launches, major model releases, notable research, security
   advisories - skip minor or purely promotional posts).
3. Use check_duplicate to make sure this story hasn't already been covered.
   If it's a duplicate, pick the next best story and check again.
4. Write a short, clear article about the story (title + 150-300 word body in
   Markdown). Write it yourself in plain, human language - no filler, no
   "in today's fast-paced world" style padding. Add 2-4 short key takeaways.
5. Publish it using the posting tools, in this order: post_to_blog,
   post_to_telegram, post_to_x, post_to_whatsapp. Adapt each message to fit
   the channel (Telegram/X should be a short teaser + link/summary, not the
   full article body).
6. If a posting tool fails (e.g. WhatsApp not approved yet), note the failure
   and continue with the remaining channels - do not stop the whole run.
7. Once everything that can succeed has succeeded, call mark_as_posted so this
   story isn't repeated tomorrow.
8. Finish with a short plain-text summary of what you did and what succeeded
   or failed, so a human can glance at the log.

If search_ai_news returns nothing usable, say so clearly and stop - do not
invent news.
"""


def run():
    if not config.ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)

    db.init_db()
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    messages = [
        {
            "role": "user",
            "content": "Run today's AI news cycle: find, write, and publish one article.",
        }
    ]

    max_turns = 20  # safety cap so a confused loop can't run forever / burn API credits
    for turn in range(max_turns):
        response = client.messages.create(
            model=config.MODEL_NAME,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            # Model is done - print its final summary and exit.
            for block in response.content:
                if block.type == "text":
                    print(block.text)
            return

        # Execute every tool call the model asked for, feed results back.
        tool_results = []
        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"[agent] {block.text.strip()}")
            if block.type == "tool_use":
                fn = TOOL_DISPATCH.get(block.name)
                print(f"[tool call] {block.name}({json.dumps(block.input)[:200]})")
                if fn is None:
                    result = {"error": f"Unknown tool {block.name}"}
                else:
                    try:
                        result = fn(**block.input)
                    except Exception as e:
                        result = {"error": str(e)}
                print(f"[tool result] {json.dumps(result)[:300]}")

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    }
                )

        messages.append({"role": "user", "content": tool_results})

    print("[agent] Hit max_turns safety cap without finishing - check the log above.")


if __name__ == "__main__":
    run()
