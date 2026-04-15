import os
from typing import Dict, List

import streamlit as st
from openai import OpenAI


st.set_page_config(
    page_title="Koocester Viral Content Engine",
    page_icon="🚀",
    layout="wide"
)


# --------------------------------------------------
# PAGE-BASED LENGTH RULES
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
def get_client(api_key_from_ui: str) -> OpenAI:
    api_key = api_key_from_ui.strip() or os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "No OpenAI API key found. Add it in the sidebar or set OPENAI_API_KEY."
        )
    return OpenAI(api_key=api_key)


# --------------------------------------------------
# MASTER PROMPT BUILDER
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
) -> str:
    return f"""
You are an ELITE viral content strategist, retention expert, storyboard architect, and video scriptwriter for Koocester.

Your job is to generate the BEST possible viral video ideas targeted for qualified leads, with complete storyboarding automation and full video structure.

You must think like:
- viral strategist
- retention editor
- hook writer
- scriptwriter
- storyboard planner
- lead generation strategist
- platform growth operator

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

==================================================
PAGE-SPECIFIC RULE (VERY IMPORTANT)
==================================================

The selected page is: {category}

You must ONLY generate content relevant to this page.

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

Do not mix categories.
Do not generate generic content.
Everything must stay tightly aligned to the selected page.

==================================================
PAGE POSITIONING
==================================================

Homes:
- renovation
- home tours
- interior design
- homeowner mistakes
- property lifestyle
- budget vs premium decisions

Business:
- founder content
- networking
- interviews
- social proof
- event-driven content
- business lifestyle
- entrepreneurship insights

Autos:
- luxury lifestyle
- car showcases
- buyer psychology
- status signaling
- aspiration
- performance and ownership experience

Foodie:
- food discovery
- restaurant highlights
- dish-focused content
- cafe experiences
- taste reactions
- dining lifestyle
- visually satisfying food storytelling

==================================================
TARGET AUDIENCE
==================================================

Audience / Lead Type: {lead_type}
Audience Details: {audience}
Pain Point: {pain_point}
Offer / CTA: {offer}
Goal: {goal}
Niche: {niche}

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
- stronger visuals
- aesthetic pacing
- more polished storytelling

TikTok:
- faster pacing
- sharper hooks
- more direct language
- more pattern interrupts
- more raw relatability

You must tailor all ideas and scripts to the selected platform.

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
- slightly deeper explanation
- include a mid-video hook
- use 1–2 pattern interrupts
- stronger storytelling and context
- maintain retention throughout

If video length is 180–240 sec:
- strong opening hook in first 0–5 seconds
- multiple retention checkpoints
- clear narrative flow
- scene progression must keep interest alive
- use emotional and visual payoff throughout

If video length is 300–360 sec:
- use chapter-like structure
- introduce mini-hooks throughout the video
- keep energy changing across scenes
- avoid slow filler
- use deeper storytelling, examples, comparisons, and reveals
- maintain attention with progression, not repetition

==================================================
RETENTION RULES (CRITICAL)
==================================================

Every best-performing output MUST include:

1. HOOK
- immediate scroll-stop
- tension, curiosity, fear, regret, aspiration, controversy, or shock
- no slow intro

2. PATTERN INTERRUPT
- a switch in visual, tone, camera angle, statement, subtitle, or pacing that re-grabs attention

3. OPEN LOOP
- create unresolved tension or curiosity so the viewer keeps watching

4. PAYOFF
- deliver the answer, reveal, lesson, or transformation clearly

5. CTA
- natural, not forced
- aligned with the goal
- positioned at the right moment

==================================================
CONTENT RULES
==================================================

Your ideas MUST:
- be BETTER versions of Koocester’s current content style
- align with the selected page only
- be optimized for Malaysian audience psychology
- be practical to film
- be easy for a team to execute
- improve hooks, retention, and watch time
- attract real interest from leads
- feel scroll-stopping, not generic

==================================================
VIRAL CONTENT TYPES TO USE
==================================================

Use these strategically where relevant:
- Mistake
- POV
- Comparison
- Story
- Curiosity
- Controversial Take
- Aspiration
- Regret
- Transformation
- Behind-the-scenes

==================================================
VIDEO EXECUTION REQUIREMENTS
==================================================

For the BEST idea, provide:
- best video format
- best hook
- retention structure
- complete storyboard
- shot direction
- full script
- dialogue
- on-screen text
- CTA line
- caption

==================================================
OUTPUT FORMAT (STRICT)
==================================================

Return in this exact structure:

1. CONTENT STRATEGY GAP
- what this specific page is currently missing or doing weakly
- explain only in relation to the selected page

2. 7 VIRAL VIDEO IDEAS
For each idea include:
- Hook
- Type
- Concept
- Video Format
- Why It Will Work
- Lead Intent

3. BEST IDEA
- explain why this is strongest for views + retention + clicks + leads
- explain why it fits this specific page

4. RETENTION ENGINE
- Hook
- Pattern Interrupt
- Open Loop
- Payoff
- CTA Placement

5. FULL STORYBOARD
- Scene 1
- Scene 2
- Scene 3
- Scene 4
- Scene 5
- Ending CTA

6. VIDEO SCRIPT WITH DIALOGUE
- Opening Line
- Host Dialogue
- Supporting Dialogue / Narration
- Scene-by-Scene Script
- On-Screen Text
- Closing CTA Dialogue

7. CAPTION
- natural
- platform-suitable
- not robotic
- engaging enough to support clicks and reach

==================================================
TONE AND EXECUTION SETTINGS
==================================================

Tone: {tone}

==================================================
FINAL INSTRUCTIONS
==================================================

Make sure the output is:
- page-specific
- platform-specific
- Malaysia-first
- aligned with Koocester’s previous content direction
- improved for better hooks, better retention, and stronger lead generation
- practical enough to actually film
- strong enough to outperform generic content

IMPORTANT:
- If page = Autos, only provide auto-related ideas
- If page = Homes, only provide home-related ideas
- If page = Business, only provide founder/networking/business-related ideas
- If page = Foodie, only provide foodie-related ideas
- Never mix page types
- Never go outside the selected page
""".strip()


