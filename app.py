import os
import json
import uuid
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any

import streamlit as st
from openai import OpenAI


st.set_page_config(
    page_title="Koocester SG Viral Intelligence Engine",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "analytics.db"
DEFAULT_MODEL = "gpt-5.4"


# --------------------------------------------------
# DATABASE
# --------------------------------------------------
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            session_id TEXT NOT NULL,
            page TEXT,
            platform TEXT,
            market TEXT,
            role_mode TEXT,
            niche TEXT,
            audience TEXT,
            lead_type TEXT,
            pain_point TEXT,
            offer TEXT,
            goal TEXT,
            video_length TEXT,
            tone TEXT,
            scenario TEXT,
            action_type TEXT NOT NULL,
            output_chars INTEGER DEFAULT 0,
            user_agent TEXT,
            uploaded_files_json TEXT,
            uploaded_total_bytes INTEGER DEFAULT 0,
            uploaded_count INTEGER DEFAULT 0,
            ip_value TEXT,
            ip_source TEXT,
            notes TEXT
        )
        """
    )
    return conn


def insert_usage_log(payload: dict) -> None:
    conn = get_db()
    conn.execute(
        """
        INSERT INTO usage_logs (
            ts, session_id, page, platform, market, role_mode, niche, audience, lead_type,
            pain_point, offer, goal, video_length, tone, scenario, action_type,
            output_chars, user_agent, uploaded_files_json,
            uploaded_total_bytes, uploaded_count, ip_value, ip_source, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.get("ts"),
            payload.get("session_id"),
            payload.get("page"),
            payload.get("platform"),
            payload.get("market"),
            payload.get("role_mode"),
            payload.get("niche"),
            payload.get("audience"),
            payload.get("lead_type"),
            payload.get("pain_point"),
            payload.get("offer"),
            payload.get("goal"),
            payload.get("video_length"),
            payload.get("tone"),
            payload.get("scenario"),
            payload.get("action_type"),
            payload.get("output_chars", 0),
            payload.get("user_agent"),
            payload.get("uploaded_files_json"),
            payload.get("uploaded_total_bytes", 0),
            payload.get("uploaded_count", 0),
            payload.get("ip_value"),
            payload.get("ip_source"),
            payload.get("notes"),
        ),
    )
    conn.commit()
    conn.close()


def read_recent_logs(limit: int = 200) -> List[dict]:
    conn = get_db()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT *
        FROM usage_logs
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --------------------------------------------------
# SESSION / ADMIN
# --------------------------------------------------
def get_session_id() -> str:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    return st.session_state.session_id


def get_admin_password() -> str:
    return st.secrets.get("ADMIN_PASSWORD", "")


def is_admin() -> bool:
    return bool(st.session_state.get("admin_authenticated", False))


def render_admin_login() -> None:
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    with st.sidebar:
        st.header("🔒 Admin Access")
        password = st.text_input("Enter admin password", type="password")

        if password:
            if password == get_admin_password():
                st.session_state.admin_authenticated = True
                st.success("Admin mode activated")
            else:
                st.error("Wrong password")

        st.divider()
        st.header("Engine Priorities")
        st.markdown(
            """
- Singapore-first relevance
- page-aware outputs
- same brand path, stronger execution
- viral now + rising next
- competitor intelligence
- producer mode
- copywriter mode
- storyboard + script depth
- better leads + better retention
"""
        )


# --------------------------------------------------
# REQUEST METADATA
# --------------------------------------------------
def get_user_agent() -> str:
    try:
        return st.context.headers.get("user-agent", "")
    except Exception:
        return ""


def get_ip_if_available() -> Tuple[str, str]:
    try:
        headers = st.context.headers
        for name in ["x-forwarded-for", "x-real-ip", "cf-connecting-ip", "forwarded"]:
            value = headers.get(name)
            if value:
                return value, f"header:{name}"
    except Exception:
        pass
    return "unavailable", "not_exposed"


# --------------------------------------------------
# OPENAI CLIENT
# --------------------------------------------------
def get_client() -> OpenAI:
    api_key = st.secrets.get("OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY. Add it to Streamlit Secrets.")
    return OpenAI(api_key=api_key)


# --------------------------------------------------
# FILE HELPERS
# --------------------------------------------------
def summarize_uploaded_files(uploaded_files) -> Tuple[str, str, int, int]:
    if not uploaded_files:
        return "No files uploaded.", "[]", 0, 0

    lines = []
    file_meta = []
    total_bytes = 0

    for f in uploaded_files:
        size = getattr(f, "size", 0) or 0
        total_bytes += size
        file_meta.append({"name": f.name, "size_bytes": size, "type": f.type})
        lines.append(f"- {f.name} ({size} bytes, type={f.type or 'unknown'})")

    return "\n".join(lines), json.dumps(file_meta), len(uploaded_files), total_bytes


