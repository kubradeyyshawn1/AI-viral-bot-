import os
import json
import uuid
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Any
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

import streamlit as st
from openai import OpenAI


st.set_page_config(
    page_title="Koocester Producer Intelligence Engine",
    page_icon="K",
    layout="wide",
    initial_sidebar_state="collapsed",
)

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "analytics.db"
DEFAULT_MODEL = "gpt-5.4"

# Hide backend/debug sections from normal producers.
SHOW_ADVANCED_FIELDS = False
SHOW_DEBUG_PROMPTS = False
SHOW_PUBLIC_INTELLIGENCE = False
SHOW_PAGE_INTELLIGENCE_PREVIEW = False


# --------------------------------------------------
# STREAMLIT SECRETS TEMPLATE
# --------------------------------------------------
SECRETS_TEMPLATE = """
OPENAI_API_KEY = "your_openai_api_key_here"
ADMIN_PASSWORD = "your_admin_password_here"

# Optional Meta / Instagram own-account analytics.
# Use official Meta API only. Do not commit real values to GitHub.
META_ACCESS_TOKEN = "your_meta_access_token_here"

# Map each page internal_key to its Instagram Business/Creator User ID.
IG_USER_ID_MAP_JSON = "{\"main\":\"\",\"business\":\"\",\"autos\":\"\",\"homes\":\"\",\"business_my\":\"\",\"autos_my\":\"\",\"homes_my\":\"\",\"wealth\":\"\",\"foodie\":\"\"}"

# Optional latest public trend feed.
# This is needed for latest public viral scanning beyond your own account analytics.
TREND_FEED_API_URL = ""

# Optional manual trend feed JSON fallback.
# Keep only recent items. posted_at must be ISO format.
TREND_FEED_JSON = "[]"

# Optional Apify Instagram trend scanner.
APIFY_API_TOKEN = ""
APIFY_INSTAGRAM_ACTOR = "apify/instagram-scraper"
APIFY_RESULTS_LIMIT = "40"
APIFY_INPUT_FIELD = "directUrls"
APIFY_MAX_PROFILES = "8"
APIFY_MAX_HASHTAGS = "4"
APIFY_RESULTS_TYPE = "posts"
"""


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
        st.header("Admin Access")
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
- Country-specific relevance
- Instagram-page-aware outputs
- same brand path, stronger execution
- viral now + rising next
- producer/copywriter outputs
- hidden backend intelligence
- cleaner producer interface
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
# OPTIONAL INSTAGRAM ANALYTICS CONNECTOR
# --------------------------------------------------
def safe_json_loads(value: str, default: Any) -> Any:
    try:
        if not value:
            return default
        return json.loads(value)
    except Exception:
        return default