# --------------------------------------------------
# SAMPLE OUTPUTS
# --------------------------------------------------
def get_sample_outputs(category: str) -> dict:
    samples = {
        "Homes": {
            "gap": [
                "The niche is strong, but content can be more pain-driven and emotionally framed.",
                "Mistakes, regret, budget tension, and Malaysian homeowner realities can improve views and retention.",
            ],
            "ideas": [
                {
                    "hook": "Most Malaysians get this wrong before renovating.",
                    "type": "Mistake",
                    "concept": "Reveal one expensive renovation mistake that causes regret later.",
                    "format": "Presenter + B-roll",
                    "why": "Fear + regret + local homeowner relatability.",
                    "lead": "High",
                },
                {
                    "hook": "POV: you got your first home and now every decision feels expensive.",
                    "type": "POV",
                    "concept": "Emotional first-home stress journey.",
                    "format": "POV skit",
                    "why": "Aspirational milestone + pressure + relatability.",
                    "lead": "High",
                },
                {
                    "hook": "This house looks more expensive than it actually is.",
                    "type": "Curiosity",
                    "concept": "Show design decisions that elevate perceived value.",
                    "format": "Voiceover home tour",
                    "why": "Visual payoff + money angle.",
                    "lead": "Medium",
                },
                {
                    "hook": "Nobody talks about this renovation regret in Malaysia.",
                    "type": "Story",
                    "concept": "Tell a regret story and reveal the lesson.",
                    "format": "Narrated reel",
                    "why": "Local relevance + emotional payoff.",
                    "lead": "High",
                },
                {
                    "hook": "The budget mistake that ruins a beautiful renovation.",
                    "type": "Mistake",
                    "concept": "Talk about budgeting in the wrong order.",
                    "format": "Talking-head + examples",
                    "why": "Money pain + fear + usefulness.",
                    "lead": "High",
                },
                {
                    "hook": "Before you choose an ID, watch this.",
                    "type": "Warning",
                    "concept": "Checklist of what homeowners miss.",
                    "format": "Checklist reel",
                    "why": "Urgency + practical value.",
                    "lead": "High",
                },
                {
                    "hook": "This is why some homes feel premium instantly.",
                    "type": "Comparison",
                    "concept": "Show design choices that change feel and perceived value.",
                    "format": "Before/after comparison",
                    "why": "Visual contrast + aspiration.",
                    "lead": "Medium",
                },
            ],
            "best": "Most Malaysians get this wrong before renovating.",
            "storyboard": [
                "Hook over strong home visual.",
                "Show homeowner confusion and saving inspiration references.",
                "Show wrong order of decisions: beauty before layout and budget.",
                "Show consequence: wasted money, poor function, regret.",
                "Reveal smarter planning order and close with CTA.",
            ],
            "script": [
                "Opening: Most Malaysians make this mistake before the renovation even starts.",
                "Host: A lot of people think renovation starts with choosing a beautiful design. It doesn’t.",
                "Narration: The biggest mistake usually happens before any work even begins.",
                "Host: You save inspiration first, but you still haven’t planned your layout, budget, or flow.",
                "CTA: If you’re planning your renovation, talk to us before you make the expensive mistakes.",
            ],
            "caption": "One wrong renovation decision at the start can cost you way more later."
        },
        "Business": {
            "gap": [
                "Content direction is strong, but hooks are often not aggressive enough for retention.",
                "Sharper founder pain, stronger networking lessons, stronger opinions, and more social-proof tension would improve performance.",
            ],
            "ideas": [
                {
                    "hook": "Why smart founders still get ignored online.",
                    "type": "Controversial",
                    "concept": "Show that good advice alone is not enough without a strong hook.",
                    "format": "Talking-head breakdown",
                    "why": "Debate + relevance + creator pain point.",
                    "lead": "Medium",
                },
                {
                    "hook": "The networking mistake most founders only realize too late.",
                    "type": "Mistake",
                    "concept": "Break down how people attend events but build no real relationships.",
                    "format": "Presenter + event clips",
                    "why": "Business pain + regret + practical lesson.",
                    "lead": "High",
                },
                {
                    "hook": "POV: you met the right person at one event and everything changed.",
                    "type": "POV",
                    "concept": "Story-driven networking payoff clip.",
                    "format": "POV + recap montage",
                    "why": "Aspiration + opportunity + emotional payoff.",
                    "lead": "High",
                },
                {
                    "hook": "This is why your founder content looks smart but gets no reach.",
                    "type": "Educational pain",
                    "concept": "Compare weak hooks vs strong hooks.",
                    "format": "Hook teardown",
                    "why": "Highly relevant and instantly useful.",
                    "lead": "Medium",
                },
                {
                    "hook": "What actually makes people trust a founder online.",
                    "type": "Curiosity",
                    "concept": "Explain what builds credibility beyond just advice.",
                    "format": "Presenter + proof examples",
                    "why": "Trust psychology + social proof.",
                    "lead": "Medium",
                },
                {
                    "hook": "Most business events fail because people do this.",
                    "type": "Story",
                    "concept": "Show surface-level networking vs meaningful interaction.",
                    "format": "Event narrative reel",
                    "why": "Pain + relatability + improvement angle.",
                    "lead": "High",
                },
                {
                    "hook": "The one thing successful founders do differently in a room full of people.",
                    "type": "Aspiration",
                    "concept": "Behavioral difference breakdown.",
                    "format": "Narrated event reel",
                    "why": "Status + curiosity + self-improvement.",
                    "lead": "Medium",
                },
            ],
            "best": "The networking mistake most founders only realize too late.",
            "storyboard": [
                "Hook with a sharp statement over event visuals.",
                "Show people networking badly — quick hellos, no follow-up, shallow conversations.",
                "Reveal the mistake: collecting contacts but building no real connection.",
                "Show what stronger networking looks like.",
                "Close with action step and CTA.",
            ],
            "script": [
                "Opening: Most founders network a lot and still get nothing from it.",
                "Host: The mistake isn’t showing up. It’s showing up without intention.",
                "Narration: You meet people, exchange contacts, and then nothing happens.",
                "Host: The real value comes from relevance, follow-up, and actual connection.",
                "CTA: Want better rooms and better conversations? Start here.",
            ],
            "caption": "Most people attend events. Few know how to turn them into real opportunities."
        },
        "Autos": {
            "gap": [
                "Auto content often looks visually nice but lacks enough tension, status psychology, and story to hold retention.",
                "The page should push stronger buyer psychology, aspiration, and contrast instead of just static showcase clips.",
            ],
            "ideas": [
                {
                    "hook": "This is the kind of car content people actually finish watching.",
                    "type": "Comparison",
                    "concept": "Show boring showcase vs story-driven premium auto content.",
                    "format": "Comparison edit",
                    "why": "Clear contrast improves retention.",
                    "lead": "Medium",
                },
                {
                    "hook": "Why some cars feel premium before you even drive them.",
                    "type": "Curiosity",
                    "concept": "Break down details that create premium perception.",
                    "format": "Voiceover cinematic reel",
                    "why": "Status psychology + satisfying payoff.",
                    "lead": "Medium",
                },
                {
                    "hook": "POV: you finally got the car you always wanted.",
                    "type": "POV",
                    "concept": "Aspirational ownership moment.",
                    "format": "Driver POV cinematic reel",
                    "why": "Aspiration + emotional payoff.",
                    "lead": "High",
                },
                {
                    "hook": "The mistake people make when buying a premium car.",
                    "type": "Mistake",
                    "concept": "Explain what buyers focus on wrongly.",
                    "format": "Presenter + B-roll",
                    "why": "Buyer pain + fear + usefulness.",
                    "lead": "High",
                },
                {
                    "hook": "This one detail changes how expensive a car feels.",
                    "type": "Curiosity",
                    "concept": "Focus on interior, sound, materials, or driving feel.",
                    "format": "Detail-focused short reel",
                    "why": "Sensory curiosity + premium angle.",
                    "lead": "Medium",
                },
                {
                    "hook": "Most people show cars the boring way.",
                    "type": "Controversial",
                    "concept": "Call out static walkarounds and show better storytelling.",
                    "format": "Breakdown + examples",
                    "why": "Debate + content improvement angle.",
                    "lead": "Medium",
                },
                {
                    "hook": "This is what luxury car content should feel like.",
                    "type": "Aspiration",
                    "concept": "Blend motion, status, mood, and ownership feeling.",
                    "format": "Lifestyle montage",
                    "why": "Emotion + status + identity.",
                    "lead": "Medium",
                },
            ],
            "best": "The mistake people make when buying a premium car.",
            "storyboard": [
                "Hook with sharp buyer warning.",
                "Show people focusing on the wrong things.",
                "Introduce real premium-buyer considerations.",
                "Show better decision framework with matching visuals.",
                "End with a clean CTA.",
            ],
            "script": [
                "Opening: Most people look at the wrong things when buying a premium car.",
                "Host: They focus on the badge first, but not the ownership experience.",
                "Narration: A premium car is not just what it looks like. It’s what it feels like to live with.",
                "Host: Sound, comfort, drive feel, cabin quality, and status fit matter more than people think.",
                "CTA: Looking for the right premium experience? Start with the right questions.",
            ],
            "caption": "A premium car isn’t just about the badge. It’s about the whole ownership experience."
        },
        "Foodie": {
            "gap": [
                "Food content needs stronger hooks than just showing the dish.",
                "More taste tension, reaction moments, contrast, price-value framing, and local foodie relatability will improve performance.",
            ],
            "ideas": [
                {
                    "hook": "This might be the most satisfying bite you’ll see today.",
                    "type": "Curiosity",
                    "concept": "Lead with a close-up food payoff and texture reveal.",
                    "format": "Close-up visual reel",
                    "why": "Immediate sensory hook and strong visual satisfaction.",
                    "lead": "Medium",
                },
                {
                    "hook": "POV: you found a spot in Malaysia you almost don’t want to share.",
                    "type": "POV",
                    "concept": "Food discovery story with exclusivity tension.",
                    "format": "Foodie discovery vlog",
                    "why": "Discovery + exclusivity + local appeal.",
                    "lead": "High",
                },
                {
                    "hook": "Is this actually worth the hype?",
                    "type": "Comparison",
                    "concept": "Test a viral dish or popular place honestly.",
                    "format": "Taste test breakdown",
                    "why": "Debate + curiosity + click-worthy framing.",
                    "lead": "High",
                },
                {
                    "hook": "This is what RM___ gets you here.",
                    "type": "Money angle",
                    "concept": "Show price-to-value and portions clearly.",
                    "format": "Value breakdown reel",
                    "why": "Malaysian audience loves value framing.",
                    "lead": "High",
                },
                {
                    "hook": "The one dish you should not leave without trying.",
                    "type": "Recommendation",
                    "concept": "Single-dish spotlight with strong reaction.",
                    "format": "Presenter + dish spotlight",
                    "why": "Simple, clear, high intent.",
                    "lead": "Medium",
                },
                {
                    "hook": "Most people order the wrong thing here.",
                    "type": "Mistake",
                    "concept": "Guide viewers to a better order choice.",
                    "format": "Food ordering tip reel",
                    "why": "Mistake framing creates curiosity fast.",
                    "lead": "High",
                },
                {
                    "hook": "This place looks normal until the food arrives.",
                    "type": "Story",
                    "concept": "Build tension from environment to dish payoff.",
                    "format": "Mini reveal story",
                    "why": "Strong reveal structure and visual payoff.",
                    "lead": "Medium",
                },
            ],
            "best": "This is what RM___ gets you here.",
            "storyboard": [
                "Hook with price-value question.",
                "Show venue quickly without overexplaining.",
                "Reveal dishes one by one with texture and reaction.",
                "Compare expectation vs actual value.",
                "End with recommendation and CTA.",
            ],
            "script": [
                "Opening: This is what RM___ gets you here.",
                "Host: And honestly, I didn’t expect this much.",
                "Narration: The place looks simple, but the food tells a different story.",
                "Host: If you come here, don’t waste your order on the obvious pick first.",
                "CTA: Save this for your next food hunt.",
            ],
            "caption": "Worth it or overhyped? This one surprised me."
        },
    }
    return samples[category]