# --------------------------------------------------
# PAGE INTELLIGENCE
# --------------------------------------------------
PAGE_INTELLIGENCE = {
    "Koocester Main": {
        "internal_key": "main",
        "audience": "Singapore lifestyle audience, aspirational viewers, young professionals, founders, social audience, premium discovery audience",
        "lead_type": "Brand engagement leads, ecosystem leads, premium awareness audience",
        "tone": "Premium",
        "default_goal": "Awareness",
        "recommended_mode": "Brand-Led Viral Discovery",
        "recommended_length": "90 sec",
        "allowed_lengths": ["30 sec", "45 sec", "60 sec", "90 sec", "120 sec", "180 sec"],
        "niche_memory": "Premium Singapore lifestyle content, founder ecosystem exposure, discovery-led social content, brand-driven high-perception videos",
        "page_direction": "Broad Koocester brand content that should still feel premium, sharp, culturally relevant to Singapore, and social-first.",
        "winning_formats": [
            "strong opinion hook",
            "event atmosphere with meaning",
            "social proof montage",
            "premium micro-story",
            "aspirational lifestyle cut",
            "curiosity-led discovery reel",
        ],
        "viral_now": [
            "fast subtitle reels with premium cuts",
            "short social-proof clips with strong first sentence",
            "micro-story reels that reveal payoff early",
            "clean event reels with tension instead of generic recaps",
        ],
        "rising_next": [
            "identity-based lifestyle hooks",
            "short documentary-style brand snippets",
            "community-status storytelling",
            "high-contrast before-vs-after perception edits",
        ],
        "competitor_patterns": [
            "premium event recap with stronger tension in first 2 seconds",
            "bold statement before visuals fully establish context",
            "fast pacing with cleaner caption styling",
            "emotion + credibility combined quickly",
        ],
    },
    "Koocester Business Singapore": {
        "internal_key": "business",
        "audience": "Singapore founders, business owners, operators, startup audience, networking audience, ambitious professionals",
        "lead_type": "Founder/event leads, networking leads, brand authority leads, business ecosystem leads",
        "tone": "Bold",
        "default_goal": "Leads",
        "recommended_mode": "Authority + Retention",
        "recommended_length": "90 sec",
        "allowed_lengths": ["30 sec", "45 sec", "60 sec", "90 sec", "120 sec", "180 sec", "240 sec"],
        "niche_memory": "Founder networking, business insight, business psychology, startup/operator talk, high-value rooms, social proof for serious founders",
        "page_direction": "Business content should feel intelligent, sharp, premium, opinionated when needed, and useful enough for founders to save or send.",
        "winning_formats": [
            "contrarian founder hook",
            "what founders get wrong",
            "high-value room vs low-value room comparison",
            "short founder lesson clip",
            "networking ROI explanation",
            "business myth breakdown",
        ],
        "viral_now": [
            "hard-truth founder hooks",
            "anti-fluff networking breakdowns",
            "short clips exposing useless founder behavior",
            "high-status room analysis with strong subtitles",
        ],
        "rising_next": [
            "operator confession format",
            "business lesson from one real moment",
            "event room psychology content",
            "comment-bait controversial founder opinions",
        ],
        "competitor_patterns": [
            "most strong business reels start with tension immediately",
            "reels that compare bad vs good founder behavior perform better than generic motivation",
            "captions often stay short, sharp, and high-conviction",
            "strongest videos create disagreement early to drive comments",
        ],
    },
    "Koocester Autos Singapore": {
        "internal_key": "autos",
        "audience": "Singapore car buyers, luxury car audience, aspirational viewers, enthusiasts, first-time premium buyers",
        "lead_type": "Premium buyer leads, showroom traffic leads, aspiration-driven leads",
        "tone": "Premium",
        "default_goal": "Leads",
        "recommended_mode": "Extended Visual Storytelling",
        "recommended_length": "90 sec",
        "allowed_lengths": ["30 sec", "45 sec", "60 sec", "90 sec", "120 sec", "180 sec"],
        "niche_memory": "Luxury ownership emotion, aspiration, premium car buyer psychology, driving POV, design/status storytelling, comparison-led buyer logic",
        "page_direction": "Autos content should feel premium, cinematic, emotionally persuasive, and still grounded enough to move buyers closer to action.",
        "winning_formats": [
            "premium buyer mistake",
            "ownership feeling POV",
            "badge vs real ownership reality",
            "luxury reveal with emotional narration",
            "comparison reel",
            "aspirational day-in-life cut",
        ],
        "viral_now": [
            "POV ownership experience reels",
            "emotion-first luxury hooks",
            "short comparison reels with clear conclusion",
            "premium detail shots with a sharper first line",
        ],
        "rising_next": [
            "one hidden truth before buying premium",
            "buyer regret prevention reels",
            "status vs practicality comparison",
            "driving moment + narration hybrids",
        ],
        "competitor_patterns": [
            "top auto content makes viewers imagine ownership, not just view the car",
            "best hooks create a buyer decision tension quickly",
            "clean cinematic visuals still need a strong voiceover line to perform",
            "showcase-only videos are weaker than decision-led stories",
        ],
    },
    "Koocester Homes Singapore": {
        "internal_key": "homes",
        "audience": "Singapore homeowners, condo buyers, landed property audience, renovation planners, premium home audience",
        "lead_type": "Renovation leads, home consultation leads, property lifestyle audience",
        "tone": "Premium",
        "default_goal": "Leads",
        "recommended_mode": "Long Visual Storytelling",
        "recommended_length": "120 sec",
        "allowed_lengths": ["45 sec", "60 sec", "90 sec", "120 sec", "180 sec", "240 sec"],
        "niche_memory": "Renovation storytelling, homeowner mistakes, layout logic, home transformation, budget tension, property lifestyle",
        "page_direction": "Homes content should feel premium, useful, emotionally grounded, and specific enough to trigger saves and consultation intent.",
        "winning_formats": [
            "renovation mistake",
            "before vs after transformation",
            "hidden cost reveal",
            "layout problem solved",
            "homeowner regret story",
            "walkthrough with practical logic",
        ],
        "viral_now": [
            "renovation regrets",
            "homeowner tension hooks",
            "smart layout reveal reels",
            "emotional transformation walkthroughs",
        ],
        "rising_next": [
            "budget mistake breakdown",
            "small-space transformation storytelling",
            "what nobody tells you before renovating in Singapore",
            "visual walkthrough + practical narration hybrids",
        ],
        "competitor_patterns": [
            "best renovation reels reveal the payoff quickly",
            "visual beauty alone is weaker than decision-led tension",
            "specific homeowner pain beats generic home tour content",
            "strong save-worthy content frames a mistake, regret, or solution",
        ],
    },
    "Koocester Foodie Singapore": {
        "internal_key": "foodie",
        "audience": "Singapore food lovers, cafe hoppers, discovery audience, social diners, value-conscious food audience",
        "lead_type": "Discovery engagement audience, food discovery leads, location traffic audience",
        "tone": "Emotional",
        "default_goal": "Engagement",
        "recommended_mode": "Fast Visual Storytelling",
        "recommended_length": "60 sec",
        "allowed_lengths": ["15 sec", "30 sec", "45 sec", "60 sec", "90 sec", "120 sec"],
        "niche_memory": "Food discovery, hidden gems, satisfying visual content, first-bite reactions, value framing, social dining lifestyle",
        "page_direction": "Foodie content should feel highly watchable, satisfying, saveable, and relevant to Singapore dining culture.",
        "winning_formats": [
            "worth it or not",
            "price-to-value reveal",
            "first bite reaction",
            "hidden gem discovery",
            "cheap vs expensive",
            "queue-worthy verdict",
        ],
        "viral_now": [
            "price-based food hooks",
            "first bite payoff clips",
            "hidden gem reels with quick verdict",
            "satisfying close-up edit sequences",
        ],
        "rising_next": [
            "honest hype-check food reels",
            "three-second visual payoff openings",
            "dish-by-dish verdict carousels turned into reels",
            "taste tension with quick emotional commentary",
        ],
        "competitor_patterns": [
            "best foodie reels answer is-it-worth-it quickly",
            "food texture shots must arrive early",
            "money angle performs strongly in Singapore",
            "caption and on-screen text should stay simple and verdict-driven",
        ],
    },
}


