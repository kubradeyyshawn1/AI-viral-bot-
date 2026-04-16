import os
import json
import uuid
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import streamlit as st
from openai import OpenAI


st.set_page_config(
    page_title="Koocester Viral Content Engine",
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
            ts, session_id, page, platform, niche, audience, lead_type,
            pain_point, offer, goal, video_length, tone, scenario, action_type,
            output_chars, user_agent, uploaded_files_json,
            uploaded_total_bytes, uploaded_count, ip_value, ip_source, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.get("ts"),
            payload.get("session_id"),
            payload.get("page"),
            payload.get("platform"),
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
- Malaysia-first relevance
- page-specific output
- stronger hooks
- higher retention
- better leads
- complete storyboard
- script + dialogue
- auto-optimized video length
- stronger CTA generation
- deeper content reasoning
- scenario-based virality estimate
- caption suggestion engine
- draft review and correction
- idea/script rating
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
# PAGE RULES
# --------------------------------------------------
PAGE_LENGTH_RULES = {
    "Homes": {
        "recommended_mode": "Long Visual Storytelling",
        "recommended_length": "180 sec",
        "allowed_lengths": ["60 sec", "90 sec", "120 sec", "180 sec", "240 sec", "300 sec", "360 sec"],
        "reason": "Homes content often needs more explanation, tours, renovation logic, and trust-building, so longer storytelling works well.",
    },
    "Business": {
        "recommended_mode": "Authority + Retention",
        "recommended_length": "180 sec",
        "allowed_lengths": ["60 sec", "90 sec", "120 sec", "180 sec", "240 sec"],
        "reason": "Business content can go longer when it teaches, explains, or builds authority, but still needs retention throughout.",
    },
    "Autos": {
        "recommended_mode": "Extended Visual Storytelling",
        "recommended_length": "180 sec",
        "allowed_lengths": ["60 sec", "90 sec", "120 sec", "180 sec"],
        "reason": "Autos content can hold attention longer when it is cinematic, aspirational, feature-driven, and built around ownership experience.",
    },
    "Foodie": {
        "recommended_mode": "Fast Visual Storytelling",
        "recommended_length": "90 sec",
        "allowed_lengths": ["30 sec", "45 sec", "60 sec", "90 sec", "120 sec", "180 sec"],
        "reason": "Foodie content works best when it is visually satisfying, quick, emotionally driven, and easy to consume.",
    },
}


def get_length_settings(category: str) -> Dict[str, object]:
    return PAGE_LENGTH_RULES[category]


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
# MAIN GENERATOR PROMPT
# --------------------------------------------------
def build_master_prompt(
    category: str,
    platform: str,
    niche: str,
    audience: str,
    lead_type: str,
    pain_point: str,
    offer: str,
    goal: str,
    video_length: str,
    tone: str,
    recommended_mode: str,
    uploaded_context: str,
    scenario: str,
) -> str:
    return f"""
You are an ELITE viral content strategist, retention expert, storyboard architect, content planner, video scriptwriter, and conversion-focused CTA writer for Koocester.

Your job is to generate the BEST possible viral video ideas targeted for qualified leads, with complete storyboarding automation, full video structure, deeper reasoning, better content logic, platform-accurate virality expectations, and high-converting caption + CTA suggestions.

You must think like:
- viral strategist
- retention editor
- content planner
- hook writer
- scriptwriter
- storyboard planner
- lead generation strategist
- platform growth operator
- CTA conversion specialist

==================================================
CORE OBJECTIVE
==================================================

Generate content that:
1. gets views
2. improves retention
3. increases clicks, engagement, DMs, and leads
4. aligns with the SPECIFIC Koocester page selected
5. feels highly relevant to Malaysian audiences
6. can still appeal internationally
7. improves on Koocester’s current content style instead of replacing it with random ideas
8. is content-driven, not just idea-driven
9. includes realistic expectations for performance on the selected platform

==================================================
PAGE-SPECIFIC RULE
==================================================

Selected page: {category}

If page = Homes:
- only generate content related to renovation, interior design, home tours, homeowner pain points, layout, budgeting, property lifestyle
- do NOT generate business, auto, or foodie content

If page = Business:
- only generate content related to founders, entrepreneurship, networking, interviews, social proof, events, business lifestyle, growth insights
- do NOT generate home, auto, or foodie content

If page = Autos:
- only generate content related to cars, luxury lifestyle, aspiration, performance, buyer psychology, status, premium ownership experience
- do NOT generate homes, business, or foodie content

If page = Foodie:
- only generate content related to food experiences, restaurants, cafes, dishes, taste reactions, dining lifestyle, food discovery
- do NOT generate homes, business, or auto content

==================================================
TARGET AUDIENCE
==================================================

Audience / Lead Type: {lead_type}
Audience Details: {audience}
Pain Point: {pain_point}
Offer / CTA: {offer}
Goal: {goal}
Niche: {niche}
Scenario: {scenario if scenario.strip() else "No specific scenario provided."}

Primary region:
- Malaysia

Secondary:
- International appeal where suitable

==================================================
PLATFORM BEHAVIOR
==================================================

Platform: {platform}

Instagram:
- cleaner
- premium feel
- better for polished visuals and brand-safe storytelling
- retention depends on visual quality + clarity + save/share value
- virality should be estimated based on reel behavior, shareability, saves, comments, and premium appeal

TikTok:
- faster pacing
- sharper hooks
- more raw relatability
- virality should be estimated based on immediate hook strength, pattern interrupts, emotional payoff, comment bait, rewatch potential

You must tailor all ideas, scripts, captions, and virality estimates to the selected platform only.

==================================================
CONTENT LENGTH MODE
==================================================

Recommended mode for this page: {recommended_mode}
Video Length: {video_length}

If video length is 60 sec or below:
- aggressive hook in first 0–2 seconds
- fast pacing
- minimal filler
- rapid payoff
- high visual retention

If video length is 75–120 sec:
- strong hook in first 0–3 seconds
- deeper explanation
- include at least 1 mid-video hook
- use pattern interrupts
- maintain narrative logic

If video length is 180–240 sec:
- strong opening hook in first 0–5 seconds
- multiple retention checkpoints
- clear narrative flow
- stronger content depth
- layered payoff

If video length is 300–360 sec:
- use chapter-like structure
- introduce mini-hooks throughout the video
- keep energy changing across scenes
- avoid filler
- use deep storytelling and meaningful progression

==================================================
RETENTION RULES
==================================================

Every best-performing output MUST include:

1. HOOK
2. PATTERN INTERRUPT
3. OPEN LOOP
4. PAYOFF
5. CTA
6. CONTENT EXPECTATION

Content expectation means:
- explain what the viewer expects to receive from the video
- explain whether the idea is strong enough to satisfy that expectation
- explain where retention may drop if execution is weak

==================================================
HIGH-CONVERTING CTA ENGINE
==================================================

CTA must:
- match the goal exactly
- feel natural, not overly salesy
- create urgency, curiosity, or direct action
- be short and punchy
- be practical for the selected page and platform
- work for Malaysian audience behavior

==================================================
UPLOADED FILE CONTEXT
==================================================

Uploaded files:
{uploaded_context}

Use uploaded files only if relevant.

==================================================
OUTPUT QUALITY RULE
==================================================

Do NOT be vague.
Do NOT give generic “this works because it is engaging” reasoning.

For every important section:
- explain the reasoning clearly
- explain the expected viewer psychology
- explain the realistic performance conditions
- explain what content quality is required for the video to actually perform well

==================================================
OUTPUT FORMAT
==================================================

Return in this exact structure:

1. CONTENT STRATEGY GAP
- explain what is currently weak or missing
- make it longer, specific, and content-driven
- explain what type of content is underperforming and why

2. 7 VIRAL VIDEO IDEAS
For each idea include:
- Hook
- Type
- Concept
- Video Format
- Why It Will Work
- Viewer Expectation
- Content Requirement
- Lead Intent

Make each idea more detailed and sensible.

3. BEST IDEA
- explain in depth why this is strongest for views + retention + clicks + leads
- explain why it fits the selected page
- explain what kind of execution quality it needs

4. RETENTION ENGINE
- Hook
- Pattern Interrupt
- Open Loop
- Payoff
- CTA Placement
- Content Expectation
- Retention Risk

5. FULL STORYBOARD
For each scene include:
- Visual
- Shot Direction
- Purpose
- Audio/Dialogue
- On-Screen Text
- Why This Scene Matters

Make scenes content-driven, not just visual.

6. VIDEO SCRIPT WITH DIALOGUE
- Opening Line
- Host Dialogue
- Supporting Dialogue / Narration
- Scene-by-Scene Script
- On-Screen Text
- Closing CTA Dialogue

Make script longer, more natural, more sensible, and more practical to film.

7. VIRALITY ESTIMATE
Based ONLY on the selected platform, estimate:
- Viral Potential Score (0-100)
- Hook Strength Score
- Retention Strength Score
- Save/Share Potential
- DM/Lead Potential
- Realistic Performance Expectation
- Why it may underperform
- What needs to be improved for stronger virality

Do NOT guarantee virality.
Be realistic.

8. CAPTION SUGGESTIONS
Give:
- Caption Option 1
- Caption Option 2
- Caption Option 3
- Which caption is strongest and why

9. CTA OPTIONS
- CTA Option 1
- CTA Option 2
- CTA Option 3

==================================================
FINAL INSTRUCTIONS
==================================================

Make sure the output is:
- page-specific
- platform-specific
- Malaysia-first
- content-driven
- deeper than generic idea generation
- logically reasoned
- realistic
- practical enough to actually produce
""".strip()


# --------------------------------------------------
# DRAFT REVIEW PROMPT
# --------------------------------------------------
def build_draft_review_prompt(
    category: str,
    platform: str,
    audience: str,
    lead_type: str,
    goal: str,
    tone: str,
    scenario: str,
    draft_video_idea: str,
    draft_cta: str,
    draft_caption: str,
) -> str:
    return f"""
You are an ELITE viral content reviewer, content strategist, script optimizer, CTA critic, caption optimizer, and platform-specific viral analyst for Koocester.

Your task is to REVIEW and IMPROVE the user's submitted draft.

==================================================
CONTEXT
==================================================

Selected Page: {category}
Platform: {platform}
Audience: {audience}
Lead Type: {lead_type}
Goal: {goal}
Tone: {tone}
Scenario: {scenario if scenario.strip() else "No scenario provided."}

User's Draft Video Idea:
{draft_video_idea}

User's Draft CTA:
{draft_cta}

User's Draft Caption:
{draft_caption}

==================================================
REVIEW OBJECTIVE
==================================================

You must:
1. Judge how strong the submitted video idea is for the selected platform
2. Judge whether it matches the selected page
3. Judge whether the CTA is strong enough
4. Judge whether the caption helps or weakens the content
5. Identify mistakes, weak logic, weak hooks, generic phrasing, poor retention logic, weak audience targeting, poor lead intention, weak CTA structure, and weak caption writing
6. Improve everything
7. Give better viral suggestions

==================================================
PLATFORM-SPECIFIC REVIEW
==================================================

If platform = Instagram:
- judge based on reel appeal, polish, clarity, save/share value, comment potential, premium feel, and whether it matches Instagram viewer behavior

If platform = TikTok:
- judge based on hook speed, raw relatability, pattern interrupts, comment bait, rewatch potential, and whether it matches TikTok viewer behavior

==================================================
OUTPUT FORMAT
==================================================

Return in this exact structure:

1. DRAFT REVIEW SUMMARY
- Overall quality verdict
- Is it strong or weak and why

2. VIDEO IDEA SCORE
- Score out of 100
- Hook strength
- Retention strength
- Lead generation strength
- Platform fit
- Page fit

3. WHAT IS WRONG
- List specific mistakes
- Explain what feels weak, vague, generic, confusing, or not viral enough

4. WHAT IS WORKING
- Explain what should be kept

5. IMPROVED VIDEO IDEA
- Rewrite the idea into a stronger version
- Make it more content-driven
- Make it more scroll-stopping
- Make it more aligned to the selected page and platform

6. IMPROVED CTA
- Rewrite CTA
- Give 3 better CTA options
- Explain which CTA is strongest and why

7. IMPROVED CAPTION
- Rewrite caption
- Give 3 better caption options
- Explain which caption is strongest and why

8. VIRALITY ESTIMATE
- Viral Potential Score (0-100)
- Why it may perform
- Why it may fail
- What needs to happen in execution for it to work

9. FINAL RECOMMENDATION
- Should they use this idea as-is?
- Should they improve it?
- Should they scrap it and use the improved version instead?
""".strip()


# --------------------------------------------------
# IDEA / SCRIPT REVIEW PROMPT
# --------------------------------------------------
def build_idea_review_prompt(
    category: str,
    platform: str,
    audience: str,
    lead_type: str,
    goal: str,
    tone: str,
    scenario: str,
    draft_video_idea: str,
    draft_script: str,
    draft_cta: str,
    draft_caption: str,
) -> str:
    return f"""
You are an ELITE viral content reviewer, script critic, hook analyst, CTA reviewer, and caption optimizer for Koocester.

Your job is to REVIEW a user's submitted draft idea and script honestly, score it out of 5, explain what is weak, explain what is working, and improve it.

==================================================
CONTEXT
==================================================

Selected Page: {category}
Platform: {platform}
Audience: {audience}
Lead Type: {lead_type}
Goal: {goal}
Tone: {tone}
Scenario: {scenario if scenario.strip() else "No scenario provided."}

Submitted Video Idea:
{draft_video_idea}

Submitted Script:
{draft_script}

Submitted CTA:
{draft_cta}

Submitted Caption:
{draft_caption}

==================================================
REVIEW RULES
==================================================

Be honest.
Do not flatter weak content.
If something is weak, explain exactly why.

Judge using:
- hook strength
- clarity
- retention logic
- content value
- lead generation strength
- CTA quality
- caption strength
- platform fit
- page fit

If platform = Instagram:
- judge based on reel polish, save/share value, premium feel, retention, comment potential

If platform = TikTok:
- judge based on hook speed, relatability, comment bait, rewatch potential, retention pacing

==================================================
OUTPUT FORMAT
==================================================

1. OVERALL VERDICT
- Short summary of whether the idea is strong, average, or weak

2. SCORES OUT OF 5
- Idea Rating: x/5
- Script Rating: x/5
- Hook Rating: x/5
- CTA Rating: x/5
- Caption Rating: x/5
- Platform Fit Rating: x/5

3. WHAT IS GOOD
- Bullet points

4. WHAT IS WEAK
- Bullet points
- Explain what feels generic, boring, confusing, or weak

5. REMARKS
- Honest remarks on how usable this is in current form

6. IMPROVEMENT SUGGESTIONS
- Practical suggestions to improve hook, script, CTA, caption, retention, and virality

7. IMPROVED VIDEO IDEA
- Rewrite the idea stronger
- Make it more content-driven and platform-suitable

8. IMPROVED SCRIPT
- Rewrite the script stronger
- Make it sound more natural, clearer, more viral, and more useful

9. IMPROVED CTA
- Give 3 better CTA options

10. IMPROVED CAPTIONS
- Give 3 better caption options
- Explain which one is strongest and why
""".strip()


# --------------------------------------------------
# SAMPLE OUTPUTS
# --------------------------------------------------
def get_sample_outputs(category: str) -> dict:
    base = {
        "Homes": {
            "gap": [
                "Homes content often looks visually appealing but may underperform when it focuses too much on surface-level beauty without enough homeowner tension, decision-making pressure, budgeting logic, or post-renovation regret framing.",
                "For stronger performance, the content should shift from 'nice-looking renovation content' into 'decision-driven homeowner content' where viewers feel the stakes, the mistakes, and the payoff more clearly.",
            ],
            "ideas": [
                {
                    "hook": "Most Malaysians get this wrong before renovating.",
                    "type": "Mistake",
                    "concept": "Break down one high-cost renovation mistake that looks small at first but causes long-term regret.",
                    "format": "Premium host-led breakdown with real examples and supporting visual references.",
                    "why": "It hits a direct homeowner fear, creates immediate relevance, and gives the viewer a clear reason to stay until the explanation and payoff.",
                    "expectation": "The viewer expects a real mistake with practical consequences and a better alternative.",
                    "requirement": "Needs specific examples, clean pacing, and enough proof to feel credible.",
                    "lead": "High",
                }
            ],
            "best": "Most Malaysians get this wrong before renovating.",
            "storyboard": [
                "Scene 1: Strong homeowner pain hook with premium visuals and immediate verbal tension.",
                "Scene 2: Show the common mistake and why people make it.",
                "Scene 3: Break down real consequence and emotional regret.",
                "Scene 4: Reveal smarter decision logic.",
                "Scene 5: End with useful CTA tied to planning support.",
            ],
            "script": [
                "Opening: Most Malaysians make this mistake before the renovation even starts.",
                "Host: People think renovation starts with design inspiration. It usually starts with decision errors.",
                "Narration: And those errors often cost more later than people expect.",
                "Host: If you want a renovation that looks good and works properly, you need to understand the order of decisions first.",
                "CTA: Save this before your renovation starts or send it to someone planning one.",
            ],
            "cta": {
                "on_screen": "Save this before your renovation starts.",
                "caption_cta": "DM 'HOME' and we’ll send you the full renovation breakdown.",
                "options": [
                    "DM 'HOME' and we’ll send you the full breakdown.",
                    "Save this before your next renovation decision.",
                    "Send this to someone planning a renovation."
                ]
            },
            "captions": [
                "One renovation mistake at the start can cost you more than most people expect.",
                "Before you choose finishes, understand this first.",
                "A beautiful renovation means nothing if the decision-making was wrong."
            ],
            "virality": [
                "Viral Potential Score: 76/100",
                "Hook Strength Score: 84/100",
                "Retention Strength Score: 73/100",
                "Save/Share Potential: High",
                "DM/Lead Potential: High",
                "Realistic Performance Expectation: Strong if the execution is specific, proof-based, and visually premium.",
            ],
        },
        "Business": {
            "gap": [
                "Business content often performs better when it has real founder tension, strong positioning, and meaningful outcomes. Generic founder motivation or vague event recap content usually underperforms because it lacks a clear viewer payoff.",
                "To perform better, the page should create more conflict, clearer founder pain points, and stronger contrast between low-value and high-value founder behavior, rooms, and opportunities.",
            ],
            "ideas": [
                {
                    "hook": "Most founder events look productive. Most are actually a waste of time.",
                    "type": "Controversial Take + Comparison",
                    "concept": "Compare low-value networking events vs high-value founder rooms, showing what separates an event that creates real business from one that creates nothing.",
                    "format": "Premium host-led breakdown with event footage, interview cuts, and on-screen framework.",
                    "why": "It attacks a founder pain point immediately, creates tension fast, and positions Koocester as a curator of quality business environments rather than just another event brand.",
                    "expectation": "The viewer expects a real breakdown of what makes networking valuable, not empty motivation.",
                    "requirement": "Needs strong comparison logic, confident delivery, and event footage that supports authority.",
                    "lead": "High",
                }
            ],
            "best": "Most founder events look productive. Most are actually a waste of time.",
            "storyboard": [
                "Scene 1: Strong contrarian hook over premium event visuals.",
                "Scene 2: Show what low-value founder rooms look like.",
                "Scene 3: Explain what actually makes a founder room valuable.",
                "Scene 4: Build authority with better business environment logic.",
                "Scene 5: End with high-intent CTA for serious founders.",
            ],
            "script": [
                "Opening: Most founder events look productive. Most are actually a waste of time.",
                "Host: Just because a room is full of founders does not mean the room is valuable.",
                "Narration: A valuable room creates access, relevant conversations, and follow-through.",
                "Host: The best founder rooms are not loud. They are intentional.",
                "CTA: If you want better rooms and better outcomes, start here.",
            ],
            "cta": {
                "on_screen": "Comment 'NETWORK' and we’ll send you the next step.",
                "caption_cta": "Follow for more real founder insights.",
                "options": [
                    "Comment 'NETWORK' and we’ll send you the next step.",
                    "Follow for more real founder insights.",
                    "Send this to a founder who is tired of low-value events."
                ]
            },
            "captions": [
                "Most founder events look good on camera. Fewer create real business.",
                "Busy does not mean valuable.",
                "The best founder rooms are not the loudest ones."
            ],
            "virality": [
                "Viral Potential Score: 82/100",
                "Hook Strength Score: 90/100",
                "Retention Strength Score: 79/100",
                "Save/Share Potential: Medium-High",
                "DM/Lead Potential: High",
                "Realistic Performance Expectation: Strong if the delivery is sharp, opinionated, and supported by strong event footage.",
            ],
        },
        "Autos": {
            "gap": [
                "Auto content often looks polished but underperforms if it only showcases the car without deeper ownership psychology, status framing, or meaningful buyer logic.",
                "For stronger retention, the content should connect aesthetics to decision-making, aspiration, and real buyer emotion rather than relying on visuals alone.",
            ],
            "ideas": [
                {
                    "hook": "The mistake people make when buying a premium car.",
                    "type": "Mistake",
                    "concept": "Explain the wrong criteria many buyers focus on and what actually matters in a premium ownership decision.",
                    "format": "Premium host-led breakdown with clean cinematic B-roll and interior detail cuts.",
                    "why": "It creates immediate buyer tension, gives useful content, and shifts the video from pure showcase to decision-led value.",
                    "expectation": "The viewer expects a smarter buyer framework, not just car visuals.",
                    "requirement": "Needs confident delivery and premium footage that matches the positioning.",
                    "lead": "High",
                }
            ],
            "best": "The mistake people make when buying a premium car.",
            "storyboard": [
                "Scene 1: Strong buyer warning hook.",
                "Scene 2: Show the wrong decision criteria.",
                "Scene 3: Reframe what premium ownership really means.",
                "Scene 4: Support with detail shots and logic.",
                "Scene 5: Close with CTA for premium buyers.",
            ],
            "script": [
                "Opening: Most people look at the wrong things when buying a premium car.",
                "Host: They focus on the badge first, but not the ownership experience.",
                "Narration: Premium is not just what looks expensive. It is what continues to feel right after the purchase.",
                "Host: The real question is not just what the car says about you. It is how the car fits your actual life and expectations.",
                "CTA: Save this before your next premium car decision.",
            ],
            "cta": {
                "on_screen": "Save this before your next premium car decision.",
                "caption_cta": "DM 'AUTO' and we’ll show you the next step before you buy.",
                "options": [
                    "DM 'AUTO' and we’ll show you the next step before you buy.",
                    "Save this before your next premium car decision.",
                    "Comment 'AUTO' for the next premium buyer guide."
                ]
            },
            "captions": [
                "A premium car is more than a badge.",
                "Most premium buyers focus on the wrong thing first.",
                "Buying premium should feel smart, not just impressive."
            ],
            "virality": [
                "Viral Potential Score: 74/100",
                "Hook Strength Score: 80/100",
                "Retention Strength Score: 72/100",
                "Save/Share Potential: Medium",
                "DM/Lead Potential: High",
                "Realistic Performance Expectation: Strong when the host delivery feels credible and the footage looks expensive enough to match the topic.",
            ],
        },
        "Foodie": {
            "gap": [
                "Foodie content often becomes repetitive when it relies only on dish visuals without enough taste tension, value framing, reaction payoff, or discovery energy.",
                "To perform better, the content should make the viewer feel there is something worth discovering, comparing, or saving rather than just passively looking at food.",
            ],
            "ideas": [
                {
                    "hook": "This is what RM___ gets you here.",
                    "type": "Money Angle",
                    "concept": "Show the price-to-value clearly while building curiosity around whether the experience is actually worth it.",
                    "format": "Fast visual breakdown with host commentary, texture shots, and payoff moments.",
                    "why": "Money framing performs strongly with Malaysian audiences because it instantly creates relevance and forces a value judgment.",
                    "expectation": "The viewer expects a clear answer on whether the place is worth trying.",
                    "requirement": "Needs satisfying food visuals, pacing, and honest reaction logic.",
                    "lead": "High",
                }
            ],
            "best": "This is what RM___ gets you here.",
            "storyboard": [
                "Scene 1: Price-driven hook.",
                "Scene 2: Quick venue setup.",
                "Scene 3: Dish reveal and texture payoff.",
                "Scene 4: Value judgment and reaction.",
                "Scene 5: Save/share CTA.",
            ],
            "script": [
                "Opening: This is what RM___ gets you here.",
                "Host: And honestly, I did not expect this much.",
                "Narration: The place looks simple, but the food tells a very different story.",
                "Host: What matters here is whether the value matches the hype.",
                "CTA: Save this for your next food hunt.",
            ],
            "cta": {
                "on_screen": "Save this for your next food hunt.",
                "caption_cta": "Tag the person you’re taking here next.",
                "options": [
                    "Save this for your next food hunt.",
                    "Tag the person you’re taking here next.",
                    "Comment 'FOOD' if you want more spots like this."
                ]
            },
            "captions": [
                "Worth it or just hype?",
                "This is what RM___ gets you here.",
                "Simple place, stronger payoff than expected."
            ],
            "virality": [
                "Viral Potential Score: 78/100",
                "Hook Strength Score: 83/100",
                "Retention Strength Score: 76/100",
                "Save/Share Potential: High",
                "DM/Lead Potential: Medium",
                "Realistic Performance Expectation: Strong if the visuals are satisfying and the value verdict feels honest.",
            ],
        },
    }
    return base[category]


# --------------------------------------------------
# OPENAI CALLS
# --------------------------------------------------
def generate_strategy(
    category: str,
    platform: str,
    niche: str,
    audience: str,
    lead_type: str,
    pain_point: str,
    offer: str,
    goal: str,
    video_length: str,
    tone: str,
    recommended_mode: str,
    uploaded_context: str,
    scenario: str,
    model: str = DEFAULT_MODEL,
) -> str:
    client = get_client()

    prompt = build_master_prompt(
        category=category,
        platform=platform,
        niche=niche,
        audience=audience,
        lead_type=lead_type,
        pain_point=pain_point,
        offer=offer,
        goal=goal,
        video_length=video_length,
        tone=tone,
        recommended_mode=recommended_mode,
        uploaded_context=uploaded_context,
        scenario=scenario,
    )

    response = client.responses.create(
        model=model,
        input=prompt,
    )

    return response.output_text


def review_submitted_draft(
    category: str,
    platform: str,
    audience: str,
    lead_type: str,
    goal: str,
    tone: str,
    scenario: str,
    draft_video_idea: str,
    draft_cta: str,
    draft_caption: str,
    model: str = DEFAULT_MODEL,
) -> str:
    client = get_client()

    prompt = build_draft_review_prompt(
        category=category,
        platform=platform,
        audience=audience,
        lead_type=lead_type,
        goal=goal,
        tone=tone,
        scenario=scenario,
        draft_video_idea=draft_video_idea,
        draft_cta=draft_cta,
        draft_caption=draft_caption,
    )

    response = client.responses.create(
        model=model,
        input=prompt,
    )

    return response.output_text


def review_idea_and_script(
    category: str,
    platform: str,
    audience: str,
    lead_type: str,
    goal: str,
    tone: str,
    scenario: str,
    draft_video_idea: str,
    draft_script: str,
    draft_cta: str,
    draft_caption: str,
    model: str = DEFAULT_MODEL,
) -> str:
    client = get_client()

    prompt = build_idea_review_prompt(
        category=category,
        platform=platform,
        audience=audience,
        lead_type=lead_type,
        goal=goal,
        tone=tone,
        scenario=scenario,
        draft_video_idea=draft_video_idea,
        draft_script=draft_script,
        draft_cta=draft_cta,
        draft_caption=draft_caption,
    )

    response = client.responses.create(
        model=model,
        input=prompt,
    )

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
            st.write(f"**Page:** {row.get('page', '-')}")
            st.write(f"**Platform:** {row.get('platform', '-')}")
            st.write(f"**Goal:** {row.get('goal', '-')}")
            st.write(f"**Scenario:** {row.get('scenario', '-')}")
            st.write(f"**Output chars:** {row.get('output_chars', 0)}")
            st.write(f"**Uploaded count:** {row.get('uploaded_count', 0)}")
            st.write(f"**Uploaded bytes:** {row.get('uploaded_total_bytes', 0)}")
            st.write(f"**User agent:** {row.get('user_agent', '')}")
            st.write(f"**IP value:** {row.get('ip_value', '')}")
            st.write(f"**IP source:** {row.get('ip_source', '')}")
            st.write(f"**Notes:** {row.get('notes', '')}")


# --------------------------------------------------
# UI
# --------------------------------------------------
st.title("🚀 Koocester Viral Content Engine")
st.caption(
    "Page-specific viral video idea generator, deeper content planner, virality estimator, storyboard engine, script builder, caption engine, CTA engine, draft reviewer, idea/script scorer, uploads, and admin analytics."
)

session_id = get_session_id()
render_admin_login()

left, right = st.columns([1.2, 0.8], gap="large")

with left:
    st.subheader("Content Brief + Draft Review + Idea Review")

    category = st.selectbox("Koocester Page", ["Homes", "Business", "Autos", "Foodie"])
    length_settings = get_length_settings(category)

    platform = st.selectbox("Platform", ["Instagram", "TikTok"])

    niche = st.text_input(
        "Niche",
        placeholder="e.g. founder networking, renovation mistakes, premium car buying, café discovery",
    )
    audience = st.text_input(
        "Audience",
        placeholder="e.g. founders, first-time homeowners, premium car buyers, food lovers",
    )
    lead_type = st.text_input(
        "Lead Type",
        placeholder="e.g. event leads, homeowners planning renovation, premium buyers, diners",
    )
    pain_point = st.text_input(
        "Pain Point",
        placeholder="e.g. weak hooks, poor retention, generic event recap content",
    )
    offer = st.text_input(
        "Offer / CTA",
        placeholder="e.g. register, DM us, book consultation, visit the place",
    )

    scenario = st.text_area(
        "Video Scenario / Situation",
        placeholder="e.g. We have footage from a founders dinner with people networking, short interviews, venue shots, and premium ambience. We want a video that feels high-value, serious, and good enough to attract founders who care about ROI.",
        height=140,
    )

    goal = st.selectbox("Goal", ["Views", "Engagement", "Leads", "Awareness"])

    video_length = st.selectbox(
        "Video Length",
        length_settings["allowed_lengths"],
        index=length_settings["allowed_lengths"].index(length_settings["recommended_length"]),
    )

    tone = st.selectbox("Tone", ["Premium", "Bold", "Educational", "Emotional", "Direct"])

    uploaded_files = st.file_uploader(
        "Upload supporting files (optional)",
        accept_multiple_files=True,
        type=None,
        help="You can upload files to provide extra context for the strategy.",
    )

    st.divider()
    st.subheader("Draft Review / Idea Correction")

    draft_video_idea = st.text_area(
        "Draft Video Idea",
        placeholder="e.g. We want a founders dinner video showing premium networking and why good rooms matter more than just big events.",
        height=120,
    )

    draft_cta = st.text_input(
        "Draft CTA",
        placeholder="e.g. Fill the Luma form / DM us / Register now",
    )

    draft_caption = st.text_area(
        "Draft Caption",
        placeholder="e.g. Most founder events look productive, but only a few actually create real business.",
        height=100,
    )

    st.divider()
    st.subheader("Idea / Script Review")

    review_video_idea = st.text_area(
        "Your Video Idea",
        placeholder="e.g. A premium reel showing why most people buy cars emotionally but justify them logically.",
        height=110,
    )

    review_script = st.text_area(
        "Your Draft Script",
        placeholder="Paste your draft script here...",
        height=180,
    )

    review_cta = st.text_input(
        "Your Draft CTA",
        placeholder="e.g. DM us to book a viewing / Fill the Luma form / Register now",
    )

    review_caption = st.text_area(
        "Your Draft Caption",
        placeholder="Paste your draft caption here...",
        height=100,
    )

    c_btn1, c_btn2, c_btn3 = st.columns(3)
    with c_btn1:
        generate = st.button("Build Viral Strategy", use_container_width=True)
    with c_btn2:
        review_draft = st.button("Rate & Improve Draft", use_container_width=True)
    with c_btn3:
        review_idea_btn = st.button("Rate My Idea / Script", use_container_width=True)

with right:
    st.subheader("Live Brief Preview")
    st.write(f"**Page:** {category}")
    st.write(f"**Platform:** {platform}")
    st.write(f"**Niche:** {niche or '—'}")
    st.write(f"**Audience:** {audience or '—'}")
    st.write(f"**Lead Type:** {lead_type or '—'}")
    st.write(f"**Pain Point:** {pain_point or '—'}")
    st.write(f"**Offer / CTA:** {offer or '—'}")
    st.write(f"**Goal:** {goal}")
    st.write(f"**Recommended Mode:** {length_settings['recommended_mode']}")
    st.write(f"**Recommended Length:** {length_settings['recommended_length']}")
    st.write(f"**Selected Length:** {video_length}")
    st.write(f"**Why:** {length_settings['reason']}")
    st.write(f"**Tone:** {tone}")
    st.write(f"**Scenario:** {scenario[:250] + '...' if len(scenario) > 250 else (scenario or '—')}")

    uploaded_context, uploaded_files_json, uploaded_count, uploaded_total_bytes = summarize_uploaded_files(uploaded_files)
    st.divider()
    st.subheader("Upload Summary")
    st.write(f"**Files uploaded:** {uploaded_count}")
    st.write(f"**Total size (bytes):** {uploaded_total_bytes}")
    if uploaded_count:
        st.code(uploaded_context, language="text")

    st.divider()
    st.subheader("Draft Review Preview")
    st.write(f"**Draft Video Idea:** {draft_video_idea or '—'}")
    st.write(f"**Draft CTA:** {draft_cta or '—'}")
    st.write(f"**Draft Caption:** {draft_caption or '—'}")

    st.divider()
    st.subheader("Idea / Script Review Preview")
    st.write(f"**Video Idea:** {review_video_idea or '—'}")
    st.write(f"**Draft Script:** {(review_script[:250] + '...') if len(review_script) > 250 else (review_script or '—')}")
    st.write(f"**Draft CTA:** {review_cta or '—'}")
    st.write(f"**Draft Caption:** {review_caption or '—'}")

st.divider()
st.subheader("Master Prompt Preview")

if niche or audience or lead_type or pain_point or offer or scenario:
    master_prompt = build_master_prompt(
        category=category,
        platform=platform,
        niche=niche,
        audience=audience,
        lead_type=lead_type,
        pain_point=pain_point,
        offer=offer,
        goal=goal,
        video_length=video_length,
        tone=tone,
        recommended_mode=length_settings["recommended_mode"],
        uploaded_context=uploaded_context,
        scenario=scenario,
    )
    st.code(master_prompt, language="text")
else:
    st.caption("Fill in the form to see the full prompt preview.")


# --------------------------------------------------
# GENERATE MAIN STRATEGY
# --------------------------------------------------
if generate:
    missing: List[str] = []
    if not niche.strip():
        missing.append("Niche")
    if not audience.strip():
        missing.append("Audience")
    if not lead_type.strip():
        missing.append("Lead Type")
    if not pain_point.strip():
        missing.append("Pain Point")
    if not offer.strip():
        missing.append("Offer / CTA")

    ip_value, ip_source = get_ip_if_available()
    user_agent = get_user_agent()

    if missing:
        insert_usage_log(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
                "page": category,
                "platform": platform,
                "niche": niche,
                "audience": audience,
                "lead_type": lead_type,
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
            with st.spinner("Generating viral strategy..."):
                output = generate_strategy(
                    category=category,
                    platform=platform,
                    niche=niche,
                    audience=audience,
                    lead_type=lead_type,
                    pain_point=pain_point,
                    offer=offer,
                    goal=goal,
                    video_length=video_length,
                    tone=tone,
                    recommended_mode=length_settings["recommended_mode"],
                    uploaded_context=uploaded_context,
                    scenario=scenario,
                    model=DEFAULT_MODEL,
                )

            insert_usage_log(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "page": category,
                    "platform": platform,
                    "niche": niche,
                    "audience": audience,
                    "lead_type": lead_type,
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
                    "notes": "",
                }
            )

            st.divider()
            st.subheader("Generated Strategy")
            st.markdown(output)

        except Exception as e:
            insert_usage_log(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "page": category,
                    "platform": platform,
                    "niche": niche,
                    "audience": audience,
                    "lead_type": lead_type,
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
            st.info("Showing page-specific sample output below so you can keep testing the UI.")

            data = get_sample_outputs(category)

            tabs = st.tabs(
                [
                    "Strategy Gap",
                    "7 Viral Ideas",
                    "Best Idea",
                    "Storyboard",
                    "Script + Dialogue",
                    "Virality Estimate",
                    "CTA",
                    "Captions",
                ]
            )

            with tabs[0]:
                st.subheader("Content Strategy Gap")
                for item in data["gap"]:
                    st.write(f"- {item}")

            with tabs[1]:
                st.subheader(f"{category} Viral Ideas")
                for i, idea in enumerate(data["ideas"], start=1):
                    st.markdown(f"### Idea {i}")
                    st.write(f"**Hook:** {idea['hook']}")
                    st.write(f"**Type:** {idea['type']}")
                    st.write(f"**Concept:** {idea['concept']}")
                    st.write(f"**Video Format:** {idea['format']}")
                    st.write(f"**Why It Will Work:** {idea['why']}")
                    st.write(f"**Viewer Expectation:** {idea['expectation']}")
                    st.write(f"**Content Requirement:** {idea['requirement']}")
                    st.write(f"**Lead Intent:** {idea['lead']}")
                    st.divider()

            with tabs[2]:
                st.subheader("Best Idea")
                st.write(data["best"])

            with tabs[3]:
                st.subheader("Full Storyboard")
                for idx, scene in enumerate(data["storyboard"], start=1):
                    st.write(f"**Scene {idx}:** {scene}")
                st.write(f"**CTA (ON-SCREEN TEXT):** {data['cta']['on_screen']}")
                st.write(f"**CTA (CAPTION CTA):** {data['cta']['caption_cta']}")

            with tabs[4]:
                st.subheader("Video Script With Dialogue")
                for line in data["script"]:
                    st.write(f"- {line}")

            with tabs[5]:
                st.subheader("Virality Estimate")
                for line in data["virality"]:
                    st.write(f"- {line}")

            with tabs[6]:
                st.subheader("🎯 Call To Action")
                st.write(f"**On-Screen CTA:** {data['cta']['on_screen']}")
                st.write(f"**Caption CTA:** {data['cta']['caption_cta']}")
                st.write("**CTA Options:**")
                for option in data["cta"]["options"]:
                    st.write(f"- {option}")

            with tabs[7]:
                st.subheader("Caption Suggestions")
                for idx, caption in enumerate(data["captions"], start=1):
                    st.write(f"**Caption {idx}:** {caption}")


# --------------------------------------------------
# REVIEW DRAFT
# --------------------------------------------------
if review_draft:
    review_missing: List[str] = []

    if not draft_video_idea.strip():
        review_missing.append("Draft Video Idea")
    if not draft_cta.strip():
        review_missing.append("Draft CTA")
    if not draft_caption.strip():
        review_missing.append("Draft Caption")

    ip_value, ip_source = get_ip_if_available()
    user_agent = get_user_agent()

    if review_missing:
        insert_usage_log(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
                "page": category,
                "platform": platform,
                "niche": niche,
                "audience": audience,
                "lead_type": lead_type,
                "pain_point": pain_point,
                "offer": offer,
                "goal": goal,
                "video_length": video_length,
                "tone": tone,
                "scenario": scenario,
                "action_type": "draft_review_validation_error",
                "output_chars": 0,
                "user_agent": user_agent,
                "uploaded_files_json": uploaded_files_json,
                "uploaded_total_bytes": uploaded_total_bytes,
                "uploaded_count": uploaded_count,
                "ip_value": ip_value,
                "ip_source": ip_source,
                "notes": "Missing draft review fields",
            }
        )
        st.error("Please fill in: " + ", ".join(review_missing))
    else:
        try:
            with st.spinner("Reviewing and improving draft..."):
                review_output = review_submitted_draft(
                    category=category,
                    platform=platform,
                    audience=audience,
                    lead_type=lead_type,
                    goal=goal,
                    tone=tone,
                    scenario=scenario,
                    draft_video_idea=draft_video_idea,
                    draft_cta=draft_cta,
                    draft_caption=draft_caption,
                    model=DEFAULT_MODEL,
                )

            insert_usage_log(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "page": category,
                    "platform": platform,
                    "niche": niche,
                    "audience": audience,
                    "lead_type": lead_type,
                    "pain_point": pain_point,
                    "offer": offer,
                    "goal": goal,
                    "video_length": video_length,
                    "tone": tone,
                    "scenario": scenario,
                    "action_type": "draft_review",
                    "output_chars": len(review_output or ""),
                    "user_agent": user_agent,
                    "uploaded_files_json": uploaded_files_json,
                    "uploaded_total_bytes": uploaded_total_bytes,
                    "uploaded_count": uploaded_count,
                    "ip_value": ip_value,
                    "ip_source": ip_source,
                    "notes": f"Draft CTA: {draft_cta} | Draft Caption: {draft_caption}",
                }
            )

            st.divider()
            st.subheader("Draft Review Result")
            st.markdown(review_output)

        except Exception as e:
            insert_usage_log(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "page": category,
                    "platform": platform,
                    "niche": niche,
                    "audience": audience,
                    "lead_type": lead_type,
                    "pain_point": pain_point,
                    "offer": offer,
                    "goal": goal,
                    "video_length": video_length,
                    "tone": tone,
                    "scenario": scenario,
                    "action_type": "draft_review_error",
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

    ip_value, ip_source = get_ip_if_available()
    user_agent = get_user_agent()

    if missing_review:
        insert_usage_log(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
                "page": category,
                "platform": platform,
                "niche": niche,
                "audience": audience,
                "lead_type": lead_type,
                "pain_point": pain_point,
                "offer": offer,
                "goal": goal,
                "video_length": video_length,
                "tone": tone,
                "scenario": scenario,
                "action_type": "idea_script_review_validation_error",
                "output_chars": 0,
                "user_agent": user_agent,
                "uploaded_files_json": uploaded_files_json,
                "uploaded_total_bytes": uploaded_total_bytes,
                "uploaded_count": uploaded_count,
                "ip_value": ip_value,
                "ip_source": ip_source,
                "notes": "Missing idea/script review fields",
            }
        )
        st.error("Please fill in: " + ", ".join(missing_review))
    else:
        try:
            with st.spinner("Reviewing your idea and script..."):
                reviewed_output = review_idea_and_script(
                    category=category,
                    platform=platform,
                    audience=audience,
                    lead_type=lead_type,
                    goal=goal,
                    tone=tone,
                    scenario=scenario,
                    draft_video_idea=review_video_idea,
                    draft_script=review_script,
                    draft_cta=review_cta,
                    draft_caption=review_caption,
                    model=DEFAULT_MODEL,
                )

            insert_usage_log(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "page": category,
                    "platform": platform,
                    "niche": niche,
                    "audience": audience,
                    "lead_type": lead_type,
                    "pain_point": pain_point,
                    "offer": offer,
                    "goal": goal,
                    "video_length": video_length,
                    "tone": tone,
                    "scenario": scenario,
                    "action_type": "idea_script_review",
                    "output_chars": len(reviewed_output or ""),
                    "user_agent": user_agent,
                    "uploaded_files_json": uploaded_files_json,
                    "uploaded_total_bytes": uploaded_total_bytes,
                    "uploaded_count": uploaded_count,
                    "ip_value": ip_value,
                    "ip_source": ip_source,
                    "notes": "Reviewed submitted idea/script",
                }
            )

            st.divider()
            st.subheader("Idea / Script Review Result")
            st.markdown(reviewed_output)

        except Exception as e:
            insert_usage_log(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "page": category,
                    "platform": platform,
                    "niche": niche,
                    "audience": audience,
                    "lead_type": lead_type,
                    "pain_point": pain_point,
                    "offer": offer,
                    "goal": goal,
                    "video_length": video_length,
                    "tone": tone,
                    "scenario": scenario,
                    "action_type": "idea_script_review_error",
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


if is_admin():
    render_admin_analytics()

st.divider()
st.caption(
    "Final file: main generator + draft review + idea/script review + scenario-based virality estimates + caption suggestions + uploads + analytics + admin view."
)