# --------------------------------------------------
# OPENAI GENERATION
# --------------------------------------------------
def generate_strategy(
    api_key: str,
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
    model: str,
) -> str:
    client = get_client(api_key)

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
    )

    response = client.responses.create(
        model=model,
        input=prompt,
    )

    return response.output_text


# --------------------------------------------------
# UI
# --------------------------------------------------
st.title("🚀 Koocester Viral Content Engine")
st.caption("Page-specific viral video idea generator, retention planner, storyboard engine, and script builder.")

with st.sidebar:
    st.header("OpenAI")
    api_key_input = st.text_input("API Key", type="password")
    model_name = st.text_input("Model", value="gpt-5.4")
    st.caption("Paste the API key here or use OPENAI_API_KEY.")

    st.divider()
    st.header("Engine Priorities")
    st.markdown("""
- Malaysia-first relevance
- page-specific output
- stronger hooks
- higher retention
- better leads
- complete storyboard
- script + dialogue
- auto-optimized video length
""")

st.divider()

left, right = st.columns([1.2, 0.8], gap="large")

with left:
    st.subheader("Content Brief")

    category = st.selectbox(
        "Koocester Page",
        ["Homes", "Business", "Autos", "Foodie"]
    )

    length_settings = get_length_settings(category)

    platform = st.selectbox(
        "Platform",
        ["Instagram", "TikTok"]
    )

    niche = st.text_input(
        "Niche",
        placeholder="e.g. renovation mistakes, founder networking, premium car buying, café discovery"
    )
    audience = st.text_input(
        "Audience",
        placeholder="e.g. first-time homeowners, founders, premium car buyers, food lovers"
    )
    lead_type = st.text_input(
        "Lead Type",
        placeholder="e.g. homeowners planning renovation, event leads, premium buyers, diners"
    )
    pain_point = st.text_input(
        "Pain Point",
        placeholder="e.g. weak hooks, poor retention, generic content"
    )
    offer = st.text_input(
        "Offer / CTA",
        placeholder="e.g. book consultation, register, DM us, visit the place"
    )

    goal = st.selectbox(
        "Goal",
        ["Views", "Engagement", "Leads", "Awareness"]
    )

    video_length = st.selectbox(
        "Video Length",
        length_settings["allowed_lengths"],
        index=length_settings["allowed_lengths"].index(length_settings["recommended_length"])
    )

    tone = st.selectbox(
        "Tone",
        ["Premium", "Bold", "Educational", "Emotional", "Direct"]
    )

    generate = st.button("Build Viral Strategy", use_container_width=True)

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