def get_page_intelligence(page_name: str) -> Dict[str, Any]:
    return PAGE_INTELLIGENCE[page_name]


# --------------------------------------------------
# VIRAL INTELLIGENCE / TREND LAYER (NO ACCOUNT ACCESS)
# --------------------------------------------------
def build_public_intelligence_summary(page_data: Dict[str, Any], platform: str) -> str:
    platform_now = []
    platform_next = []

    if platform == "Instagram":
        platform_now = [
            "cleaner premium edit structures",
            "strong opening statement in first 1-2 seconds",
            "save-worthy educational framing",
            "high-contrast captions with fast readability",
        ]
        platform_next = [
            "micro-documentary style reels",
            "storytelling with earlier payoff reveals",
            "identity-based hooks for niche audiences",
            "faster clarity in first 3 seconds",
        ]
    else:
        platform_now = [
            "harder hooks in first second",
            "rawer tension-driven opening lines",
            "comment-bait opinions",
            "pattern interrupts every few seconds",
        ]
        platform_next = [
            "mini-story confession formats",
            "POV + decision tension",
            "one strong belief/opinion format",
            "high-rewatch payoff structures",
        ]

    lines = [
        f"Market focus: Singapore only.",
        f"Page direction memory: {page_data['page_direction']}",
        f"Known page niche: {page_data['niche_memory']}",
        f"Known audience: {page_data['audience']}",
        "Viral now for this page path: " + ", ".join(page_data["viral_now"]),
        "Likely rising next for this page path: " + ", ".join(page_data["rising_next"]),
        "Competitor-style patterns in same niche: " + ", ".join(page_data["competitor_patterns"]),
        f"Current {platform} format signals: " + ", ".join(platform_now),
        f"Likely next {platform} format signals: " + ", ".join(platform_next),
    ]
    return "\n".join(f"- {line}" for line in lines)