def graph_api_get(path: str, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
    base_url = "https://graph.facebook.com/v20.0"
    query = dict(params or {})
    query["access_token"] = access_token
    url = f"{base_url}/{path.lstrip('/')}?{urlencode(query)}"
    request = Request(url, headers={"User-Agent": "KoocesterViralGenerator/1.0"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def get_instagram_user_id_for_page(page_data: Dict[str, Any]) -> str:
    mapping_raw = st.secrets.get("IG_USER_ID_MAP_JSON", "") or os.getenv("IG_USER_ID_MAP_JSON", "")
    mapping = safe_json_loads(mapping_raw, {})
    return str(mapping.get(page_data.get("internal_key", ""), "")).strip()


def fetch_instagram_live_analytics(page_data: Dict[str, Any], limit: int = 12) -> Dict[str, Any]:
    access_token = st.secrets.get("META_ACCESS_TOKEN", "") or os.getenv("META_ACCESS_TOKEN", "")
    ig_user_id = get_instagram_user_id_for_page(page_data)

    if not access_token or not ig_user_id:
        return {
            "connected": False,
            "status": "Live Instagram analytics not connected. Add META_ACCESS_TOKEN and IG_USER_ID_MAP_JSON in Streamlit secrets to enable own-account analytics.",
            "media": [],
        }

    try:
        media_response = graph_api_get(
            f"{ig_user_id}/media",
            {
                "fields": "id,caption,media_type,permalink,timestamp,like_count,comments_count",
                "limit": limit,
            },
            access_token,
        )

        enriched_items = []
        for item in media_response.get("data", []):
            media_id = item.get("id")
            insights = {}
            if media_id:
                try:
                    insight_response = graph_api_get(
                        f"{media_id}/insights",
                        {"metric": "reach,saved,shares,total_interactions"},
                        access_token,
                    )
                    for metric in insight_response.get("data", []):
                        values = metric.get("values", [])
                        if values:
                            insights[metric.get("name", "")] = values[0].get("value")
                except Exception as insight_error:
                    insights["insight_error"] = str(insight_error)

            enriched = dict(item)
            enriched["insights"] = insights
            enriched_items.append(enriched)

        return {
            "connected": True,
            "status": "Live own-account Instagram analytics connected through Meta API. This analyzes Koocester account media only, not all public Instagram trends.",
            "media": enriched_items,
        }
    except Exception as error:
        return {
            "connected": False,
            "status": f"Instagram analytics fetch failed: {error}",
            "media": [],
        }


def summarize_live_analytics_for_prompt(live_data: Dict[str, Any]) -> str:
    if not live_data.get("connected"):
        return live_data.get("status", "Live analytics unavailable.")

    media = live_data.get("media", [])
    if not media:
        return "Live analytics connected, but no recent media data returned."

    scored = []
    for item in media:
        insights = item.get("insights", {}) or {}
        likes = item.get("like_count") or 0
        comments = item.get("comments_count") or 0
        saved = insights.get("saved") or 0
        shares = insights.get("shares") or 0
        total_interactions = insights.get("total_interactions") or (likes + comments + saved + shares)
        score = (likes * 1) + (comments * 3) + (saved * 4) + (shares * 5) + (total_interactions * 1)
        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)

    lines = [live_data.get("status", "Live analytics connected.")]
    lines.append("Top recent Koocester media signals from connected account:")
    for rank, (score, item) in enumerate(scored[:8], start=1):
        caption = (item.get("caption") or "").replace("\n", " ").strip()
        if len(caption) > 180:
            caption = caption[:180] + "..."
        insights = item.get("insights", {}) or {}
        lines.append(
            f"{rank}. Score={score}; type={item.get('media_type')}; likes={item.get('like_count')}; "
            f"comments={item.get('comments_count')}; reach={insights.get('reach', 'n/a')}; "
            f"saved={insights.get('saved', 'n/a')}; shares={insights.get('shares', 'n/a')}; "
            f"caption={caption}; link={item.get('permalink')}"
        )

    return "\n".join(lines)


# --------------------------------------------------
# LATEST VIRAL TREND FEED CONNECTOR
# --------------------------------------------------
def parse_datetime_safe(value: str) -> datetime | None:
    if not value:
        return None
    try:
        normalized = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def normalize_trend_item(item: Dict[str, Any]) -> Dict[str, Any]:
    posted_at = parse_datetime_safe(str(item.get("posted_at") or item.get("timestamp") or item.get("date") or ""))
    now = datetime.now(timezone.utc)
    age_days = None
    if posted_at:
        age_days = max(0, (now - posted_at).days)

    views = int(item.get("views") or item.get("play_count") or item.get("view_count") or 0)
    likes = int(item.get("likes") or item.get("like_count") or 0)
    comments = int(item.get("comments") or item.get("comment_count") or 0)
    shares = int(item.get("shares") or item.get("share_count") or 0)
    saves = int(item.get("saves") or item.get("save_count") or 0)

    engagement_score = (likes * 1) + (comments * 3) + (shares * 5) + (saves * 4)
    if views > 0:
        engagement_rate = round(engagement_score / views, 4)
    else:
        engagement_rate = 0

    velocity_score = engagement_score
    if age_days is not None:
        velocity_score = round(engagement_score / max(age_days + 1, 1), 2)

    if age_days is not None and age_days <= 7:
        recency_bucket = "viral_now_candidate"
    elif age_days is not None and age_days <= 14:
        recency_bucket = "rising_candidate"
    elif age_days is not None and age_days <= 30:
        recency_bucket = "pattern_validation_only"
    else:
        recency_bucket = "too_old_ignore_unless_repeated"

    normalized = dict(item)
    normalized.update(
        {
            "posted_at_parsed": posted_at.isoformat() if posted_at else "",
            "age_days": age_days,
            "views": views,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "saves": saves,
            "engagement_score": engagement_score,
            "engagement_rate": engagement_rate,
            "velocity_score": velocity_score,
            "recency_bucket": recency_bucket,
        }
    )
    return normalized


def fetch_latest_trend_feed(page_data: Dict[str, Any], platform: str, limit: int = 40, manual_trend_json: str = "", run_live_scraper: bool = False) -> Dict[str, Any]:
    """
    Optional external trend feed.

    Add one of these to Streamlit secrets:
    TREND_FEED_API_URL = "https://your-trend-provider.com/api/latest"
    or
    TREND_FEED_JSON = "[{...}, {...}]"

    Expected item fields can include:
    title, url, caption, posted_at, views, likes, comments, shares, saves,
    country/market, niche, platform, account, format.
    """
    market = page_data.get("market", "")
    niche_key = page_data.get("internal_key", "")
    feed_url = st.secrets.get("TREND_FEED_API_URL", "") or os.getenv("TREND_FEED_API_URL", "")
    feed_json = manual_trend_json.strip() or st.secrets.get("TREND_FEED_JSON", "") or os.getenv("TREND_FEED_JSON", "")

    raw_items: List[Dict[str, Any]] = []

    if run_live_scraper:
        apify_data = fetch_apify_instagram_trends(page_data, platform, limit=limit)
        if apify_data.get("connected") and apify_data.get("items"):
            return apify_data
        if not feed_url and not feed_json:
            return apify_data

    if feed_url:
        try:
            query = urlencode({"market": market, "niche": niche_key, "platform": platform, "limit": limit})
            request = Request(f"{feed_url}?{query}", headers={"User-Agent": "KoocesterTrendScanner/1.0"})
            with urlopen(request, timeout=25) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if isinstance(payload, dict):
                    raw_items = payload.get("items") or payload.get("data") or []
                elif isinstance(payload, list):
                    raw_items = payload
        except Exception as error:
            return {
                "connected": False,
                "status": f"Trend feed fetch failed: {error}",
                "items": [],
            }
    elif feed_json:
        payload = safe_json_loads(feed_json, [])
        if isinstance(payload, dict):
            raw_items = payload.get("items") or payload.get("data") or []
        elif isinstance(payload, list):
            raw_items = payload

    if not raw_items:
        return {
            "connected": False,
            "status": "No live SG/MY Instagram viral scanner connected yet. The engine cannot truly detect what is currently exploding on Instagram until a real trend feed provider is connected. Add TREND_FEED_API_URL, TREND_FEED_JSON, or manual latest trend JSON.",
            "items": [],
        }

    normalized_items = [normalize_trend_item(item) for item in raw_items if isinstance(item, dict)]

    filtered_items = []
    for item in normalized_items:
        item_market = str(item.get("market") or item.get("country") or "").lower()
        item_platform = str(item.get("platform") or "").lower()
        age_days = item.get("age_days")

        if item_market and market.lower() not in item_market and item_market not in market.lower():
            continue
        if item_platform and platform.lower() not in item_platform:
            continue
        if age_days is not None and age_days > 30:
            continue

        filtered_items.append(item)

    filtered_items.sort(key=lambda item: (item.get("recency_bucket") != "viral_now_candidate", -item.get("velocity_score", 0)))

    return {
        "connected": True,
        "status": "Latest trend feed connected. Recency filter active: 0-7 days viral now, 8-14 days rising, 15-30 days validation only.",
        "items": filtered_items[:limit],
    }




def apify_actor_id_for_url(actor: str) -> str:
    return actor.strip().replace("/", "~")


def build_apify_scrape_urls(page_data: Dict[str, Any]) -> List[str]:
    """Build a smaller, cleaner source list so Apify returns real posts instead of only profile rows.

    Important:
    - Profile URLs are better than /reels/ URLs for apify/instagram-scraper.
    - Limit the amount of sources per run to reduce timeout risk.
    - Hashtags are useful, but they can be slower, so keep them limited.
    """
    urls: List[str] = []

    max_profiles = int(st.secrets.get("APIFY_MAX_PROFILES", "6") or 6)
    max_hashtags = int(st.secrets.get("APIFY_MAX_HASHTAGS", "3") or 3)

    for username in get_tracked_pages_for_page(page_data)[:max_profiles]:
        clean = username.strip().lstrip("@").strip("/")
        if clean:
            urls.append(f"https://www.instagram.com/{clean}/")

    for hashtag in get_tracked_hashtags_for_page(page_data)[:max_hashtags]:
        clean_tag = hashtag.strip().lstrip("#").strip("/")
        if clean_tag:
            urls.append(f"https://www.instagram.com/explore/tags/{clean_tag}/")

    # remove duplicates while preserving order
    seen = set()
    deduped = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def normalize_apify_item(item: Dict[str, Any], page_data: Dict[str, Any], platform: str) -> Dict[str, Any]:
    owner = (
        item.get("ownerUsername")
        or item.get("username")
        or item.get("owner")
        or item.get("account")
        or item.get("profileName")
        or item.get("ownerFullName")
        or ""
    )

    shortcode = item.get("shortCode") or item.get("shortcode") or item.get("code") or ""
    url = (
        item.get("url")
        or item.get("permalink")
        or item.get("inputUrl")
        or (f"https://www.instagram.com/reel/{shortcode}/" if shortcode else "")
    )

    caption = item.get("caption") or item.get("text") or item.get("title") or item.get("alt") or ""
    timestamp = (
        item.get("timestamp")
        or item.get("takenAt")
        or item.get("taken_at")
        or item.get("postedAt")
        or item.get("date")
        or item.get("createdAt")
        or ""
    )

    views = item.get("videoViewCount") or item.get("videoPlayCount") or item.get("playCount") or item.get("views") or item.get("viewCount") or item.get("video_view_count") or 0
    likes = item.get("likesCount") or item.get("likes") or item.get("likeCount") or item.get("likes_count") or 0
    comments = item.get("commentsCount") or item.get("comments") or item.get("commentCount") or item.get("comments_count") or 0
    shares = item.get("sharesCount") or item.get("shares") or item.get("shareCount") or 0
    saves = item.get("savesCount") or item.get("saves") or item.get("saveCount") or 0

    # If Apify returns only the input source URL, it is not a real reel/post result.
    source_only = False
    if url:
        lowered_url = url.lower().rstrip("/")
        source_only = lowered_url.endswith("/reels") or "/explore/tags/" in lowered_url

    has_real_post_signal = bool(shortcode or caption or int(views or 0) or int(likes or 0) or int(comments or 0)) and not source_only

    return {
        "title": caption[:120] if caption else f"Instagram reel/post from @{owner or 'unknown'}",
        "caption": caption,
        "posted_at": timestamp,
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "saves": saves,
        "market": page_data.get("market", ""),
        "platform": platform,
        "account": owner or "unknown",
        "source": "apify_instagram_scraper",
        "url": url,
        "shortcode": shortcode,
        "niche": page_data.get("internal_key", ""),
        "has_real_post_signal": has_real_post_signal,
        "raw_keys": sorted(list(item.keys()))[:40],
    }


def fetch_apify_instagram_trends(page_data: Dict[str, Any], platform: str, limit: int = 40) -> Dict[str, Any]:
    token = st.secrets.get("APIFY_API_TOKEN", "") or os.getenv("APIFY_API_TOKEN", "")
    actor = st.secrets.get("APIFY_INSTAGRAM_ACTOR", "") or os.getenv("APIFY_INSTAGRAM_ACTOR", "apify/instagram-scraper")
    input_field = st.secrets.get("APIFY_INPUT_FIELD", "") or os.getenv("APIFY_INPUT_FIELD", "directUrls")

    try:
        results_limit = int(st.secrets.get("APIFY_RESULTS_LIMIT", "") or os.getenv("APIFY_RESULTS_LIMIT", str(limit)))
    except Exception:
        results_limit = limit

    if not token:
        return {
            "connected": False,
            "status": "Apify trend scanner not connected. Add APIFY_API_TOKEN in Streamlit secrets.",
            "items": [],
        }

    urls = build_apify_scrape_urls(page_data)
    if not urls:
        return {
            "connected": False,
            "status": "No tracked Instagram pages or hashtags are mapped for this selected Koocester page.",
            "items": [],
        }

    actor_id = apify_actor_id_for_url(actor)
    endpoint = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items?token={token}"

    # Keep the input broad enough for the public Apify Instagram actor, but small enough to avoid Streamlit timeout.
    base_input = {
        "resultsLimit": results_limit,
        "resultsType": st.secrets.get("APIFY_RESULTS_TYPE", "posts") or "posts",
        "searchLimit": results_limit,
        "addParentData": False,
    }

    if input_field == "startUrls":
        actor_input = {**base_input, "startUrls": [{"url": url} for url in urls]}
    elif input_field == "urls":
        actor_input = {**base_input, "urls": urls}
    else:
        actor_input = {**base_input, "directUrls": urls}

    try:
        request = Request(
            endpoint,
            data=json.dumps(actor_input).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "KoocesterApifyTrendScanner/1.0"},
            method="POST",
        )

        with urlopen(request, timeout=180) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if isinstance(payload, dict):
            raw_items = payload.get("items") or payload.get("data") or []
        elif isinstance(payload, list):
            raw_items = payload
        else:
            raw_items = []

        normalized_all = [normalize_apify_item(item, page_data, platform) for item in raw_items if isinstance(item, dict)]

        # Remove source-only rows like https://instagram.com/page/reels/ with no metrics.
        normalized_real = [item for item in normalized_all if item.get("has_real_post_signal")]

        if not normalized_real:
            return {
                "connected": False,
                "status": (
                    f"Apify connected, but returned {len(normalized_all)} source rows and 0 usable reel/post rows. "
                    "This usually means the actor/input setting is wrong or the selected sources are not returning public post data. "
                    "Try APIFY_INSTAGRAM_ACTOR='apify/instagram-scraper', APIFY_INPUT_FIELD='directUrls', APIFY_RESULTS_LIMIT='15'."
                ),
                "items": [],
                "raw_count": len(raw_items),
                "tracked_pages": get_tracked_pages_for_page(page_data),
                "tracked_hashtags": get_tracked_hashtags_for_page(page_data),
                "scrape_urls": urls,
            }

        normalized = [normalize_trend_item(item) for item in normalized_real]
        normalized = sorted(
            normalized,
            key=lambda item: (
                item.get("recency_bucket") != "viral_now_candidate",
                -(item.get("velocity_score") or 0),
                -(item.get("views") or 0),
                -(item.get("likes") or 0),
                -(item.get("comments") or 0),
            ),
        )

        return {
            "connected": True,
            "status": f"Live Apify Instagram scraper connected. Found {len(normalized)} raw usable reel/post items from {len(urls)} sources for {page_data.get('market')} / {page_data.get('internal_key')}. Post-level Koocester relevance filtering is applied before results are shown.",
            "items": normalized[:results_limit],
            "raw_count": len(raw_items),
            "usable_count": len(normalized),
            "tracked_pages": get_tracked_pages_for_page(page_data),
            "tracked_hashtags": get_tracked_hashtags_for_page(page_data),
            "scrape_urls": urls,
        }
    except Exception as error:
        return {
            "connected": False,
            "status": f"Apify Instagram scraper failed: {error}",
            "items": [],
            "tracked_pages": get_tracked_pages_for_page(page_data),
            "tracked_hashtags": get_tracked_hashtags_for_page(page_data),
            "scrape_urls": urls,
        }


def summarize_latest_trends_for_prompt(trend_data: Dict[str, Any]) -> str:
    if not trend_data.get("connected"):
        return trend_data.get("status", "Latest trend feed unavailable.")

    items = trend_data.get("items", [])
    if not items:
        return "Latest trend feed connected, but no matching recent items found for this page, market, and platform."

    buckets = {
        "viral_now_candidate": [],
        "rising_candidate": [],
        "pattern_validation_only": [],
    }

    for item in items:
        bucket = item.get("recency_bucket", "pattern_validation_only")
        if bucket in buckets:
            buckets[bucket].append(item)

    lines = [trend_data.get("status", "Latest trend feed connected.")]
    labels = {
        "viral_now_candidate": "Viral now candidates, posted within 7 days",
        "rising_candidate": "Rising candidates, posted within 14 days",
        "pattern_validation_only": "Pattern validation only, posted within 30 days",
    }

    for bucket, label in labels.items():
        lines.append(label + ":")
        for rank, item in enumerate(buckets.get(bucket, [])[:8], start=1):
            title = str(item.get("title") or item.get("format") or item.get("caption") or "Untitled").replace("\n", " ")
            if len(title) > 150:
                title = title[:150] + "..."
            lines.append(
                f"{rank}. age_days={item.get('age_days')}; views={item.get('views')}; "
                f"likes={item.get('likes')}; comments={item.get('comments')}; shares={item.get('shares')}; "
                f"saves={item.get('saves')}; velocity={item.get('velocity_score')}; "
                f"engagement_rate={item.get('engagement_rate')}; title={title}; url={item.get('url') or item.get('permalink') or ''}"
            )

    return "\n".join(lines)




# --------------------------------------------------
# REAL VIRAL INSTAGRAM SCAN OUTPUT — POST-LEVEL PRODUCER VERSION
# --------------------------------------------------
def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def format_number(value: Any) -> str:
    """Format large metrics into producer-friendly labels."""
    value = safe_int(value)
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def format_posted_recency(age_days: Any) -> str:
    """Professional replacement for 'Age Days'."""
    if age_days is None:
        return "Date unavailable"
    try:
        age_days = int(age_days)
    except Exception:
        return "Date unavailable"

    if age_days == 0:
        return "Posted today"
    if age_days == 1:
        return "Posted 1 day ago"
    return f"Posted {age_days} days ago"


POST_INTENT_RULES = {
    "autos": {
        "strong": [
            "buy", "buying", "buyer", "buyers", "own", "owner", "ownership", "drive", "driving",
            "test drive", "viewing", "price", "cost", "worth", "review", "comparison", "compare",
            "spec", "specs", "interior", "engine", "horsepower", "luxury car", "supercar", "sedan",
            "suv", "porsche", "mercedes", "bmw", "audi", "ferrari", "lamborghini", "brabus",
            "mclaren", "tesla", "daily driver", "delivery", "car collection", "showroom",
        ],
        "producer": [
            "pov", "first drive", "delivery day", "walkaround", "interior tour", "exterior", "sound",
            "startup", "0-100", "ownership experience", "dream car", "finance", "installment",
        ],
        "bad": [
            "hotel", "resort", "beach", "outfit", "makeup", "food", "party", "vacation", "monaco for a very special", "airport lounge"],
        "minimum": 3,
    },
    "autos_my": {
        "strong": [
            "buy", "buying", "buyer", "buyers", "own", "owner", "ownership", "drive", "driving",
            "test drive", "viewing", "price", "cost", "worth", "review", "comparison", "compare",
            "spec", "specs", "interior", "engine", "horsepower", "luxury car", "supercar", "sedan",
            "suv", "porsche", "mercedes", "bmw", "audi", "ferrari", "lamborghini", "brabus",
            "mclaren", "tesla", "daily driver", "delivery", "car collection", "showroom", "kereta",
        ],
        "producer": [
            "pov", "first drive", "delivery day", "walkaround", "interior tour", "exterior", "sound",
            "startup", "0-100", "ownership experience", "dream car", "finance", "installment",
        ],
        "bad": ["hotel", "resort", "beach", "outfit", "makeup", "food", "party", "vacation", "airport lounge"],
        "minimum": 3,
    },
    "homes": {
        "strong": [
            "home", "house", "condo", "property", "renovation", "reno", "interior", "layout", "space",
            "before", "after", "kitchen", "living room", "bedroom", "bathroom", "landed", "hdb",
            "bto", "apartment", "tour", "walkthrough", "design", "renovate", "homeowner", "buyer",
        ],
        "producer": ["home tour", "before and after", "layout mistake", "storage", "small space", "budget", "transformation"],
        "bad": ["car", "supercar", "makeup", "party", "food review", "hotel vacation"],
        "minimum": 3,
    },
    "homes_my": {
        "strong": [
            "home", "house", "condo", "property", "renovation", "reno", "interior", "layout", "space",
            "before", "after", "kitchen", "living room", "bedroom", "bathroom", "landed", "apartment",
            "tour", "walkthrough", "design", "renovate", "homeowner", "buyer", "rumah", "kl property",
        ],
        "producer": ["home tour", "before and after", "layout mistake", "storage", "small space", "budget", "transformation"],
        "bad": ["car", "supercar", "makeup", "party", "food review", "hotel vacation"],
        "minimum": 3,
    },
    "business": {
        "strong": [
            "founder", "business", "entrepreneur", "startup", "owner", "ceo", "sales", "growth", "networking",
            "client", "customers", "profit", "revenue", "marketing", "lead", "strategy", "operator", "SME".lower(),
            "event", "conference", "investor", "pitch", "team", "hiring", "brand",
        ],
        "producer": ["founder lesson", "hard truth", "business mistake", "networking", "operator", "case study", "growth lesson"],
        "bad": ["makeup", "food", "beach", "hotel", "car review", "home tour"],
        "minimum": 3,
    },
    "business_my": {
        "strong": [
            "founder", "business", "entrepreneur", "startup", "owner", "ceo", "sales", "growth", "networking",
            "client", "customers", "profit", "revenue", "marketing", "lead", "strategy", "operator", "sme",
            "event", "conference", "investor", "pitch", "team", "hiring", "brand", "usahawan",
        ],
        "producer": ["founder lesson", "hard truth", "business mistake", "networking", "operator", "case study", "growth lesson"],
        "bad": ["makeup", "food", "beach", "hotel", "car review", "home tour"],
        "minimum": 3,
    },
    "main": {
        "strong": ["premium", "event", "founder", "community", "lifestyle", "experience", "network", "luxury", "social", "brand", "story"],
        "producer": ["social proof", "premium event", "community", "story", "moment", "behind the scenes"],
        "bad": ["random meme", "gaming", "politics"],
        "minimum": 2,
    },
}


def get_intent_rules(page_data: Dict[str, Any]) -> Dict[str, Any]:
    key = page_data.get("internal_key", "main")
    return POST_INTENT_RULES.get(key, POST_INTENT_RULES["main"])


def calculate_post_relevance(item: Dict[str, Any], page_data: Dict[str, Any]) -> Tuple[int, List[str], List[str]]:
    """Score the actual post, not just the account.

    This prevents random posts from car/luxury accounts from being treated as useful Koocester references.
    """
    rules = get_intent_rules(page_data)
    text = " ".join(
        str(item.get(k) or "")
        for k in ["caption", "title", "account", "url", "shortcode"]
    ).lower()

    matched: List[str] = []
    bad_hits: List[str] = []
    score = 0

    for word in rules.get("strong", []):
        if word and word.lower() in text:
            matched.append(word)
            score += 12

    for word in rules.get("producer", []):
        if word and word.lower() in text:
            matched.append(word)
            score += 18

    for word in rules.get("bad", []):
        if word and word.lower() in text:
            bad_hits.append(word)
            score -= 20

    # Account source helps, but should never be enough by itself.
    account = str(item.get("account") or "").lower().lstrip("@")
    if account in [p.lower().lstrip("@") for p in get_tracked_pages_for_page(page_data)]:
        # Being from a carefully selected tracked profile should help more,
        # but it still should not be the only reason a post is accepted.
        score += 18

    # Public performance signals add confidence, but relevance remains the gatekeeper.
    if safe_int(item.get("views")) >= 50_000:
        score += 8
    if safe_int(item.get("comments")) >= 100:
        score += 6
    if item.get("age_days") is not None and safe_int(item.get("age_days")) <= 7:
        score += 6

    return max(0, min(score, 100)), sorted(set(matched)), sorted(set(bad_hits))


def producer_value_score(item: Dict[str, Any], page_data: Dict[str, Any]) -> int:
    score = 35
    retention = retention_trigger(item, page_data).lower()
    hook = hook_strength(item).lower()
    caption = (item.get("caption") or item.get("title") or "").lower()

    if "strong" in hook:
        score += 20
    elif "decent" in hook:
        score += 10

    if any(term in retention for term in ["tension", "curiosity", "cost", "decision"]):
        score += 15

    if any(word in caption for word in ["before", "after", "pov", "mistake", "worth", "why", "how", "tour", "review"]):
        score += 15

    if safe_int(item.get("comments")) >= 50:
        score += 8
    if safe_int(item.get("likes")) >= 1000:
        score += 7

    return max(0, min(score, 100))


def virality_probability(item: Dict[str, Any]) -> Tuple[int, str]:
    """Estimate breakout potential from public metrics returned by scraper."""
    views = safe_int(item.get("views"))
    likes = safe_int(item.get("likes"))
    comments = safe_int(item.get("comments"))
    shares = safe_int(item.get("shares"))
    saves = safe_int(item.get("saves"))
    age_days = item.get("age_days")

    score = 25

    if views >= 1_000_000:
        score += 30
    elif views >= 500_000:
        score += 25
    elif views >= 100_000:
        score += 18
    elif views >= 30_000:
        score += 10
    elif views >= 10_000:
        score += 5

    if likes >= 25_000:
        score += 18
    elif likes >= 10_000:
        score += 14
    elif likes >= 3_000:
        score += 9
    elif likes >= 1_000:
        score += 5

    if comments >= 1_000:
        score += 14
    elif comments >= 500:
        score += 11
    elif comments >= 100:
        score += 7
    elif comments >= 30:
        score += 4

    score += min(10, (shares // 100) + (saves // 100))

    if age_days is not None:
        age_days_int = safe_int(age_days, 999)
        if age_days_int <= 3:
            score += 12
        elif age_days_int <= 7:
            score += 8
        elif age_days_int <= 14:
            score += 4

    score = max(0, min(score, 95))

    if score >= 82:
        label = "High breakout potential"
    elif score >= 65:
        label = "Strong rising potential"
    elif score >= 48:
        label = "Moderate potential"
    else:
        label = "Weak/early signal"

    return score, label


def final_fit_score(item: Dict[str, Any], page_data: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    viral_score, viral_label = virality_probability(item)
    relevance_score, matched, bad_hits = calculate_post_relevance(item, page_data)
    producer_score = producer_value_score(item, page_data)

    final_score = round((viral_score * 0.40) + (relevance_score * 0.42) + (producer_score * 0.18))
    debug = {
        "viral_score": viral_score,
        "viral_label": viral_label,
        "relevance_score": relevance_score,
        "producer_score": producer_score,
        "matched_terms": matched,
        "negative_terms": bad_hits,
    }
    return max(0, min(final_score, 100)), debug


def should_keep_post(item: Dict[str, Any], page_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Decide whether a scraped Instagram post should be shown.

    This version is intentionally softer than the old one. Instagram captions are often
    short, messy, or visual-first, so requiring 3 exact niche keyword matches rejects
    too many usable posts.
    """
    final_score, debug = final_fit_score(item, page_data)
    matched_count = len(debug.get("matched_terms", []))
    bad_count = len(debug.get("negative_terms", []))
    relevance_score = debug.get("relevance_score", 0)
    producer_score = debug.get("producer_score", 0)
    viral_score = debug.get("viral_score", 0)

    # Only reject immediately when it is clearly off-niche and has no positive signal.
    if bad_count >= 2 and matched_count == 0:
        return False, "Rejected: clearly off-niche lifestyle signals with no niche match.", debug

    # If there are no matched terms, still allow strong posts from tracked sources
    # when performance/producer value is decent.
    if matched_count == 0 and relevance_score < 12 and final_score < 35 and producer_score < 50 and viral_score < 55:
        return False, "Rejected: too little niche relevance or usable viral/producer signal.", debug

    # Lower combined threshold so the scan does not become empty too easily.
    if final_score < 30:
        return False, "Rejected: weak combined viral/relevance/producer-value score.", debug

    return True, "Accepted: enough niche relevance, viral signal, or producer value.", debug


def enrich_scanned_item(item: Dict[str, Any], page_data: Dict[str, Any]) -> Dict[str, Any]:
    keep, decision_reason, debug = should_keep_post(item, page_data)
    final_score, _ = final_fit_score(item, page_data)
    enriched = dict(item)
    enriched.update(
        {
            "koocester_keep": keep,
            "koocester_decision_reason": decision_reason,
            "koocester_final_score": final_score,
            "koocester_relevance_score": debug.get("relevance_score", 0),
            "producer_value_score": debug.get("producer_score", 0),
            "matched_terms": debug.get("matched_terms", []),
            "negative_terms": debug.get("negative_terms", []),
            "viral_score": debug.get("viral_score", 0),
            "viral_label": debug.get("viral_label", ""),
        }
    )
    return enriched


def hook_strength(item: Dict[str, Any]) -> str:
    caption = (item.get("caption") or item.get("title") or "").lower()
    strong_words = [
        "mistake", "regret", "truth", "secret", "hidden", "before", "why", "nobody",
        "stop", "avoid", "cost", "expensive", "worth", "cheap", "owner", "founder",
        "renovation", "property", "business", "million", "best", "worst", "problem", "solution",
    ]
    hits = sum(1 for word in strong_words if word in caption)
    if hits >= 3:
        return "Strong hook"
    if hits >= 1:
        return "Decent hook"
    return "Weak/unclear hook"


def retention_trigger(item: Dict[str, Any], page_data: Dict[str, Any]) -> str:
    niche = page_data.get("internal_key", "")
    caption = (item.get("caption") or item.get("title") or "").lower()

    if any(word in caption for word in ["mistake", "regret", "avoid", "before"]):
        return "Mistake/regret tension"
    if any(word in caption for word in ["secret", "hidden", "nobody", "truth"]):
        return "Curiosity gap"
    if any(word in caption for word in ["worth", "cheap", "expensive", "cost", "price"]):
        return "Value/cost tension"
    if niche in ["homes", "homes_my"]:
        return "Homeowner decision / transformation tension"
    if niche in ["autos", "autos_my"]:
        return "Buyer decision / ownership desire tension"
    if niche in ["business", "business_my"]:
        return "Founder lesson / business opinion tension"
    return "Lifestyle discovery / social proof"


def content_type_label(item: Dict[str, Any], page_data: Dict[str, Any]) -> str:
    caption = (item.get("caption") or item.get("title") or "").lower()
    niche = page_data.get("internal_key", "")

    if any(w in caption for w in ["mistake", "regret", "avoid", "before"]):
        return "Decision-risk content"
    if any(w in caption for w in ["pov", "drive", "ownership", "owner"]):
        return "Ownership/POV content"
    if any(w in caption for w in ["tour", "walkthrough", "before", "after"]):
        return "Tour/transformation content"
    if any(w in caption for w in ["founder", "business", "lesson", "growth"]):
        return "Founder/business lesson"
    if niche in ["autos", "autos_my"]:
        return "Auto buyer-interest content"
    if niche in ["homes", "homes_my"]:
        return "Home/property-interest content"
    if niche in ["business", "business_my"]:
        return "Business operator-interest content"
    return "Premium discovery content"


def producer_insight(item: Dict[str, Any], page_data: Dict[str, Any]) -> str:
    niche = page_data.get("internal_key", "")
    probability_score, probability_label = virality_probability(item)
    matched = item.get("matched_terms") or calculate_post_relevance(item, page_data)[1]

    if niche in ["homes", "homes_my"]:
        base = "Producer value: use this to study the opening room shot, walkthrough pacing, homeowner problem, and reveal/payoff timing."
    elif niche in ["autos", "autos_my"]:
        base = "Producer value: use this to study buyer curiosity, ownership desire, car-detail sequencing, POV shots, and narration angle."
    elif niche in ["business", "business_my"]:
        base = "Producer value: use this to study the first opinion/lesson, founder credibility, room energy, and comment-triggering angle."
    else:
        base = "Producer value: use this to study the first 2 seconds, social proof, scene selection, and premium perception."

    if matched:
        base += f" Matching signals: {', '.join(matched[:6])}."
    if safe_int(item.get("views")) >= 100_000:
        base += " Strong validation: the reach suggests this format has moved beyond normal niche reach."
    elif safe_int(item.get("comments")) >= 100:
        base += " Discussion signal: comments suggest the topic creates reaction, useful for engagement-led content."
    else:
        base += f" Treat as a {probability_label.lower()} reference unless stronger metrics appear."

    return base


def koocester_fit_reason(item: Dict[str, Any], page_data: Dict[str, Any]) -> str:
    market = page_data.get("market", "")
    niche = page_data.get("internal_key", "")
    relevance = item.get("koocester_relevance_score", calculate_post_relevance(item, page_data)[0])

    if niche in ["autos", "autos_my"]:
        return f"Fits Koocester Autos only if it supports car buyer psychology, ownership desire, viewing intent, or premium car decision content for {market}. Relevance score: {relevance}/100."
    if niche in ["homes", "homes_my"]:
        return f"Fits Koocester Homes only if it supports renovation, property, layout, homeowner pain, or save-worthy home decision content for {market}. Relevance score: {relevance}/100."
    if niche in ["business", "business_my"]:
        return f"Fits Koocester Business only if it supports founder, SME, networking, operator, or business-growth content for {market}. Relevance score: {relevance}/100."
    return f"Fits Koocester Main only if it supports premium lifestyle, event, founder, discovery, or social-proof content for {market}. Relevance score: {relevance}/100."


def diversify_by_profile(items: List[Dict[str, Any]], max_per_profile: int = 2) -> List[Dict[str, Any]]:
    """Prevent one Instagram profile from dominating the scan result."""
    profile_counts: Dict[str, int] = {}
    diversified: List[Dict[str, Any]] = []

    for item in items:
        account = str(item.get("account") or "unknown").lower()
        current_count = profile_counts.get(account, 0)
        if current_count < max_per_profile:
            diversified.append(item)
            profile_counts[account] = current_count + 1
    return diversified


def render_source_health(items: List[Dict[str, Any]]) -> None:
    accounts = {}
    for item in items:
        account = str(item.get("account") or "unknown")
        accounts[account] = accounts.get(account, 0) + 1

    if not accounts:
        return

    with st.expander("Profile diversity check", expanded=False):
        st.write("This prevents the scan from depending on only one creator/profile.")
        rows = [{"Profile": "@" + acc, "Posts Returned": count} for acc, count in sorted(accounts.items(), key=lambda x: x[1], reverse=True)]
        st.dataframe(rows, use_container_width=True, hide_index=True)


def render_rejected_posts(rejected_items: List[Dict[str, Any]]) -> None:
    if not rejected_items:
        return
    with st.expander("Rejected off-niche posts", expanded=False):
        st.write("These were scraped but removed because the actual post did not match Koocester's selected niche strongly enough.")
        rows = []
        for item in rejected_items[:30]:
            caption = (item.get("caption") or item.get("title") or "").replace("\n", " ").strip()
            if len(caption) > 120:
                caption = caption[:120] + "..."
            rows.append(
                {
                    "Profile": "@" + str(item.get("account") or "unknown"),
                    "Reason": item.get("koocester_decision_reason", "Rejected"),
                    "Relevance": item.get("koocester_relevance_score", 0),
                    "Negative Terms": ", ".join(item.get("negative_terms", [])),
                    "Caption": caption,
                    "Link": item.get("url") or item.get("permalink") or "",
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)


def render_real_viral_scan(trend_data: Dict[str, Any], page_name: str, page_data: Dict[str, Any]) -> None:
    st.divider()
    st.title("Koocester Live Viral Intelligence Scan")
    st.caption("Post-level matching: every result must match the selected Koocester page niche, not just come from a related account.")

    raw_items = trend_data.get("items", []) or []
    tracked_pages = trend_data.get("tracked_pages", []) or get_tracked_pages_for_page(page_data)
    tracked_hashtags = trend_data.get("tracked_hashtags", []) or get_tracked_hashtags_for_page(page_data)

    enriched_items = [enrich_scanned_item(item, page_data) for item in raw_items]
    accepted_items = [item for item in enriched_items if item.get("koocester_keep")]
    rejected_items = [item for item in enriched_items if not item.get("koocester_keep")]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Scanner Status", "Connected" if trend_data.get("connected") else "Not connected")
    c2.metric("Accepted Posts", len(accepted_items))
    c3.metric("Rejected Off-Niche", len(rejected_items))
    c4.metric("Market", page_data.get("market", "-"))
    c5.metric("Page Niche", page_data.get("internal_key", "-"))

    if trend_data.get("connected") and raw_items:
        st.success(trend_data.get("status", "Scanner connected."))
    else:
        st.warning(trend_data.get("status", "Scanner not connected."))

    with st.expander("Sources scanned", expanded=False):
        st.write("**Tracked profiles:**")
        st.write(", ".join(["@" + p for p in tracked_pages]) if tracked_pages else "No tracked pages mapped.")
        st.write("**Tracked hashtags:**")
        st.write(", ".join(["#" + h for h in tracked_hashtags]) if tracked_hashtags else "No tracked hashtags mapped.")
        if trend_data.get("scrape_urls"):
            st.write("**Actual URLs sent to Apify:**")
            st.code("\n".join(trend_data.get("scrape_urls", [])), language="text")

    render_rejected_posts(rejected_items)

    if not trend_data.get("connected") or not raw_items:
        st.error("No usable Instagram posts were returned. Check Apify token, actor, input field, and source profiles.")
        st.info("Recommended secrets: APIFY_INSTAGRAM_ACTOR='apify/instagram-scraper', APIFY_INPUT_FIELD='directUrls', APIFY_RESULTS_LIMIT='40', APIFY_MAX_PROFILES='8'.")
        st.stop()

    if not accepted_items:
        st.error("The scraper returned posts, but all were rejected as off-niche or weak-fit. Add better niche profiles or loosen the relevance rules slightly.")
        st.stop()

    ranked_items = sorted(
        accepted_items,
        key=lambda x: (
            -(x.get("koocester_final_score") or 0),
            x.get("recency_bucket") != "viral_now_candidate",
            -(x.get("velocity_score") or 0),
            -(x.get("views") or 0),
            -(x.get("likes") or 0),
            -(x.get("comments") or 0),
        ),
    )

    diversified_items = diversify_by_profile(ranked_items, max_per_profile=2)

    total_views = sum(safe_int(i.get("views")) for i in diversified_items)
    total_likes = sum(safe_int(i.get("likes")) for i in diversified_items)
    total_comments = sum(safe_int(i.get("comments")) for i in diversified_items)
    avg_relevance = round(sum(safe_float(i.get("koocester_relevance_score")) for i in diversified_items) / max(len(diversified_items), 1), 1)

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Total Views Scanned", format_number(total_views))
    a2.metric("Total Likes", format_number(total_likes))
    a3.metric("Total Comments", format_number(total_comments))
    a4.metric("Avg Koocester Relevance", f"{avg_relevance}/100")

    st.subheader("Executive Scan Summary")
    st.markdown(
        f"""
**Selected page:** {page_name}  
**Market:** {page_data.get("market")}  
**Producer objective:** Find real posts/reels that match Koocester's actual niche and show viral or rising signals.  
**Post-level rule:** A reel must match the content intent, not just come from a related profile.  
**Diversity rule:** Maximum 2 posts per profile, so one account cannot dominate the scan.
"""
    )

    render_source_health(diversified_items)

    table_rows = []
    for item in diversified_items[:40]:
        caption = (item.get("caption") or item.get("title") or "").replace("\n", " ").strip()
        if len(caption) > 140:
            caption = caption[:140] + "..."

        probability_score, probability_label = virality_probability(item)

        table_rows.append(
            {
                "Profile": "@" + str(item.get("account") or "unknown"),
                "Posted": format_posted_recency(item.get("age_days")),
                "Views": safe_int(item.get("views")),
                "Likes": safe_int(item.get("likes")),
                "Comments": safe_int(item.get("comments")),
                "Koocester Fit": item.get("koocester_final_score", 0),
                "Relevance": item.get("koocester_relevance_score", 0),
                "Producer Value": item.get("producer_value_score", 0),
                "Viral Probability": f"{probability_score}% - {probability_label}",
                "Content Type": content_type_label(item, page_data),
                "Retention Trigger": retention_trigger(item, page_data),
                "Matched Signals": ", ".join(item.get("matched_terms", [])[:5]),
                "Caption / Topic": caption,
                "Link": item.get("url") or item.get("permalink") or "",
            }
        )

    st.subheader("Ranked Koocester-Fit Viral / Rising Matches")
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    viral_now = [i for i in diversified_items if i.get("recency_bucket") == "viral_now_candidate"]
    rising = [i for i in diversified_items if i.get("recency_bucket") == "rising_candidate"]
    validation = [
        i for i in diversified_items
        if i.get("recency_bucket") == "pattern_validation_only" or i.get("age_days") is None
    ]

    def render_cards(title: str, data: List[Dict[str, Any]]) -> None:
        st.markdown(f"### {title}")

        if not data:
            st.info("No accepted posts in this section.")
            return

        for index, item in enumerate(data[:12], start=1):
            account = item.get("account") or "unknown"
            url = item.get("url") or item.get("permalink") or ""
            caption = (item.get("caption") or item.get("title") or "").replace("\n", " ").strip()
            if len(caption) > 260:
                caption = caption[:260] + "..."

            probability_score, probability_label = virality_probability(item)

            with st.container(border=True):
                top = st.columns([2.2, 1, 1, 1, 1])
                top[0].markdown(f"**{index}. @{account}**")
                top[1].metric("Views", format_number(item.get("views")))
                top[2].metric("Likes", format_number(item.get("likes")))
                top[3].metric("Comments", format_number(item.get("comments")))
                top[4].metric("Fit", f"{item.get('koocester_final_score', 0)}/100")

                st.write(caption if caption else "No caption returned by scraper.")

                m1, m2, m3, m4 = st.columns(4)
                m1.write(f"**Posted:** {format_posted_recency(item.get('age_days'))}")
                m2.write(f"**Viral Probability:** {probability_score}%")
                m3.write(f"**Relevance:** {item.get('koocester_relevance_score', 0)}/100")
                m4.write(f"**Signal:** {probability_label}")

                st.write(f"**Content Type:** {content_type_label(item, page_data)}")
                st.write(f"**Retention Trigger:** {retention_trigger(item, page_data)}")
                st.write(f"**Why this fits Koocester:** {koocester_fit_reason(item, page_data)}")
                st.write(f"**Producer Insight:** {producer_insight(item, page_data)}")
                if item.get("matched_terms"):
                    st.caption("Matched post-level signals: " + ", ".join(item.get("matched_terms", [])[:8]))

                if url:
                    st.link_button("Open Instagram Post/Reel", url)

    render_cards("Viral Now: accepted 0–7 day Koocester-fit posts", viral_now)
    render_cards("Rising / About-To-Go-Viral: accepted 8–14 day signals", rising)
    render_cards("Pattern Validation / Older or Unknown Date", validation)

    st.divider()
    st.subheader("Producer Takeaways")
    st.markdown(
        """
- Do not copy a creator because one post performed well. Extract the pattern: opening hook, shot sequence, caption promise, and emotional trigger.
- Prioritize posts with high **Koocester Fit**, not only likes.
- Use rejected posts to see what the engine removed as off-niche, then improve tracked sources if needed.
- For producers, the best references are specific, shootable, and tied to buyer/homeowner/founder decisions.
"""
    )


# PAGE INTELLIGENCE + CONFIRMED INSTAGRAM LINKS
# --------------------------------------------------
PAGE_INTELLIGENCE = {
    "Koocester Main": {
        "internal_key": "main",
        "market": "Singapore",
        "instagram_url": "https://www.instagram.com/koocester/",
        "audience": "Singapore lifestyle audience, aspirational viewers, young professionals, founders, social audience, premium discovery audience",
        "lead_type": "Brand engagement leads, ecosystem leads, premium awareness audience",
        "cta_intent": "discover Koocester, engage with the ecosystem, follow the brand, attend or explore premium experiences",
        "cta_keyword": "KOOCESTER",
        "tone": "Premium",
        "default_goal": "Awareness",
        "recommended_mode": "Brand-Led Viral Discovery",
        "recommended_length": "90 sec",
        "allowed_lengths": ["30 sec", "45 sec", "60 sec", "90 sec", "120 sec", "180 sec"],
        "niche_memory": "Premium Singapore lifestyle content, founder ecosystem exposure, discovery-led social content, brand-driven high-perception videos",
        "page_direction": "Broad Koocester brand content that should feel premium, sharp, culturally relevant to Singapore, and social-first.",
        "producer_question": "What moment, person, event, or experience has enough social/status pull to make people stop scrolling?",
        "success_definition": "Success means the content makes Koocester feel culturally relevant, premium, and worth following or engaging with.",
        "winning_formats": ["strong opinion hook", "event atmosphere with meaning", "social proof montage", "premium micro-story", "aspirational lifestyle cut", "curiosity-led discovery reel"],
        "viral_now": ["fast subtitle reels with premium cuts", "short social-proof clips with strong first sentence", "micro-story reels that reveal payoff early", "clean event reels with tension instead of generic recaps"],
        "rising_next": ["identity-based lifestyle hooks", "short documentary-style brand snippets", "community-status storytelling", "high-contrast before-vs-after perception edits"],
        "competitor_patterns": ["premium event recap with stronger tension in first 2 seconds", "bold statement before visuals fully establish context", "fast pacing with cleaner caption styling", "emotion + credibility combined quickly"],
    },
    "Koocester Business Singapore": {
        "internal_key": "business",
        "market": "Singapore",
        "instagram_url": "https://www.instagram.com/koocesterbusiness",
        "audience": "Singapore founders, business owners, operators, startup audience, networking audience, ambitious professionals",
        "lead_type": "Founder/event leads, networking leads, brand authority leads, business ecosystem leads",
        "cta_intent": "join better business rooms, connect with founders, attend business events, build authority and opportunities",
        "cta_keyword": "NETWORK",
        "tone": "Bold",
        "default_goal": "Leads",
        "recommended_mode": "Authority + Retention",
        "recommended_length": "90 sec",
        "allowed_lengths": ["30 sec", "45 sec", "60 sec", "90 sec", "120 sec", "180 sec", "240 sec"],
        "niche_memory": "Founder networking, business insight, business psychology, startup/operator talk, high-value rooms, social proof for serious founders",
        "page_direction": "Business content should feel intelligent, sharp, premium, opinionated when needed, and useful enough for founders to save or send.",
        "producer_question": "Why would this founder, company, room, or interview be worth watching instead of a generic business video?",
        "success_definition": "Success means founders or business owners feel this content gives useful insight, social proof, or access to better rooms.",
        "winning_formats": ["contrarian founder hook", "what founders get wrong", "high-value room vs low-value room comparison", "short founder lesson clip", "networking ROI explanation", "business myth breakdown"],
        "viral_now": ["hard-truth founder hooks", "anti-fluff networking breakdowns", "short clips exposing useless founder behavior", "high-status room analysis with strong subtitles"],
        "rising_next": ["operator confession format", "business lesson from one real moment", "event room psychology content", "comment-bait controversial founder opinions"],
        "competitor_patterns": ["most strong business reels start with tension immediately", "reels that compare bad vs good founder behavior perform better than generic motivation", "captions often stay short, sharp, and high-conviction", "strongest videos create disagreement early to drive comments"],
    },
    "Koocester Autos Singapore": {
        "internal_key": "autos",
        "market": "Singapore",
        "instagram_url": "https://www.instagram.com/koocesterautos",
        "audience": "Singapore car buyers, luxury car audience, aspirational viewers, enthusiasts, first-time premium buyers",
        "lead_type": "Premium buyer leads, showroom traffic leads, aspiration-driven leads",
        "cta_intent": "book a viewing, enquire about the car, imagine ownership, move closer to a premium car decision",
        "cta_keyword": "AUTO",
        "tone": "Premium",
        "default_goal": "Leads",
        "recommended_mode": "Extended Visual Storytelling",
        "recommended_length": "90 sec",
        "allowed_lengths": ["30 sec", "45 sec", "60 sec", "90 sec", "120 sec", "180 sec"],
        "niche_memory": "Luxury ownership emotion, aspiration, premium car buyer psychology, driving POV, design/status storytelling, comparison-led buyer logic",
        "page_direction": "Autos content should feel premium, cinematic, emotionally persuasive, and still grounded enough to move buyers closer to action.",
        "producer_question": "Why would this exact car, owner, spec, or driving moment make viewers imagine themselves owning it?",
        "success_definition": "Success means viewers feel desire, status, or buyer curiosity strong enough to save, enquire, or book a viewing.",
        "winning_formats": ["premium buyer mistake", "ownership feeling POV", "badge vs real ownership reality", "luxury reveal with emotional narration", "comparison reel", "aspirational day-in-life cut"],
        "viral_now": ["POV ownership experience reels", "emotion-first luxury hooks", "short comparison reels with clear conclusion", "premium detail shots with a sharper first line"],
        "rising_next": ["one hidden truth before buying premium", "buyer regret prevention reels", "status vs practicality comparison", "driving moment + narration hybrids"],
        "competitor_patterns": ["top auto content makes viewers imagine ownership, not just view the car", "best hooks create a buyer decision tension quickly", "clean cinematic visuals still need a strong voiceover line to perform", "showcase-only videos are weaker than decision-led stories"],
    },
    "Koocester Homes Singapore": {
        "internal_key": "homes",
        "market": "Singapore",
        "instagram_url": "https://www.instagram.com/koocesterhomes",
        "audience": "Singapore homeowners, condo buyers, landed property audience, renovation planners, premium home audience",
        "lead_type": "Renovation leads, home consultation leads, property lifestyle audience",
        "cta_intent": "start a home upgrade, plan renovation, save renovation ideas, book a consultation or showroom visit",
        "cta_keyword": "HOME",
        "tone": "Premium",
        "default_goal": "Leads",
        "recommended_mode": "Long Visual Storytelling",
        "recommended_length": "120 sec",
        "allowed_lengths": ["45 sec", "60 sec", "90 sec", "120 sec", "180 sec", "240 sec"],
        "niche_memory": "Renovation storytelling, homeowner mistakes, layout logic, home transformation, budget tension, property lifestyle",
        "page_direction": "Homes content should feel premium, useful, emotionally grounded, and specific enough to trigger saves and consultation intent.",
        "producer_question": "Why would this exact home, homeowner, layout, transformation, or house tour be worth filming and worth saving?",
        "success_definition": "Success means homeowners feel inspired and informed enough to save, share, or enquire about their own renovation journey.",
        "winning_formats": ["renovation mistake", "before vs after transformation", "hidden cost reveal", "layout problem solved", "homeowner regret story", "walkthrough with practical logic"],
        "viral_now": ["renovation regrets", "homeowner tension hooks", "smart layout reveal reels", "emotional transformation walkthroughs"],
        "rising_next": ["budget mistake breakdown", "small-space transformation storytelling", "what nobody tells you before renovating in Singapore", "visual walkthrough + practical narration hybrids"],
        "competitor_patterns": ["best renovation reels reveal the payoff quickly", "visual beauty alone is weaker than decision-led tension", "specific homeowner pain beats generic home tour content", "strong save-worthy content frames a mistake, regret, or solution"],
    },
    "Koocester Business Malaysia": {
        "internal_key": "business_my",
        "market": "Malaysia",
        "instagram_url": "https://www.instagram.com/koocesterbusiness.my",
        "audience": "Malaysia founders, SME owners, startup operators, entrepreneurs, business event audience, ambitious professionals",
        "lead_type": "Founder/event leads, SME networking leads, business authority leads, Malaysian business ecosystem leads",
        "cta_intent": "join better business rooms, connect with founders, attend business events, build authority and opportunities in Malaysia",
        "cta_keyword": "NETWORK",
        "tone": "Bold",
        "default_goal": "Leads",
        "recommended_mode": "Authority + Retention",
        "recommended_length": "90 sec",
        "allowed_lengths": ["30 sec", "45 sec", "60 sec", "90 sec", "120 sec", "180 sec", "240 sec"],
        "niche_memory": "Malaysia founder networking, SME growth, business insight, operator talk, high-value rooms, founder interviews, social proof for serious business owners",
        "page_direction": "Business Malaysia content should feel sharp, founder-led, practical, opportunity-driven, and relevant to Malaysian entrepreneurs and business owners.",
        "producer_question": "Why would this Malaysian founder, company, room, or interview be worth watching instead of a generic business video?",
        "success_definition": "Success means Malaysian founders or business owners feel this content gives useful insight, social proof, or access to better business rooms.",
        "winning_formats": ["contrarian founder hook", "SME growth lesson", "high-value room vs low-value room comparison", "short founder interview clip", "networking ROI explanation", "business myth breakdown"],
        "viral_now": ["hard-truth founder hooks", "SME owner lessons", "anti-fluff networking breakdowns", "short clips exposing business mistakes", "high-status room analysis with strong subtitles"],
        "rising_next": ["operator confession format", "business lesson from one real Malaysian founder moment", "event room psychology content", "comment-bait founder opinions", "Malaysia business growth frameworks"],
        "competitor_patterns": ["strong business reels start with tension immediately", "reels that compare bad vs good founder behavior perform better than generic motivation", "captions often stay short and high-conviction", "strongest videos create disagreement or recognition early"],
    },
    "Koocester Autos Malaysia": {
        "internal_key": "autos_my",
        "market": "Malaysia",
        "instagram_url": "https://www.instagram.com/koocesterautos.my",
        "audience": "Malaysia car buyers, premium and luxury car audience, aspirational viewers, enthusiasts, first-time premium buyers",
        "lead_type": "Premium buyer leads, showroom traffic leads, aspiration-driven Malaysian auto leads",
        "cta_intent": "book a viewing, enquire about the car, imagine ownership, move closer to a premium car decision in Malaysia",
        "cta_keyword": "AUTO",
        "tone": "Premium",
        "default_goal": "Leads",
        "recommended_mode": "Extended Visual Storytelling",
        "recommended_length": "90 sec",
        "allowed_lengths": ["30 sec", "45 sec", "60 sec", "90 sec", "120 sec", "180 sec"],
        "niche_memory": "Malaysia premium car lifestyle, luxury ownership emotion, aspiration, buyer psychology, driving POV, design/status storytelling, comparison-led buyer logic",
        "page_direction": "Autos Malaysia content should feel premium, cinematic, emotionally persuasive, and grounded in Malaysian car buyer lifestyle and status psychology.",
        "producer_question": "Why would this exact car, owner, spec, or driving moment make Malaysian viewers imagine themselves owning it?",
        "success_definition": "Success means viewers feel desire, status, or buyer curiosity strong enough to save, enquire, or book a viewing.",
        "winning_formats": ["premium buyer mistake", "ownership feeling POV", "badge vs real ownership reality", "luxury reveal with emotional narration", "comparison reel", "aspirational day-in-life cut"],
        "viral_now": ["POV ownership experience reels", "emotion-first luxury hooks", "short comparison reels with clear conclusion", "premium detail shots with a sharper first line"],
        "rising_next": ["one hidden truth before buying premium", "buyer regret prevention reels", "status vs practicality comparison", "driving moment + narration hybrids", "Malaysia road/lifestyle ownership angles"],
        "competitor_patterns": ["top auto content makes viewers imagine ownership, not just view the car", "best hooks create a buyer decision tension quickly", "clean cinematic visuals still need a strong voiceover line to perform", "showcase-only videos are weaker than decision-led stories"],
    },
    "Koocester Homes Malaysia": {
        "internal_key": "homes_my",
        "market": "Malaysia",
        "instagram_url": "https://www.instagram.com/koocesterhomes.my",
        "audience": "Malaysia homeowners, condo buyers, landed property audience, renovation planners, premium home audience",
        "lead_type": "Renovation leads, home consultation leads, property lifestyle audience, Malaysian homeowner leads",
        "cta_intent": "start a home upgrade, plan renovation, save renovation ideas, book a consultation or showroom visit in Malaysia",
        "cta_keyword": "HOME",
        "tone": "Premium",
        "default_goal": "Leads",
        "recommended_mode": "Long Visual Storytelling",
        "recommended_length": "120 sec",
        "allowed_lengths": ["45 sec", "60 sec", "90 sec", "120 sec", "180 sec", "240 sec"],
        "niche_memory": "Malaysia renovation storytelling, homeowner mistakes, layout logic, home transformation, budget tension, condo and landed property lifestyle",
        "page_direction": "Homes Malaysia content should feel premium, practical, emotionally grounded, and specific enough to make Malaysian homeowners save, share, or enquire.",
        "producer_question": "Why would this exact Malaysian home, homeowner, layout, transformation, or house tour be worth filming and worth saving?",
        "success_definition": "Success means homeowners feel inspired and informed enough to save, share, or enquire about their own renovation journey.",
        "winning_formats": ["renovation mistake", "before vs after transformation", "hidden cost reveal", "layout problem solved", "homeowner regret story", "walkthrough with practical logic"],
        "viral_now": ["renovation regrets", "homeowner tension hooks", "smart layout reveal reels", "emotional transformation walkthroughs"],
        "rising_next": ["budget mistake breakdown", "small-space transformation storytelling", "what nobody tells you before renovating in Malaysia", "visual walkthrough + practical narration hybrids", "landed vs condo renovation angles"],
        "competitor_patterns": ["best renovation reels reveal the payoff quickly", "visual beauty alone is weaker than decision-led tension", "specific homeowner pain beats generic home tour content", "strong save-worthy content frames a mistake, regret, or solution"],
    },
    "Koocester Wealth Singapore": {
        "internal_key": "wealth",
        "market": "Singapore",
        "instagram_url": "",
        "audience": "Singapore professionals, aspiring investors, business owners, wealth builders, high-income aspirational audience",
        "lead_type": "Wealth-building leads, investor education leads, financial planning interest leads",
        "cta_intent": "build wealth, learn better money decisions, start investing, understand financial growth, improve long-term security",
        "cta_keyword": "WEALTH",
        "tone": "Educational",
        "default_goal": "Leads",
        "recommended_mode": "Trust + Authority Wealth Education",
        "recommended_length": "90 sec",
        "allowed_lengths": ["30 sec", "45 sec", "60 sec", "90 sec", "120 sec", "180 sec"],
        "niche_memory": "wealth building, investing psychology, financial planning, money mistakes, long-term security, status and freedom through better money decisions",
        "page_direction": "Wealth content should feel trustworthy, sharp, educational, status-aware, and focused on helping Singapore audiences build wealth properly.",
        "producer_question": "Why would this money story, expert, investor, or financial insight make someone rethink how they build wealth?",
        "success_definition": "Success means viewers feel more serious about building wealth and take an action such as enquiring, saving, or requesting guidance.",
        "winning_formats": ["wealth mistake", "what rich people understand", "money myth breakdown", "investor psychology", "financial planning truth", "status vs security decision"],
        "viral_now": ["money mistake hooks", "wealth-building identity content", "simple investment psychology breakdowns", "what Singaporeans get wrong about wealth"],
        "rising_next": ["financial freedom micro-stories", "wealth gap explanation reels", "expert reaction to common money beliefs", "young professional money decision frameworks"],
        "competitor_patterns": ["strong wealth content opens with a money belief tension", "simple frameworks outperform vague financial motivation", "trust and credibility matter more than hype", "viewer must feel this applies to their future self"],
    },
    "Koocester Foodie Singapore": {
        "internal_key": "foodie",
        "market": "Singapore",
        "instagram_url": "",
        "audience": "Singapore food lovers, cafe hoppers, discovery audience, social diners, value-conscious food audience",
        "lead_type": "Discovery engagement audience, food discovery leads, location traffic audience",
        "cta_intent": "discover food spots, save the place, tag friends, visit the location, follow for food recommendations",
        "cta_keyword": "FOOD",
        "tone": "Emotional",
        "default_goal": "Engagement",
        "recommended_mode": "Fast Visual Storytelling",
        "recommended_length": "60 sec",
        "allowed_lengths": ["15 sec", "30 sec", "45 sec", "60 sec", "90 sec", "120 sec"],
        "niche_memory": "Food discovery, hidden gems, satisfying visual content, first-bite reactions, value framing, social dining lifestyle",
        "page_direction": "Foodie content should feel highly watchable, satisfying, saveable, and relevant to Singapore dining culture.",
        "producer_question": "Why would this specific food place, dish, price, reaction, or discovery be worth saving and sharing?",
        "success_definition": "Success means viewers want to save the spot, tag someone, visit, or follow for more Singapore food discoveries.",
        "winning_formats": ["worth it or not", "price-to-value reveal", "first bite reaction", "hidden gem discovery", "cheap vs expensive", "queue-worthy verdict"],
        "viral_now": ["price-based food hooks", "first bite payoff clips", "hidden gem reels with quick verdict", "satisfying close-up edit sequences"],
        "rising_next": ["honest hype-check food reels", "three-second visual payoff openings", "dish-by-dish verdict carousels turned into reels", "taste tension with quick emotional commentary"],
        "competitor_patterns": ["best foodie reels answer is-it-worth-it quickly", "food texture shots must arrive early", "money angle performs strongly in Singapore", "caption and on-screen text should stay simple and verdict-driven"],
    },
}



# --------------------------------------------------
# TRACKED COMPETITOR / NICHE PAGE MAP
# --------------------------------------------------
# These are sources to scan, not automatic recommendations.
# The post-level relevance filter below decides whether each actual post is useful for Koocester.
TRACKED_COMPETITOR_PAGES = {
    "homes_sg": [
        "stackedhomes", "propertylimbrothers", "thelocalinnterior", "qanvast", "renonation",
        "sgproperty", "edgeprop.sg", "homeanddecor_sg", "lookboxliving", "singaporeinterior",
    ],
    "homes_my": [
        "malaysiaproperty", "propertyguru_malaysia", "ipropertymalaysia", "interior.my",
        "klproperty", "malaysiarenovation", "atap.co", "myhome", "renonation.my",
    ],
    "business_sg": [
        "startupsg", "sgfounders", "thebusinessshowasia", "e27co", "techinasia",
        "foundr", "entrepreneur", "alexhormozi", "garyvee", "businessinsider",
    ],
    "business_my": [
        "malaysiabusiness", "myfounders", "entrepreneurmy", "smemalaysia", "digitalnewsasia",
        "vulcanpost", "startupmalaysia", "foundr", "alexhormozi",
    ],
    "autos_sg": [
        "sgcarmart", "motoristsg", "torqusingapore", "oneshift_sg", "carbuyersingapore",
        "supercarsingapore", "luxurycarsg", "carwow", "topgear", "pistonheads",
    ],
    "autos_my": [
        "paultan", "carlistmy", "wapcar.my", "autobuzz.my", "zigwheelsmy",
        "malaysiaautos", "mycar", "supercarmy", "luxurycarsmy", "topgear",
    ],
}

TRACKED_HASHTAGS = {
    "homes_sg": [
        "singaporehomes", "singaporeproperty", "sginteriordesign", "sgrenovation",
        "singaporecondo", "hdbrenovation", "singaporeinterior", "sgpropertymarket",
    ],
    "homes_my": [
        "malaysiahomes", "malaysiaproperty", "myinteriordesign", "malaysiarenovation",
        "klproperty", "rumahmalaysia", "malaysiainterior", "malaysiahomedecor",
    ],
    "business_sg": [
        "sgbusiness", "singaporebusiness", "sgfounders", "startupsg", "entrepreneursg",
        "smebusiness", "businessnetworking", "founderstory",
    ],
    "business_my": [
        "malaysiabusiness", "malaysiaentrepreneur", "smemalaysia", "startupmalaysia",
        "usahawanmalaysia", "bisnesmalaysia", "foundermalaysia",
    ],
    "autos_sg": [
        "sgcars", "singaporecars", "sgcarmart", "supercarsingapore", "luxurycarsg",
        "carreviewsg", "sgcarclub", "singaporecar",
    ],
    "autos_my": [
        "malaysiacars", "keretamalaysia", "supercarmy", "luxurycarsmy", "automalaysia",
        "carreviewmalaysia", "paultan", "malaysiacarclub",
    ],
}

def get_niche_bucket_for_page(page_data: Dict[str, Any]) -> str:
    key = page_data.get("internal_key", "")
    if key == "homes":
        return "homes_sg"
    if key == "homes_my":
        return "homes_my"
    if key == "business":
        return "business_sg"
    if key == "business_my":
        return "business_my"
    if key == "autos":
        return "autos_sg"
    if key == "autos_my":
        return "autos_my"
    if page_data.get("market", "").lower() == "malaysia":
        return "business_my"
    return "business_sg"


def get_tracked_hashtags_for_page(page_data: Dict[str, Any]) -> List[str]:
    return TRACKED_HASHTAGS.get(get_niche_bucket_for_page(page_data), [])



def get_tracked_pages_for_page(page_data: Dict[str, Any]) -> List[str]:
    key = page_data.get("internal_key", "")
    market = page_data.get("market", "").lower()

    if key == "homes":
        return TRACKED_COMPETITOR_PAGES.get("homes_sg", [])
    if key == "homes_my":
        return TRACKED_COMPETITOR_PAGES.get("homes_my", [])
    if key == "business":
        return TRACKED_COMPETITOR_PAGES.get("business_sg", [])
    if key == "business_my":
        return TRACKED_COMPETITOR_PAGES.get("business_my", [])
    if key == "autos":
        return TRACKED_COMPETITOR_PAGES.get("autos_sg", [])
    if key == "autos_my":
        return TRACKED_COMPETITOR_PAGES.get("autos_my", [])

    if market == "singapore":
        return TRACKED_COMPETITOR_PAGES.get("homes_sg", []) + TRACKED_COMPETITOR_PAGES.get("business_sg", []) + TRACKED_COMPETITOR_PAGES.get("autos_sg", [])
    if market == "malaysia":
        return TRACKED_COMPETITOR_PAGES.get("homes_my", []) + TRACKED_COMPETITOR_PAGES.get("business_my", []) + TRACKED_COMPETITOR_PAGES.get("autos_my", [])
    return []


def get_page_intelligence(page_name: str) -> Dict[str, Any]:
    return PAGE_INTELLIGENCE[page_name]


def get_market_pages(market: str) -> List[str]:
    return [name for name, data in PAGE_INTELLIGENCE.items() if data.get("market") == market]


def get_connected_instagram_status(page_data: Dict[str, Any]) -> str:
    instagram_url = page_data.get("instagram_url", "")
    access_token = st.secrets.get("META_ACCESS_TOKEN", "") or os.getenv("META_ACCESS_TOKEN", "")
    ig_user_id = get_instagram_user_id_for_page(page_data)

    if not instagram_url:
        return "Instagram page link is not added yet. The engine will rely on stored page intelligence only."
    if access_token and ig_user_id:
        return "Instagram page link and live own-account analytics are connected."
    return "Instagram page link is added. Live analytics are not connected yet, so the engine uses stored page intelligence plus the page identity."


def build_page_readiness_notes(page_name: str, page_data: Dict[str, Any], platform: str) -> str:
    market = page_data.get("market", "Singapore")
    same_market_pages = get_market_pages(market)
    return (
        f"Selected page: {page_name}\n"
        f"Market: {market}\n"
        f"Platform: {platform}\n"
        f"Instagram status: {get_connected_instagram_status(page_data)}\n"
        f"Same-market pages available in system: {', '.join(same_market_pages)}\n"
        "Current mode: latest public trend scanning requires TREND_FEED_API_URL or TREND_FEED_JSON. Do not claim broad public Instagram trend scanning unless that feed is connected."
    )


# --------------------------------------------------
# VIRAL INTELLIGENCE / TREND LAYER (NO ACCOUNT ACCESS)
# --------------------------------------------------
def build_public_intelligence_summary(page_name: str, page_data: Dict[str, Any], platform: str, reference_links: str, live_analytics_summary: str = "", latest_trend_summary: str = "") -> str:
    if platform == "Instagram":
        platform_now = [
            "clean premium edits with immediate context",
            "strong first-line hooks within 1-2 seconds",
            "save-worthy or share-worthy educational framing",
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
            "raw tension-driven opening lines",
            "comment-bait opinions",
            "pattern interrupts every few seconds",
        ]
        platform_next = [
            "mini-story confession formats",
            "POV + decision tension",
            "one strong belief/opinion format",
            "high-rewatch payoff structures",
        ]

    ig_url = page_data.get("instagram_url") or "No confirmed Instagram link provided yet."
    links = reference_links.strip() if reference_links.strip() else "No extra links provided by producer."
    readiness_notes = build_page_readiness_notes(page_name, page_data, platform)
    tracked_pages = get_tracked_pages_for_page(page_data)

    lines = [
        "Tracked competitor / niche pages to monitor: " + (", ".join(tracked_pages) if tracked_pages else "No tracked pages mapped for this page yet."),
        "Trend priority rule: actual latest trend feed data is primary; stored intelligence is secondary only.",
        "System readiness notes: " + readiness_notes.replace("\n", " | "),
        f"Market focus: {page_data.get('market', 'Singapore')} only.",
        f"Selected Instagram page identity: {page_name} - {ig_url}",
        f"Page direction memory: {page_data['page_direction']}",
        f"Known page niche: {page_data['niche_memory']}",
        f"Known audience: {page_data['audience']}",
        f"Producer evaluation question: {page_data['producer_question']}",
        f"What success looks like: {page_data['success_definition']}",
        f"CTA intent for this page: {page_data['cta_intent']}",
        "Viral now for this page path: " + ", ".join(page_data["viral_now"]),
        "Likely rising next for this page path: " + ", ".join(page_data["rising_next"]),
        "Competitor-style patterns in same niche: " + ", ".join(page_data["competitor_patterns"]),
        f"Current {platform} format signals: " + ", ".join(platform_now),
        f"Likely next {platform} format signals: " + ", ".join(platform_next),
        f"Reference / inspiration links to consider: {links}",
        "Live / connected analytics summary: " + (live_analytics_summary.strip() if live_analytics_summary.strip() else "No live analytics available."),
        "Latest public trend feed summary: " + (latest_trend_summary.strip() if latest_trend_summary.strip() else "No latest public trend feed available."),
    ]
    return "\n".join(f"- {line}" for line in lines)


def build_auto_cta(page_name: str, page_data: Dict[str, Any], platform: str) -> str:
    keyword = page_data.get("cta_keyword", "START")
    intent = page_data.get("cta_intent", "take the next step")
    if platform == "TikTok":
        return f"DM '{keyword}' if you want to {intent}."
    return f"DM '{keyword}' if you want to {intent}."


# --------------------------------------------------
# PROMPTS
# --------------------------------------------------
def build_master_prompt(
    page_name: str,
    page_data: Dict[str, Any],
    platform: str,
    market: str,
    role_mode: str,
    auto_cta: str,
    goal: str,
    video_length: str,
    tone: str,
    uploaded_context: str,
    scenario: str,
    success_looks_like: str,
    filming_subject: str,
    reference_links: str,
    advanced_context: str,
    intelligence_summary: str,
) -> str:
    role_block = (
        "Prioritize what to shoot, who/what to shoot, what makes the subject film-worthy, how to structure scenes, what questions to ask, and what producer decisions increase virality."
        if role_mode == "Producer"
        else "Prioritize hooks, caption logic, on-screen text, scripting, wording, CTA language, and copy refinement."
    )

    return f"""
You are an ELITE real-time viral content generator and Instagram trend intelligence strategist for Koocester.

Your primary job is NOT to write a generic strategy report.
Your primary job is to generate latest viral or about-to-go-viral content ideas based on:
- the selected Koocester page niche
- the selected country/market
- latest public trend feed data when connected
- Instagram/TikTok short-form content behavior
- stored page intelligence
- uploaded analytics or reference links
- live own-account Instagram analytics when connected

You must think like a viral content desk:
- what is already going viral in this niche within the last 7 days
- what is starting to spike within the last 14 days
- what formats are becoming saturated
- what formats are underused
- how Koocester should adapt the trend without copying
- what should be filmed next
- what hook, structure, caption, and CTA should be used

==================================================
SYSTEM MODE
==================================================

Selected Page: {page_name}
Selected Instagram Page: {page_data.get('instagram_url') or 'No confirmed Instagram link provided yet.'}
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
Automatic Page CTA: {auto_cta}
CTA Intent: {page_data['cta_intent']}
Producer Evaluation Question: {page_data['producer_question']}
Default Success Definition: {page_data['success_definition']}
Producer's Success Definition: {success_looks_like if success_looks_like.strip() else 'Use the default success definition and infer success from the page goal.'}
Who / What Are We Filming: {filming_subject if filming_subject.strip() else 'Not specified. Infer the most likely subject from the selected page and scenario.'}
Scenario / Situation: {scenario if scenario.strip() else 'No specific scenario provided. Generate based on page identity and content direction.'}
Reference / Inspiration Links: {reference_links if reference_links.strip() else 'No reference links provided.'}
Advanced Context: {advanced_context if advanced_context.strip() else 'No extra advanced context provided.'}

==================================================
HIDDEN PUBLIC INTELLIGENCE LAYER
==================================================

{intelligence_summary}

Rules:
- {market} only. Do not switch to another country unless the selected page changes.
- Do not ask for a pain point. Infer weaknesses yourself.
- Stay aligned with the selected Instagram page identity and content direction.
- Improve the page's current content path; do not replace it with random unrelated ideas.
- Use Instagram page link, reference links, and uploaded context as direction signals.
- If live Instagram analytics are connected, use them as own-account performance signals.
- If live Instagram analytics are not connected, do not claim real-time analytics; clearly say the output is based on stored page intelligence and available references.
- Do not claim access to all public Instagram trends unless TREND_FEED_API_URL, TREND_FEED_JSON, or uploaded trend data is provided.
- Recency rules are strict: 0-7 days means viral now, 8-14 days means rising, 15-30 days means pattern validation only, older than 30 days must be ignored unless repeated in recent data.
- If no latest trend feed is connected, DO NOT generate fake or inferred viral-now Instagram content.
- Instead clearly say: "No live SG/MY Instagram trend feed connected yet."
- Only generate real viral-now or rising Instagram content when actual trend data exists.
- If no trend feed exists, you may provide setup guidance and describe what data is missing, but do not pretend assumptions are real viral content.
- Be clear on what would become stronger if broader Instagram trend feeds or competitor analytics are connected.
- For each idea, explain why this subject/person/place/content type is film-worthy.
- Distinguish clearly between:
  1. Viral Now
  2. Likely To Go Viral Next
  3. Same-Niche Competitor Opportunity
- Be realistic and practical.
- No generic filler logic.
- Do not invent analytics, follower numbers, view counts, watch time, saves, shares, comments, or live trend data.
- Use phrases like "likely", "inferred", or "based on stored page intelligence" when live Instagram access is not connected.
- If the selected page has a confirmed Instagram link, treat it as the page identity anchor.
- If reference links or uploaded files are provided, use them as stronger signals than general assumptions.
- Keep the original Koocester brand direction and improve execution only.

==================================================
QUALITY CONTROL CHECK BEFORE ANSWERING
==================================================

Before producing the final answer, internally check:
1. Does the idea match the selected page and market?
2. Is the subject film-worthy?
3. Is the hook strong within the first 2 seconds?
4. Is there a clear retention path?
5. Is the CTA aligned with the page objective?
6. Is the recommendation practical for a producer or copywriter?
7. Did you avoid claiming live Instagram analytics?

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

1. DATA SOURCE STATUS
- say whether live own-account Instagram analytics are connected
- say whether broad public Instagram trend analytics are connected or not
- never fake analytics
- identify what the recommendation is based on

2. REAL VIRAL INSTAGRAM CONTENT RIGHT NOW
Use only actual latest trend feed items from the last 7 days.
If no real latest trend feed is connected, do not invent examples. Say "No live SG/MY Instagram trend feed connected yet."
For each real item include:
- real reel/post title
- actual Instagram page or source
- actual reel/post link
- posted recency
- views/engagement if available
- why it is going viral
- why this matters for Koocester
- what should be adapted
- content benefit for this page
- lead or engagement benefit

3. ABOUT-TO-GO-VIRAL / RISING INSTAGRAM CONTENT
Use only actual latest trend feed items from the last 8-14 days.
If no real latest trend feed is connected, do not invent examples. Say what source must be connected.
For each real item include:
- real reel/post title
- actual Instagram page or source
- actual reel/post link
- posted recency
- engagement velocity if available
- why it may grow next
- what makes it not yet saturated
- Koocester version
- best first hook
- risk level

4. DO NOT USE / SATURATED CONTENT
List 5 formats that are likely weak, overused, or low-retention for this page.
Explain why.

5. BEST 10 VIRAL VIDEO IDEAS TO MAKE NEXT
For each idea include:
- title
- viral hook
- trend source category: already viral / rising / experimental
- exact Koocester version
- why this fits the selected page
- why this fits the selected country
- what to film
- opening 2 seconds
- caption angle
- CTA angle
- predicted viral potential score
- predicted lead potential score

6. TOP 3 IDEAS TO SHOOT FIRST
Rank the best 3.
Explain why each should be prioritized.

7. ANALYTICS-BASED INSIGHTS
If own-account Instagram analytics are connected:
- summarize what recent Koocester media signals suggest
- identify top content patterns
- identify weak patterns
If latest public trend feed is connected:
- identify latest viral items from 0-7 days
- identify rising items from 8-14 days
- ignore anything older than 30 days
If either source is not connected:
- clearly say what is unavailable
- state what data must be connected to make this section real

8. PRODUCER EXECUTION PLAN
- must-have footage
- must-have first 2 seconds
- must-have on-screen text
- must-have emotion or curiosity trigger
- editing style
- what to avoid
- what the editor must emphasize

9. COPYWRITER OUTPUT
- 10 hooks
- 3 captions
- 5 on-screen text lines
- 3 CTA variations
- strongest final CTA:
{auto_cta}

10. FINAL RECOMMENDATION
- one idea to shoot first today
- why this has the highest upside
- what data would make the prediction more accurate
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
You are an ELITE market-specific viral content reviewer for Koocester.

Selected Page: {page_name}
Instagram Page: {page_data.get('instagram_url') or 'No confirmed Instagram link provided yet.'}
Page Direction: {page_data['page_direction']}
Known Niche: {page_data['niche_memory']}
Known Audience: {page_data['audience']}
Platform: {platform}
Market: {market}
Role Mode: {role_mode}
Goal: {goal}
Tone: {tone}
Scenario: {scenario if scenario.strip() else 'No scenario provided.'}

Hidden Intelligence Summary:
{intelligence_summary}

User's Draft Video Idea:
{draft_video_idea}

User's Draft CTA:
{draft_cta}

User's Draft Caption:
{draft_caption}

Review Rules:
- judge whether it matches the selected Instagram page direction
- judge whether it fits the selected market and the selected platform
- judge whether the subject/person/place is actually worth filming
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
You are an ELITE market-specific viral content reviewer and script critic for Koocester.

Selected Page: {page_name}
Instagram Page: {page_data.get('instagram_url') or 'No confirmed Instagram link provided yet.'}
Page Direction: {page_data['page_direction']}
Known Niche: {page_data['niche_memory']}
Known Audience: {page_data['audience']}
Platform: {platform}
Market: {market}
Role Mode: {role_mode}
Goal: {goal}
Tone: {tone}
Scenario: {scenario if scenario.strip() else 'No scenario provided.'}

Hidden Intelligence Summary:
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
- judge whether this stays in the same Instagram page path but stronger
- judge whether it fits the selected market and the selected platform

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
    auto_cta: str,
    goal: str,
    video_length: str,
    tone: str,
    uploaded_context: str,
    scenario: str,
    success_looks_like: str,
    filming_subject: str,
    reference_links: str,
    advanced_context: str,
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
        auto_cta=auto_cta,
        goal=goal,
        video_length=video_length,
        tone=tone,
        uploaded_context=uploaded_context,
        scenario=scenario,
        success_looks_like=success_looks_like,
        filming_subject=filming_subject,
        reference_links=reference_links,
        advanced_context=advanced_context,
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
    st.subheader("Admin Analytics")

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
            st.write(f"**Market:** {row.get('market', '-')}")
            st.write(f"**Role Mode:** {row.get('role_mode', '-')}")
            st.write(f"**Goal:** {row.get('goal', '-')}")
            st.write(f"**Scenario:** {row.get('scenario', '-')}")
            st.write(f"**Output chars:** {row.get('output_chars', 0)}")
            st.write(f"**Uploaded count:** {row.get('uploaded_count', 0)}")
            st.write(f"**Uploaded bytes:** {row.get('uploaded_total_bytes', 0)}")
            st.write(f"**Notes:** {row.get('notes', '')}")


# --------------------------------------------------
# CTA ENGINE
# --------------------------------------------------
def generate_cta_v10(goal: str, platform: str, page_name: str, page_data: Dict[str, Any], auto_cta: str) -> Tuple[List[str], str, str]:
    keyword = page_data.get("cta_keyword", "START")
    intent = page_data.get("cta_intent", "take the next step")

    if goal == "Leads":
        ctas = [
            auto_cta,
            f"DM '{keyword}' and we'll show you the next step.",
            f"If this is relevant to you, DM '{keyword}'.",
        ]
    elif goal == "Engagement":
        ctas = [
            "Be honest - would you actually agree with this?",
            "Comment your take below.",
            "Tag someone who needs to see this.",
        ]
    elif goal == "Views":
        ctas = [
            "Watch this again - you probably missed the real point.",
            "Most people don't catch this the first time.",
            "Wait till the end before you judge this.",
        ]
    else:
        ctas = [
            f"Follow if you want to {intent}.",
            "If this helped, there's more coming.",
            "Stay close - more soon.",
        ]

    if platform == "TikTok":
        ctas = [cta.rstrip(".") + "" for cta in ctas]

    best_cta = ctas[0]
    reasoning = "This CTA is strongest because it is matched to the selected Koocester page objective instead of being manually generic."
    return ctas, best_cta, reasoning


# --------------------------------------------------
# SETUP GUIDE UI
# --------------------------------------------------
def render_setup_guide() -> None:
    with st.sidebar:
        st.divider()
        st.header("Setup Guide")

        with st.expander("Streamlit Secrets Template", expanded=False):
            st.code(SECRETS_TEMPLATE, language="toml")

        with st.expander("How Instagram Connection Works", expanded=False):
            st.markdown(
                """
Official Meta access can read your own connected professional account media and insights.
It can help the engine learn what works on Koocester pages.

It does not automatically scan all public viral Instagram content.
For latest public viral scanning, connect APIFY_API_TOKEN and use the live scraper checkbox, or connect TREND_FEED_API_URL / paste TREND_FEED_JSON.
"""
            )

        with st.expander("Safety Notes", expanded=False):
            st.markdown(
                """
Low risk:
- official Meta API
- read-only insights
- no auto liking/following/commenting/DM spam

Higher risk:
- unofficial scraping
- aggressive automation
- mass DMs
- fake engagement tools
"""
            )


# --------------------------------------------------
# UI
# --------------------------------------------------
st.title("Koocester Producer Intelligence Engine")
st.caption(
    "Live Instagram viral scanning by Koocester page, market, niche sources, and producer usefulness."
)

session_id = get_session_id()
render_admin_login()
render_setup_guide()

left, right = st.columns([1.15, 0.85], gap="large")

with left:
    st.subheader("Live Instagram Viral Scanner")

    page_name = st.selectbox(
        "Koocester Instagram Page",
        [
            "Koocester Main",
            "Koocester Business Singapore",
            "Koocester Autos Singapore",
            "Koocester Homes Singapore",
            "Koocester Business Malaysia",
            "Koocester Autos Malaysia",
            "Koocester Homes Malaysia",
            "Koocester Wealth Singapore",
            "Koocester Foodie Singapore",
        ],
    )
    page_data = get_page_intelligence(page_name)
    live_instagram_data = fetch_instagram_live_analytics(page_data)
    live_analytics_summary = summarize_live_analytics_for_prompt(live_instagram_data)
    latest_trend_data = {"connected": False, "status": "Trend feed not loaded yet.", "items": []}
    latest_trend_summary = "Trend feed not loaded yet."

    if page_data.get("instagram_url"):
        st.caption(f"Instagram source page: {page_data['instagram_url']}")
    else:
        st.caption("Instagram source page: not added yet for this page. Add the IG link later for stronger page identity.")

    market = page_data.get("market", "Singapore")
    st.caption(f"Country / Market: {market}")

    platform = st.selectbox("Platform", ["Instagram", "TikTok"])
    role_mode = st.selectbox("Output For", ["Producer", "Copywriter"])

    # Hidden backend fields. They are intentionally removed from the producer interface.
    filming_subject = ""
    scenario = ""
    success_looks_like = page_data.get("success_definition", "")
    reference_links = ""

    goal = st.selectbox(
        "Main Goal",
        ["Views", "Engagement", "Leads", "Awareness"],
        index=["Views", "Engagement", "Leads", "Awareness"].index(page_data["default_goal"]),
    )

    video_length = st.selectbox(
        "Video Length",
        page_data["allowed_lengths"],
        index=page_data["allowed_lengths"].index(page_data["recommended_length"]),
    )

    tone = st.selectbox(
        "Tone",
        ["Premium", "Bold", "Educational", "Emotional", "Direct"],
        index=["Premium", "Bold", "Educational", "Emotional", "Direct"].index(page_data["tone"]),
    )

    auto_cta = build_auto_cta(page_name, page_data, platform)
    st.info(f"Auto CTA for this page: {auto_cta}")

    uploaded_files = st.file_uploader(
        "Upload supporting files (optional)",
        accept_multiple_files=True,
        type=None,
        help="Upload scripts, decks, notes, references, or anything useful for generation.",
    )

    manual_trend_json = st.text_area(
        "Optional Latest Trend Feed JSON",
        placeholder='Paste recent trend items only. Example: [{"title":"viral format","posted_at":"2026-05-04T10:00:00+00:00","views":100000,"likes":5000,"comments":300,"shares":700,"saves":900,"market":"Singapore","platform":"Instagram"}]',
        height=90,
        help="Use this if you do not have TREND_FEED_API_URL yet. Keep content recent: 0-7 days viral now, 8-14 days rising, 15-30 days validation only.",
    )

    # Do not scrape on page load. Only scrape after the user clicks the scan button.
    # This prevents timeouts and keeps the UI fast.
    latest_trend_data = {"connected": False, "status": "Not scanned yet. Click Scan Viral Instagram Content.", "items": []}
    latest_trend_summary = "Not scanned yet. Click Scan Viral Instagram Content."

    advanced_context = ""
    draft_video_idea = ""
    draft_cta = ""
    draft_caption = ""
    review_video_idea = ""
    review_script = ""
    review_cta = ""
    review_caption = ""

    if SHOW_ADVANCED_FIELDS or is_admin():
        with st.expander("Advanced / Admin Tools", expanded=False):
            advanced_context = st.text_area(
                "Extra Manual Context",
                placeholder="Anything else the AI should know before generating.",
                height=100,
            )

            st.divider()
            st.subheader("Draft Review")
            draft_video_idea = st.text_area(
                "Draft Video Idea",
                placeholder="Paste your draft video idea here...",
                height=100,
            )
            draft_cta = st.text_input("Draft CTA", placeholder="e.g. DM us / Register now / Save this")
            draft_caption = st.text_area("Draft Caption", placeholder="Paste your draft caption here...", height=90)

            st.divider()
            st.subheader("Idea / Script Review")
            review_video_idea = st.text_area("Your Video Idea", placeholder="Paste your idea here...", height=90)
            review_script = st.text_area("Your Draft Script", placeholder="Paste your script here...", height=140)
            review_cta = st.text_input("Your Draft CTA", placeholder="e.g. DM us / Register now")
            review_caption = st.text_area("Your Draft Caption", placeholder="Paste your draft caption here...", height=90)

    c1, c2, c3 = st.columns(3)
    with c1:
        generate = st.button("Scan Viral Instagram Content", use_container_width=True)
    with c2:
        review_draft_btn = st.button("Rate Draft", use_container_width=True, disabled=not is_admin())
    with c3:
        review_idea_btn = st.button("Rate Script", use_container_width=True, disabled=not is_admin())

with right:
    st.subheader("Selected Direction")
    st.write(f"**Page:** {page_name}")
    st.write(f"**Market:** {market}")
    st.write(f"**Platform:** {platform}")
    st.write(f"**Output For:** {role_mode}")
    st.write(f"**Goal:** {goal}")
    st.write(f"**Video Length:** {video_length}")
    st.write(f"**Tone:** {tone}")
    st.write(f"**CTA Intent:** {page_data['cta_intent']}")
    st.write(f"**Instagram Status:** {get_connected_instagram_status(page_data)}")
    st.write(f"**Live Analytics:** {'Connected' if live_instagram_data.get('connected') else 'Not connected'}")
    st.write(f"**Latest Trend Feed:** {'Connected' if latest_trend_data.get('connected') else 'Not connected'}")
    st.write("**Trend Recency Rules:** 0-7 days viral now, 8-14 days rising, 15-30 days validation only")
    with st.expander("Tracked niche sources", expanded=False):
        st.write("**Pages:** " + (", ".join(get_tracked_pages_for_page(page_data)) or "None"))
        st.write("**Hashtags:** " + (", ".join("#" + tag for tag in get_tracked_hashtags_for_page(page_data)) or "None"))

    uploaded_context, uploaded_files_json, uploaded_count, uploaded_total_bytes = summarize_uploaded_files(uploaded_files)
    st.divider()
    st.subheader("Upload Summary")
    st.write(f"**Files uploaded:** {uploaded_count}")
    st.write(f"**Total size:** {uploaded_total_bytes} bytes")
    if uploaded_count:
        st.code(uploaded_context, language="text")

intelligence_summary = build_public_intelligence_summary(page_name, page_data, platform, reference_links, live_analytics_summary, latest_trend_summary)

if SHOW_PUBLIC_INTELLIGENCE or is_admin():
    with st.expander("Backend Intelligence Layer", expanded=False):
        st.code(intelligence_summary, language="text")

    with st.expander("Latest Trend Feed Preview", expanded=False):
        st.code(latest_trend_summary, language="text")

    with st.expander("Instagram Analytics Preview", expanded=False):
        st.code(live_analytics_summary, language="text")

if SHOW_DEBUG_PROMPTS or is_admin():
    with st.expander("Master Prompt Preview", expanded=False):
        master_prompt = build_master_prompt(
            page_name=page_name,
            page_data=page_data,
            platform=platform,
            market=market,
            role_mode=role_mode,
            auto_cta=auto_cta,
            goal=goal,
            video_length=video_length,
            tone=tone,
            uploaded_context=uploaded_context,
            scenario=scenario,
            success_looks_like=success_looks_like,
            filming_subject=filming_subject,
            reference_links=reference_links,
            advanced_context=advanced_context,
            intelligence_summary=intelligence_summary,
        )
        st.code(master_prompt, language="text")


# --------------------------------------------------
# SCAN REAL INSTAGRAM CONTENT FIRST
# --------------------------------------------------
if generate:
    ip_value, ip_source = get_ip_if_available()
    user_agent = get_user_agent()

    try:
        with st.spinner("Scraping real Instagram niche content from tracked pages and hashtags..."):
            scanned_trend_data = fetch_latest_trend_feed(
                page_data,
                platform,
                manual_trend_json=manual_trend_json,
                run_live_scraper=True,
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
                "pain_point": "real_instagram_scan",
                "offer": auto_cta,
                "goal": goal,
                "video_length": video_length,
                "tone": tone,
                "scenario": scenario,
                "action_type": "live_instagram_scan",
                "output_chars": len(json.dumps(scanned_trend_data.get("items", [])[:20], default=str)),
                "user_agent": user_agent,
                "uploaded_files_json": uploaded_files_json,
                "uploaded_total_bytes": uploaded_total_bytes,
                "uploaded_count": uploaded_count,
                "ip_value": ip_value,
                "ip_source": ip_source,
                "notes": scanned_trend_data.get("status", "")[:1000],
            }
        )

        render_real_viral_scan(scanned_trend_data, page_name, page_data)
        st.stop()

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
                "pain_point": "real_instagram_scan_error",
                "offer": auto_cta,
                "goal": goal,
                "video_length": video_length,
                "tone": tone,
                "scenario": scenario,
                "action_type": "live_instagram_scan_error",
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
# ADMIN REVIEW TOOLS
# --------------------------------------------------
if review_draft_btn and is_admin():
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


if review_idea_btn and is_admin():
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
st.caption("Koocester Producer Intelligence Engine")