st.divider()
st.subheader("Master Prompt Preview")

if niche or audience or lead_type or pain_point or offer:
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
    )
    st.code(master_prompt, language="text")
else:
    st.caption("Fill in the form to see the full prompt preview.")

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

    if missing:
        st.error("Please fill in: " + ", ".join(missing))
    else:
        try:
            with st.spinner("Generating viral strategy..."):
                output = generate_strategy(
                    api_key=api_key_input,
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
                    model=model_name.strip() or "gpt-5.4",
                )

            st.divider()
            st.subheader("Generated Strategy")
            st.markdown(output)

        except Exception as e:
            st.error(str(e))
            st.info("Showing page-specific sample output below so you can keep testing the UI.")

            data = get_sample_outputs(category)

            tabs = st.tabs([
                "Strategy Gap",
                "7 Viral Ideas",
                "Best Idea",
                "Storyboard",
                "Script + Dialogue",
                "Caption"
            ])

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
                    st.write(f"**Lead Intent:** {idea['lead']}")
                    st.divider()

            with tabs[2]:
                st.subheader("Best Idea")
                st.write(data["best"])

            with tabs[3]:
                st.subheader("Full Storyboard")
                for idx, scene in enumerate(data["storyboard"], start=1):
                    st.write(f"**Scene {idx}:** {scene}")

            with tabs[4]:
                st.subheader("Video Script With Dialogue")
                for line in data["script"]:
                    st.write(f"- {line}")

            with tabs[5]:
                st.subheader("Caption")
                st.write(data["caption"])

st.divider()
st.caption("Final file: Homes + Business + Autos + Foodie, page-specific logic, real AI generation, and duration rules matched to your content style.")