# --------------------------------------------------
# PROMPTS
# --------------------------------------------------
def build_master_prompt(
    page_name: str,
    page_data: Dict[str, Any],
    platform: str,
    market: str,
    role_mode: str,
    pain_point: str,
    offer: str,
    goal: str,
    video_length: str,
    tone: str,
    uploaded_context: str,
    scenario: str,
    producer_goal: str,
    raw_questions: str,
    sourcing_notes: str,
    competitor_notes: str,
    manual_context: str,
    intelligence_summary: str,
) -> str:
    role_block = (
        "Prioritize what to shoot, who to shoot, how to structure scenes, what questions to ask, and what producer decisions increase virality."
        if role_mode == "Producer"
        else "Prioritize hooks, caption logic, on-screen text, scripting, wording, CTA language, and copy refinement."
    )

    return f"""
You are an ELITE Singapore-first viral content strategist, retention expert, storyboard architect, platform analyst, content planner, and conversion-focused strategist for Koocester.

You are not generating from scratch blindly.
You already know the selected page's content path, audience, tone, niche memory, likely viral directions, and same-niche competitor-style patterns.

==================================================
SYSTEM MODE
==================================================

Selected Page: {page_name}
Internal Page Direction: {page_data['page_direction']}
Known Niche Memory: {page_data['niche_memory']}
Known Audience: {page_data['audience']}
Known Lead Type: {page_data['lead_type']}
Market: {market}
Platform: {platform}
Role Mode: {role_mode}
Role Priority: {role_block}
Goal: {goal}
Tone: {tone}
Video Length: {video_length}
Producer Goal: {producer_goal}
Offer / CTA: {offer}
Pain Point: {pain_point}
Scenario: {scenario if scenario.strip() else 'No specific scenario provided.'}
Raw Questions: {raw_questions if raw_questions.strip() else 'No raw questions provided.'}
Sourcing Notes: {sourcing_notes if sourcing_notes.strip() else 'No sourcing notes provided.'}
Competitor / Trend Notes: {competitor_notes if competitor_notes.strip() else 'No manual competitor notes provided.'}
Extra Manual Context: {manual_context if manual_context.strip() else 'No extra context provided.'}

==================================================
PUBLIC INTELLIGENCE LAYER
==================================================

{intelligence_summary}

Rules:
- Singapore only. Do not default to Malaysia.
- Stay inside the same brand path and niche direction as the selected page.
- Improve the page's content direction; do not replace it with random unrelated ideas.
- Use competitor-style intelligence as inspiration, not copying.
- Distinguish clearly between:
  1. Viral Now
  2. Likely To Go Viral Next
  3. Same-Niche Competitor Opportunity
- Be realistic and practical.
- No generic filler logic.

==================================================
UPLOADED FILE CONTEXT
==================================================

Uploaded files:
{uploaded_context}

Use uploaded files only if relevant.

==================================================
OUTPUT FORMAT
==================================================

Return in this exact structure:

1. PAGE INTELLIGENCE SUMMARY
- summarize the page identity, niche, audience, and content path
- explain what the page should keep doing
- explain what should improve

2. VIRAL NOW (SINGAPORE + SELECTED PLATFORM)
- 5 strong current content directions
- why they are working now
- what makes them platform-correct

3. LIKELY TO GO VIRAL NEXT
- 5 rising content directions
- why these are rising
- what signal suggests they may grow next

4. SAME-NICHE COMPETITOR OPPORTUNITIES
- what similar niche pages are doing well conceptually
- what Koocester can do in the same direction but better
- what gap Koocester can fill

5. 7 BEST VIDEO IDEAS FOR THIS PAGE
For each idea include:
- Hook
- Type
- Concept
- Video Format
- Why It Will Work
- Viewer Expectation
- Content Requirement
- Lead Intent
- Why It Matches This Page

6. BEST IDEA
- explain in depth why this is strongest for this page, this platform, this market, and this role mode

7. RETENTION ENGINE
- Hook
- Pattern Interrupt
- Open Loop
- Payoff
- CTA Placement
- Content Expectation
- Retention Risk

8. FULL STORYBOARD
For each scene include:
- Scene Objective
- Visual
- Shot Type
- Movement
- Hook / Retention Trigger
- Audio / Dialogue
- On-Screen Text
- Transition Logic
- Why This Scene Matters

9. ROLE-SPECIFIC OUTPUT
If role = Producer:
- what footage is needed
- who should be on camera
- what energy is needed
- what questions should be asked
- what to avoid while filming

If role = Copywriter:
- best hook rewrites
- best caption structure
- best CTA language
- on-screen text suggestions
- wording upgrades

10. VIDEO SCRIPT WITH DIALOGUE
- Opening Line
- Host Dialogue
- Supporting Dialogue / Narration
- Scene-by-Scene Script
- On-Screen Text
- Closing CTA Dialogue

11. VIRALITY ESTIMATE
- Viral Potential Score (0-100)
- Hook Strength Score
- Retention Strength Score
- Save/Share Potential
- DM/Lead Potential
- Realistic Performance Expectation
- Why it may underperform
- What needs to improve

12. CAPTION SUGGESTIONS
- Caption Option 1
- Caption Option 2
- Caption Option 3
- Which is strongest and why

13. CTA
- Do not generate CTA options here
- CTA will be handled separately by the system
""".strip()


def build_draft_review_prompt(
    page_name: str,
    page_data: Dict[str, Any],
    platform: str,
    market: str,
    role_mode: str,
    goal: str,
    tone: str,
    scenario: str,
    draft_video_idea: str,
    draft_cta: str,
    draft_caption: str,
    intelligence_summary: str,
) -> str:
    return f"""
You are an ELITE Singapore-first viral content reviewer for Koocester.

Selected Page: {page_name}
Page Direction: {page_data['page_direction']}
Known Niche: {page_data['niche_memory']}
Known Audience: {page_data['audience']}
Platform: {platform}
Market: {market}
Role Mode: {role_mode}
Goal: {goal}
Tone: {tone}
Scenario: {scenario if scenario.strip() else 'No scenario provided.'}

Public Intelligence Summary:
{intelligence_summary}

User's Draft Video Idea:
{draft_video_idea}

User's Draft CTA:
{draft_cta}

User's Draft Caption:
{draft_caption}

Review Rules:
- judge whether it matches the page's actual direction
- judge whether it fits Singapore and the selected platform
- judge whether it is better than generic content
- be honest and specific

Return in this exact structure:
1. DRAFT REVIEW SUMMARY
2. VIDEO IDEA SCORE
3. WHAT IS WRONG
4. WHAT IS WORKING
5. IMPROVED VIDEO IDEA
6. IMPROVED CTA
7. IMPROVED CAPTION
8. VIRALITY ESTIMATE
9. FINAL RECOMMENDATION
""".strip()


