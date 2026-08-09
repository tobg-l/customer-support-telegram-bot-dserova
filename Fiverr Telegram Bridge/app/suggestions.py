"""Suggested-reply generation: sends the incoming message to an LLM along with
your standard reply templates, and asks it to pick the closest-matching one
and personalize it. Returns None (no suggestion shown) if OPENAI_API_KEY is unset
or the call fails - the Telegram notification still goes out either way."""
import re

from . import config

REPLY_TEMPLATES = """
1. Generic first inquiry ("I need automation help")
Hey [Name] 👋 Happy to help. To point you in the right direction: what's the manual process you're trying to automate, and what tools/platforms are involved? (e.g. CRM, Telegram, spreadsheets, etc.) Once I know that I can tell you exactly what's possible and give you a realistic scope.

2. They describe something vague ("I need a bot")
Got it, a few quick questions so I scope this right:
- What platform should the bot run on? (Telegram, WhatsApp, web?)
- What should it actually do: answer questions, collect info, connect to a database, something else?
- Do you have an existing backend/API or are we building from scratch?
These details make a big difference to the timeline and price. Happy to jump on a quick call too if easier 👍

3. Budget objection ("That's too expensive")
Totally understand, budgets vary a lot. The price reflects a production-ready Python build with proper error handling and documentation, not a quick no-code workaround. That said, if you want to tell me which part matters most to you, I can often structure a smaller Phase 1 that delivers the core value first. What's your budget range?

4. "Can you do this in [X timeframe]?" (unrealistic deadline)
I want to be honest with you: rushing this would mean cutting corners on testing, and that creates problems post-delivery. A realistic timeline for what you're describing is [X days]. I can prioritise your project if you're ready to start today. Would that work?

5. After they place an order
Thanks for the order! 🙌 I'll start with a short discovery to make sure I build exactly what you need. I'll send you 3-4 questions shortly, the faster you can get back to me, the sooner we can get moving. Expected delivery: [date].

6. Revision request
No problem, let me take a look. Can you describe specifically what's not working or what you'd like changed? A screenshot or example helps a lot. I'll get back to you within [X hours] with either a fix or a quick explanation of what's happening.

7. "Do you have samples/portfolio?"
Yes, here are a few examples relevant to what you need: [describe 1-2 case studies in 1 sentence each, e.g. "AI lead qualification bot that cut manual sales work by 35% for a CRM client" / "WhatsApp automation handling 20+ order management tasks for an e-commerce brand"]. Full details and metrics available if useful. What's your project?
""".strip()

SYSTEM_PROMPT = f"""You help a freelance automation developer respond to Fiverr buyer messages.

Below are their 7 standard reply templates, each for a distinct situation:

{REPLY_TEMPLATES}

Given an incoming buyer message, do the following:
1. Identify which of the 7 situations it matches best (or "none" if it clearly doesn't fit any).
2. Write a ready-to-send reply based on that template, personalized with any concrete details
   from the message (buyer's name if known, amounts, timeframes, platforms mentioned, etc).
   Fill in bracketed placeholders like [Name]/[X days] with real values when you can infer them
   from the message; otherwise pick a sensible placeholder or drop that clause gracefully.
3. If none of the 7 templates fit, write a short, friendly, professional freelancer reply from
   scratch instead - don't force a bad fit.
4. Keep the same tone as the templates: direct, friendly, no corporate fluff.
5. Never use em dashes (—) or en dashes (–) anywhere in the reply. Use a comma, period, colon,
   or a regular hyphen instead - em/en dashes read as AI-generated and must be avoided entirely.

Respond with ONLY the reply text - no preamble, no labels, no quotation marks around it."""

_LONG_DASH_RE = re.compile(r"\s*[–—]\s*")


def _strip_long_dashes(text):
    """Belt-and-braces cleanup in case the model uses an em/en dash despite
    being told not to - replaces it (and any surrounding spaces) with ", "."""
    return _LONG_DASH_RE.sub(", ", text).strip()


def _client():
    if not config.OPENAI_API_KEY:
        return None
    from openai import OpenAI

    return OpenAI(api_key=config.OPENAI_API_KEY)


def get_suggestion(subject, body):
    client = _client()
    if client is None:
        return None

    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Subject: {subject}\n\nMessage:\n{body}",
                },
            ],
            temperature=0.4,
        )
        return _strip_long_dashes(response.choices[0].message.content.strip())
    except Exception as exc:
        print(f"[suggestions] OpenAI call failed, skipping suggestion: {exc}")
        return None