def build_idea_review_prompt(
    page_name: str,
    page_data: Dict[str, Any],
    platform: str,
    market: str,
    role_mode: str,
    goal: str,
    tone: str,
    scenario: str,
    draft_video_idea: str,
    draft_script: str,
    draft_cta: str,
    draft_caption: str,
    intelligence_summary: str,
) -> str:
    return f"""
You are an ELITE Singapore-first viral content reviewer and script critic for Koocester.

Selected Page: {page_name}
Page Direction: {page_data['page_direction']}
Known Niche: {page_data['niche_memory']}
Known Audience: {page_data['audience']}
Platform: {platform}
Market: {market}
Role Mode: {role_mode}
Goal: {goal}
Tone: {tone}
Scenario: {scenario if scenario.strip() else 'No scenario provided.'}

Public Intelligence Summary:
{intelligence_summary}

Submitted Video Idea:
{draft_video_idea}

Submitted Script:
{draft_script}

Submitted CTA:
{draft_cta}

Submitted Caption:
{draft_caption}

Rules:
- be honest
- do not flatter weak content
- judge whether this stays in the same page path but stronger
- judge whether it fits Singapore and the selected platform

Return in this exact structure:
1. OVERALL VERDICT
2. SCORES OUT OF 5
3. WHAT IS GOOD
4. WHAT IS WEAK
5. REMARKS
6. IMPROVEMENT SUGGESTIONS
7. IMPROVED VIDEO IDEA
8. IMPROVED SCRIPT
9. IMPROVED CTA
10. IMPROVED CAPTIONS
""".strip()


# --------------------------------------------------
# OPENAI CALLS
# --------------------------------------------------
def generate_strategy(
    page_name: str,
    page_data: Dict[str, Any],
    platform: str,
    market: str,
    role_mode: str,
    pain_point: str,
    offer: str,
    goal: str,
    video_length: str,
    tone: str,
    uploaded_context: str,
    scenario: str,
    producer_goal: str,
    raw_questions: str,
    sourcing_notes: str,
    competitor_notes: str,
    manual_context: str,
    intelligence_summary: str,
    model: str = DEFAULT_MODEL,
) -> str:
    client = get_client()
    prompt = build_master_prompt(
        page_name=page_name,
        page_data=page_data,
        platform=platform,
        market=market,
        role_mode=role_mode,
        pain_point=pain_point,
        offer=offer,
        goal=goal,
        video_length=video_length,
        tone=tone,
        uploaded_context=uploaded_context,
        scenario=scenario,
        producer_goal=producer_goal,
        raw_questions=raw_questions,
        sourcing_notes=sourcing_notes,
        competitor_notes=competitor_notes,
        manual_context=manual_context,
        intelligence_summary=intelligence_summary,
    )
    response = client.responses.create(model=model, input=prompt)
    return response.output_text


def review_submitted_draft(
    page_name: str,
    page_data: Dict[str, Any],
    platform: str,
    market: str,
    role_mode: str,
    goal: str,
    tone: str,
    scenario: str,
    draft_video_idea: str,
    draft_cta: str,
    draft_caption: str,
    intelligence_summary: str,
    model: str = DEFAULT_MODEL,
) -> str:
    client = get_client()
    prompt = build_draft_review_prompt(
        page_name=page_name,
        page_data=page_data,
        platform=platform,
        market=market,
        role_mode=role_mode,
        goal=goal,
        tone=tone,
        scenario=scenario,
        draft_video_idea=draft_video_idea,
        draft_cta=draft_cta,
        draft_caption=draft_caption,
        intelligence_summary=intelligence_summary,
    )
    response = client.responses.create(model=model, input=prompt)
    return response.output_text


def review_idea_and_script(
    page_name: str,
    page_data: Dict[str, Any],
    platform: str,
    market: str,
    role_mode: str,
    goal: str,
    tone: str,
    scenario: str,
    draft_video_idea: str,
    draft_script: str,
    draft_cta: str,
    draft_caption: str,
    intelligence_summary: str,
    model: str = DEFAULT_MODEL,
) -> str:
    client = get_client()
    prompt = build_idea_review_prompt(
        page_name=page_name,
        page_data=page_data,
        platform=platform,
        market=market,
        role_mode=role_mode,
        goal=goal,
        tone=tone,
        scenario=scenario,
        draft_video_idea=draft_video_idea,
        draft_script=draft_script,
        draft_cta=draft_cta,
        draft_caption=draft_caption,
        intelligence_summary=intelligence_summary,
    )
    response = client.responses.create(model=model, input=prompt)
    return response.output_text


# --------------------------------------------------
# ADMIN ANALYTICS
# --------------------------------------------------
def render_admin_analytics() -> None:
    st.divider()
    st.subheader("📊 Admin Analytics")

    logs = read_recent_logs(limit=300)
    if not logs:
        st.info("No usage logs yet.")
        return

    total_events = len(logs)
    total_generations = sum(1 for row in logs if row["action_type"] == "generate")
    total_draft_reviews = sum(1 for row in logs if row["action_type"] == "draft_review")
    total_idea_script_reviews = sum(1 for row in logs if row["action_type"] == "idea_script_review")
    total_uploads = sum(row.get("uploaded_count", 0) or 0 for row in logs)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Events", total_events)
    c2.metric("Generations", total_generations)
    c3.metric("Draft Reviews", total_draft_reviews)
    c4.metric("Idea/Script Reviews", total_idea_script_reviews)
    c5.metric("Uploaded Files", total_uploads)

    st.markdown("### Recent Usage")
    for row in logs[:50]:
        with st.expander(
            f"{row['ts']} | {row.get('page', '-') or '-'} | {row['action_type']} | session {row['session_id'][:8]}"
        ):
            st.write(f"**Page:** {row.get('page', '-')} ")
            st.write(f"**Platform:** {row.get('platform', '-')} ")
            st.write(f"**Market:** {row.get('market', '-')} ")
            st.write(f"**Role Mode:** {row.get('role_mode', '-')} ")
            st.write(f"**Goal:** {row.get('goal', '-')} ")
            st.write(f"**Scenario:** {row.get('scenario', '-')} ")
            st.write(f"**Output chars:** {row.get('output_chars', 0)}")
            st.write(f"**Uploaded count:** {row.get('uploaded_count', 0)}")
            st.write(f"**Uploaded bytes:** {row.get('uploaded_total_bytes', 0)}")
            st.write(f"**Notes:** {row.get('notes', '')}")


# --------------------------------------------------
# CTA ENGINE
# --------------------------------------------------
def generate_cta_v10(
    goal: str,
    platform: str,
    page_name: str,
    pain_point: str,
    offer: str,
) -> Tuple[List[str], str, str]:
    category_keyword = {
        "Koocester Main": "KOOCESTER",
        "Koocester Business Singapore": "NETWORK",
        "Koocester Autos Singapore": "AUTO",
        "Koocester Homes Singapore": "HOME",
        "Koocester Foodie Singapore": "FOOD",
    }.get(page_name, "START")

    pain_part = pain_point.strip() if pain_point.strip() else "this"

    if goal == "Leads":
        ctas = [
            f"DM '{category_keyword}' if you're serious about {pain_part.lower()}.",
            f"Not for everyone — DM '{category_keyword}' if you actually want the next step.",
            f"If this sounds like you, DM '{category_keyword}' and we'll guide you from there.",
        ]
    elif goal == "Engagement":
        ctas = [
            "Be honest — would you actually agree with this?",
            "Comment your take below.",
            "Most people won't agree with this. Do you?",
        ]
    elif goal == "Views":
        ctas = [
            "Watch this again — you probably missed the real point.",
            "Most people don't catch this the first time.",
            "Wait till the end before you judge this.",
        ]
    else:
        ctas = [
            "Follow for more content like this.",
            "If this helped, there's more coming.",
            "Stay close — more soon.",
        ]

    if offer.strip():
        ctas[0] = f"{ctas[0]} {offer.strip()}."

    if platform == "TikTok":
        ctas = [cta.rstrip(".") + " 👇" for cta in ctas]

    best_cta = ctas[0]
    reasoning = "This CTA is strongest because it is direct, simple, and aligned with conversion behavior for short-form content."
    return ctas, best_cta, reasoning


# --------------------------------------------------
# UI
# --------------------------------------------------
st.title("🚀 Koocester SG Viral Intelligence Engine")
st.caption(
    "Singapore-first, page-aware viral intelligence for producers and copywriters. Same content path, stronger execution."
)

session_id = get_session_id()
render_admin_login()

left, right = st.columns([1.2, 0.8], gap="large")

with left:
    st.subheader("Viral Intelligence Brief")

    page_name = st.selectbox(
        "Koocester Page",
        [
            "Koocester Main",
            "Koocester Business Singapore",
            "Koocester Autos Singapore",
            "Koocester Homes Singapore",
            "Koocester Foodie Singapore",
        ],
    )
    page_data = get_page_intelligence(page_name)

    market = st.selectbox("Market", ["Singapore"], index=0)
    platform = st.selectbox("Platform", ["Instagram", "TikTok"])
    role_mode = st.selectbox("Mode", ["Producer", "Copywriter"])

    pain_point = st.text_input(
        "Pain Point / Problem To Solve",
        placeholder="e.g. weak hooks, low retention, generic event recap content, not enough strong Singapore angles",
    )
    offer = st.text_input(
        "Offer / CTA",
        placeholder="e.g. register, DM us, book consultation, visit the showroom, save this",
    )

    scenario = st.text_area(
        "Video Scenario / Situation",
        placeholder="e.g. We have event footage, founder interview clips, venue shots, networking moments, and want a stronger Singapore-first business reel.",
        height=130,
    )

    producer_goal = st.selectbox(
        "Producer Goal",
        [
            "General Content",
            "Find Viral Talent",
            "Interview-Based Content",
            "Lead Generation Content",
            "Brand Authority Content",
        ],
    )

    raw_questions = st.text_area(
        "Raw Interview / Storyboard Questions",
        placeholder="Paste current interview questions, producer prompts, or rough storyboard questions here...",
        height=130,
    )

    sourcing_notes = st.text_area(
        "Producer Sourcing Notes",
        placeholder="Describe who you want to source, what kind of people perform well, where producers struggle, or what type of footage is missing.",
        height=110,
    )

    competitor_notes = st.text_area(
        "Competitor / Trend Notes",
        placeholder="Paste notes on what similar niche pages are doing, strong hooks you noticed, rising formats, or anything you want AI to consider.",
        height=110,
    )

    manual_context = st.text_area(
        "Extra Manual Context",
        placeholder="Anything else the AI should know before generating.",
        height=90,
    )

    goal = st.selectbox("Goal", ["Views", "Engagement", "Leads", "Awareness"], index=["Views", "Engagement", "Leads", "Awareness"].index(page_data["default_goal"]))
    video_length = st.selectbox(
        "Video Length",
        page_data["allowed_lengths"],
        index=page_data["allowed_lengths"].index(page_data["recommended_length"]),
    )
    tone = st.selectbox("Tone", ["Premium", "Bold", "Educational", "Emotional", "Direct"], index=["Premium", "Bold", "Educational", "Emotional", "Direct"].index(page_data["tone"]))

    uploaded_files = st.file_uploader(
        "Upload supporting files (optional)",
        accept_multiple_files=True,
        type=None,
        help="Upload scripts, decks, notes, references, or anything useful for generation.",
    )

    st.divider()
    st.subheader("Draft Review")

    draft_video_idea = st.text_area(
        "Draft Video Idea",
        placeholder="Paste your draft video idea here...",
        height=120,
    )
    draft_cta = st.text_input("Draft CTA", placeholder="e.g. DM us / Register now / Save this")
    draft_caption = st.text_area("Draft Caption", placeholder="Paste your draft caption here...", height=100)

    st.divider()
    st.subheader("Idea / Script Review")

    review_video_idea = st.text_area("Your Video Idea", placeholder="Paste your idea here...", height=100)
    review_script = st.text_area("Your Draft Script", placeholder="Paste your script here...", height=170)
    review_cta = st.text_input("Your Draft CTA", placeholder="e.g. DM us / Register now")
    review_caption = st.text_area("Your Draft Caption", placeholder="Paste your draft caption here...", height=100)

    c1, c2, c3 = st.columns(3)
    with c1:
        generate = st.button("Build Viral Intelligence", use_container_width=True)
    with c2:
        review_draft_btn = st.button("Rate & Improve Draft", use_container_width=True)
    with c3:
        review_idea_btn = st.button("Rate My Idea / Script", use_container_width=True)

with right:
    st.subheader("Page Intelligence Preview")
    st.write(f"**Selected Page:** {page_name}")
    st.write(f"**Market:** {market}")
    st.write(f"**Platform:** {platform}")
    st.write(f"**Mode:** {role_mode}")
    st.write(f"**Known Audience:** {page_data['audience']}")
    st.write(f"**Known Lead Type:** {page_data['lead_type']}")
    st.write(f"**Known Niche Path:** {page_data['niche_memory']}")
    st.write(f"**Recommended Mode:** {page_data['recommended_mode']}")
    st.write(f"**Recommended Length:** {page_data['recommended_length']}")
    st.write(f"**Selected Length:** {video_length}")
    st.write(f"**Tone:** {tone}")
    st.write(f"**Goal:** {goal}")

    st.divider()
    st.subheader("Viral Now")
    for item in page_data["viral_now"]:
        st.write(f"- {item}")

    st.subheader("Likely Next")
    for item in page_data["rising_next"]:
        st.write(f"- {item}")

    st.subheader("Same-Niche Competitor Patterns")
    for item in page_data["competitor_patterns"]:
        st.write(f"- {item}")

    uploaded_context, uploaded_files_json, uploaded_count, uploaded_total_bytes = summarize_uploaded_files(uploaded_files)
    st.divider()
    st.subheader("Upload Summary")
    st.write(f"**Files uploaded:** {uploaded_count}")
    st.write(f"**Total size (bytes):** {uploaded_total_bytes}")
    if uploaded_count:
        st.code(uploaded_context, language="text")

intelligence_summary = build_public_intelligence_summary(page_data, platform)

st.divider()
st.subheader("Public Intelligence Layer")
st.code(intelligence_summary, language="text")

st.divider()
st.subheader("Master Prompt Preview")
master_prompt = build_master_prompt(
    page_name=page_name,
    page_data=page_data,
    platform=platform,
    market=market,
    role_mode=role_mode,
    pain_point=pain_point,
    offer=offer,
    goal=goal,
    video_length=video_length,
    tone=tone,
    uploaded_context=uploaded_context,
    scenario=scenario,
    producer_goal=producer_goal,
    raw_questions=raw_questions,
    sourcing_notes=sourcing_notes,
    competitor_notes=competitor_notes,
    manual_context=manual_context,
    intelligence_summary=intelligence_summary,
)
st.code(master_prompt, language="text")


# --------------------------------------------------
# GENERATE MAIN STRATEGY
# --------------------------------------------------
if generate:
    missing: List[str] = []
    if not offer.strip():
        missing.append("Offer / CTA")
    if not pain_point.strip():
        missing.append("Pain Point / Problem To Solve")

    ip_value, ip_source = get_ip_if_available()
    user_agent = get_user_agent()

    if missing:
        insert_usage_log(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
                "page": page_name,
                "platform": platform,
                "market": market,
                "role_mode": role_mode,
                "niche": page_data["niche_memory"],
                "audience": page_data["audience"],
                "lead_type": page_data["lead_type"],
                "pain_point": pain_point,
                "offer": offer,
                "goal": goal,
                "video_length": video_length,
                "tone": tone,
                "scenario": scenario,
                "action_type": "validation_error",
                "output_chars": 0,
                "user_agent": user_agent,
                "uploaded_files_json": uploaded_files_json,
                "uploaded_total_bytes": uploaded_total_bytes,
                "uploaded_count": uploaded_count,
                "ip_value": ip_value,
                "ip_source": ip_source,
                "notes": "Missing required fields",
            }
        )
        st.error("Please fill in: " + ", ".join(missing))
    else:
        try:
            with st.spinner("Building Singapore-first viral intelligence..."):
                output = generate_strategy(
                    page_name=page_name,
                    page_data=page_data,
                    platform=platform,
                    market=market,
                    role_mode=role_mode,
                    pain_point=pain_point,
                    offer=offer,
                    goal=goal,
                    video_length=video_length,
                    tone=tone,
                    uploaded_context=uploaded_context,
                    scenario=scenario,
                    producer_goal=producer_goal,
                    raw_questions=raw_questions,
                    sourcing_notes=sourcing_notes,
                    competitor_notes=competitor_notes,
                    manual_context=manual_context,
                    intelligence_summary=intelligence_summary,
                    model=DEFAULT_MODEL,
                )

            insert_usage_log(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "page": page_name,
                    "platform": platform,
                    "market": market,
                    "role_mode": role_mode,
                    "niche": page_data["niche_memory"],
                    "audience": page_data["audience"],
                    "lead_type": page_data["lead_type"],
                    "pain_point": pain_point,
                    "offer": offer,
                    "goal": goal,
                    "video_length": video_length,
                    "tone": tone,
                    "scenario": scenario,
                    "action_type": "generate",
                    "output_chars": len(output or ""),
                    "user_agent": user_agent,
                    "uploaded_files_json": uploaded_files_json,
                    "uploaded_total_bytes": uploaded_total_bytes,
                    "uploaded_count": uploaded_count,
                    "ip_value": ip_value,
                    "ip_source": ip_source,
                    "notes": intelligence_summary[:1000],
                }
            )

            st.divider()
            st.subheader("Generated Viral Intelligence")
            st.markdown(output)

            cta_options, best_cta, reasoning = generate_cta_v10(
                goal=goal,
                platform=platform,
                page_name=page_name,
                pain_point=pain_point,
                offer=offer,
            )

            st.divider()
            st.subheader("🚀 CTA Engine")
            st.markdown("### CTA Options")
            for i, cta in enumerate(cta_options, 1):
                st.write(f"{i}. {cta}")

            st.markdown("### ⭐ Best CTA")
            st.success(best_cta)

            st.markdown("### 🧠 Why This Works")
            st.write(reasoning)

        except Exception as e:
            insert_usage_log(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "page": page_name,
                    "platform": platform,
                    "market": market,
                    "role_mode": role_mode,
                    "niche": page_data["niche_memory"],
                    "audience": page_data["audience"],
                    "lead_type": page_data["lead_type"],
                    "pain_point": pain_point,
                    "offer": offer,
                    "goal": goal,
                    "video_length": video_length,
                    "tone": tone,
                    "scenario": scenario,
                    "action_type": "generation_error",
                    "output_chars": 0,
                    "user_agent": user_agent,
                    "uploaded_files_json": uploaded_files_json,
                    "uploaded_total_bytes": uploaded_total_bytes,
                    "uploaded_count": uploaded_count,
                    "ip_value": ip_value,
                    "ip_source": ip_source,
                    "notes": str(e),
                }
            )
            st.error(str(e))


# --------------------------------------------------
# REVIEW DRAFT
# --------------------------------------------------
if review_draft_btn:
    review_missing: List[str] = []
    if not draft_video_idea.strip():
        review_missing.append("Draft Video Idea")
    if not draft_cta.strip():
        review_missing.append("Draft CTA")
    if not draft_caption.strip():
        review_missing.append("Draft Caption")

    if review_missing:
        st.error("Please fill in: " + ", ".join(review_missing))
    else:
        try:
            with st.spinner("Reviewing and improving draft..."):
                review_output = review_submitted_draft(
                    page_name=page_name,
                    page_data=page_data,
                    platform=platform,
                    market=market,
                    role_mode=role_mode,
                    goal=goal,
                    tone=tone,
                    scenario=scenario,
                    draft_video_idea=draft_video_idea,
                    draft_cta=draft_cta,
                    draft_caption=draft_caption,
                    intelligence_summary=intelligence_summary,
                    model=DEFAULT_MODEL,
                )

            st.divider()
            st.subheader("Draft Review Result")
            st.markdown(review_output)
        except Exception as e:
            st.error(str(e))


# --------------------------------------------------
# REVIEW IDEA / SCRIPT
# --------------------------------------------------
if review_idea_btn:
    missing_review: List[str] = []
    if not review_video_idea.strip():
        missing_review.append("Your Video Idea")
    if not review_script.strip():
        missing_review.append("Your Draft Script")
    if not review_cta.strip():
        missing_review.append("Your Draft CTA")
    if not review_caption.strip():
        missing_review.append("Your Draft Caption")

    if missing_review:
        st.error("Please fill in: " + ", ".join(missing_review))
    else:
        try:
            with st.spinner("Reviewing your idea and script..."):
                reviewed_output = review_idea_and_script(
                    page_name=page_name,
                    page_data=page_data,
                    platform=platform,
                    market=market,
                    role_mode=role_mode,
                    goal=goal,
                    tone=tone,
                    scenario=scenario,
                    draft_video_idea=review_video_idea,
                    draft_script=review_script,
                    draft_cta=review_cta,
                    draft_caption=review_caption,
                    intelligence_summary=intelligence_summary,
                    model=DEFAULT_MODEL,
                )

            st.divider()
            st.subheader("Idea / Script Review Result")
            st.markdown(reviewed_output)
        except Exception as e:
            st.error(str(e))


if is_admin():
    render_admin_analytics()

st.divider()
st.caption(
    "Final file: Singapore-first, page-aware viral intelligence engine with producer/copywriter mode, draft review, idea/script review, analytics, and CTA engine."
)
