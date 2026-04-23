import os, re, json, sqlite3, math, uuid, threading, time, queue, webbrowser
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, Response
import ollama
import pystray
from PIL import Image, ImageDraw

app = Flask(__name__)
app.config["SECRET_KEY"] = "level-up-secret"
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "levelup.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── Per-profile DB routing ──────────────────────────────────────────────
_PROFILE_RE = re.compile(r'[^a-z0-9_]')
_initialized_dbs = set()
_init_lock = threading.Lock()

def current_profile():
    """Return sanitized profile slug for this request, or '' for default."""
    try:
        p = (request.args.get('profile') or '').strip().lower()
    except RuntimeError:
        return ''
    return _PROFILE_RE.sub('', p)[:32]

def db_path_for(profile):
    return os.path.join(BASE_DIR, f"levelup_{profile}.db") if profile else DB_PATH

# ── SSE (Server-Sent Events) for real-time multi-device sync ─────────────────
sse_clients = []  # list of (profile, queue.Queue)
sse_lock = threading.Lock()

def broadcast(event_type="sync"):
    """Push an event to all SSE clients sharing the current request's profile."""
    profile = current_profile()
    data = f"event: {event_type}\ndata: {{\"ts\":{int(time.time())}}}\n\n"
    with sse_lock:
        dead = []
        for prof, q in sse_clients:
            if prof != profile: continue
            try:
                q.put_nowait(data)
            except queue.Full:
                dead.append((prof, q))
        for item in dead:
            sse_clients.remove(item)

PERSONAS = {
    "visionary": {"name":"The Visionary","desc":"Strategy & Networking","weights":{"CHA":1.5,"INT":1.3,"DEX":0.8,"VIT":1.0},"icon":"\u2728"},
    "operator":  {"name":"The Operator", "desc":"Execution & Technical Depth","weights":{"DEX":1.5,"INT":1.3,"CHA":0.8,"VIT":1.0},"icon":"\u2699\ufe0f"},
    "scholar":   {"name":"The Scholar",  "desc":"Research & Learning","weights":{"INT":1.8,"DEX":1.0,"CHA":0.8,"VIT":1.0},"icon":"\ud83d\udcda"},
    "vitalist":  {"name":"The Vitalist", "desc":"Physical Performance & Recovery","weights":{"VIT":1.8,"DEX":1.0,"INT":0.8,"CHA":0.8},"icon":"\ud83d\udcaa"},
}

ENERGY_COSTS = {"INT": 12, "DEX": 10, "CHA": 6, "VIT": -15}

# ── Titles & Unlocks (level-gated) ────────────────────────────────────────
TITLES = [
    (1,  "Novice",       "\U0001F331"),
    (3,  "Apprentice",   "\U0001F4D6"),
    (5,  "Adventurer",   "\U0001F5E1\uFE0F"),
    (8,  "Warrior",      "\u2694\uFE0F"),
    (12, "Veteran",      "\U0001F6E1\uFE0F"),
    (16, "Elite",        "\U0001F31F"),
    (20, "Champion",     "\U0001F3C6"),
    (25, "Hero",         "\u2728"),
    (30, "Master",       "\U0001F451"),
    (40, "Grandmaster",  "\U0001F48E"),
    (50, "Legend",       "\U0001F525"),
    (65, "Mythic",       "\U0001F300"),
    (80, "Immortal",     "\u26A1"),
    (99, "Transcendent", "\U0001F30C"),
]

def title_for_level(lv):
    """Return (title_name, icon) for a given level."""
    best = TITLES[0]
    for req, name, icon in TITLES:
        if lv >= req: best = (req, name, icon)
    return {"name": best[1], "icon": best[2], "min_level": best[0]}

# Unlocks: (level_required, key, label, description)
UNLOCKS = [
    (1,  "basic",          "Quest Board",         "Access to daily quests"),
    (3,  "tomorrow",       "Tomorrow Planning",   "Plan quests a day ahead"),
    (5,  "weekly",         "Weekly Goals",        "Set ambitious weekly goals"),
    (5,  "brainstorm",     "AI Brainstorm",       "LLM-powered quest generation"),
    (8,  "challenges",     "Daily Challenges",    "Bonus challenge objectives"),
    (10, "monthly",        "Monthly Milestones",  "Epic long-term milestones"),
    (12, "leaderboard",    "Leaderboard",         "Compete with other players"),
    (15, "stat_boost",     "Stat Boost +10%",     "All stat XP gains +10%"),
    (20, "double_streak",  "Streak Shield",       "One free missed day per week"),
    (25, "xp_boost",       "XP Boost +15%",       "All XP gains boosted 15%"),
    (30, "elite_chal",     "Elite Challenges",    "Harder challenges, bigger rewards"),
    (40, "prestige_border","Prestige Border",     "Golden profile border"),
    (50, "legend_aura",    "Legend Aura",         "Animated profile glow"),
]

def unlocks_for_level(lv):
    """All unlocks earned at or below lv."""
    return [{"level": req, "key": k, "label": lb, "desc": d} for req, k, lb, d in UNLOCKS if lv >= req]

def new_unlocks_at_level(lv):
    """Unlocks that trigger exactly at this level."""
    return [{"level": req, "key": k, "label": lb, "desc": d} for req, k, lb, d in UNLOCKS if req == lv]

def next_unlock(lv):
    """The next unlock coming."""
    for req, k, lb, d in UNLOCKS:
        if req > lv:
            return {"level": req, "key": k, "label": lb, "desc": d}
    return None

# ── Leaderboard (shared across all profiles) ───────────────────────────────
LEADERBOARD_DB = os.path.join(BASE_DIR, "leaderboard.db")

def _init_leaderboard_db():
    c = sqlite3.connect(LEADERBOARD_DB)
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript("""
        CREATE TABLE IF NOT EXISTS leaderboard (
            profile TEXT PRIMARY KEY,
            display_name TEXT DEFAULT '',
            level INTEGER DEFAULT 1,
            total_xp INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            quests_done INTEGER DEFAULT 0,
            title TEXT DEFAULT 'Novice',
            title_icon TEXT DEFAULT '',
            profile_photo TEXT DEFAULT '',
            last_sync TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS profiles (
            username TEXT PRIMARY KEY,
            slug TEXT UNIQUE,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS leaderboard_history (
            snap_date TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
    """)
    # Pre-populate special profiles if missing
    c.execute("INSERT OR IGNORE INTO profiles (username, slug) VALUES (?,?)", ("viraj", ""))
    c.execute("INSERT OR IGNORE INTO profiles (username, slug) VALUES (?,?)", ("heman", "heman"))
    c.commit(); c.close()

def _snapshot_leaderboard_if_needed(conn):
    """Take one snapshot per day of the current leaderboard."""
    today = date.today().isoformat()
    existing = conn.execute("SELECT 1 FROM leaderboard_history WHERE snap_date=?",(today,)).fetchone()
    if existing: return
    rows = conn.execute("SELECT * FROM leaderboard ORDER BY total_xp DESC LIMIT 50").fetchall()
    snap = []
    for i, r in enumerate(rows):
        d = dict(r); d["rank"] = i + 1
        snap.append(d)
    conn.execute("INSERT INTO leaderboard_history (snap_date, data) VALUES (?,?)",
                 (today, json.dumps(snap)))
    conn.commit()

_init_leaderboard_db()

def sync_leaderboard(profile, user_dict, quests_done=None):
    """Upsert this profile's stats into the shared leaderboard DB."""
    t = title_for_level(user_dict.get("level", 1))
    c = sqlite3.connect(LEADERBOARD_DB)
    c.execute("PRAGMA journal_mode=WAL")
    if quests_done is None:
        # fetch from profile db
        pc = sqlite3.connect(db_path_for(profile))
        quests_done = pc.execute("SELECT COUNT(*) FROM tasks WHERE status='done'").fetchone()[0]
        pc.close()
    c.execute("""INSERT INTO leaderboard (profile,display_name,level,total_xp,streak,quests_done,title,title_icon,profile_photo,last_sync)
                 VALUES (?,?,?,?,?,?,?,?,?,datetime('now','localtime'))
                 ON CONFLICT(profile) DO UPDATE SET
                 display_name=excluded.display_name, level=excluded.level, total_xp=excluded.total_xp,
                 streak=excluded.streak, quests_done=excluded.quests_done, title=excluded.title,
                 title_icon=excluded.title_icon, profile_photo=excluded.profile_photo, last_sync=excluded.last_sync""",
              (profile or "default", user_dict.get("display_name","Hero"), user_dict.get("level",1),
               user_dict.get("total_xp",0), user_dict.get("streak",0), quests_done,
               t["name"], t["icon"], user_dict.get("profile_photo","")))
    c.commit(); c.close()

# ── Stat levelling ──────────────────────────────────────────────────────────
def stat_level_from_xp(xp):
    return min(99, int(math.sqrt(max(0, xp) / 50)) + 1)

def stat_xp_for_level(lv):  return 50 * ((lv - 1) ** 2)
def stat_xp_for_next(lv):   return 50 * (lv ** 2)

# ── Database ─────────────────────────────────────────────────────────────────
def get_db():
    path = db_path_for(current_profile())
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    # Lazy-init any non-default profile DB the first time it's opened
    if path not in _initialized_dbs:
        with _init_lock:
            if path not in _initialized_dbs:
                _run_schema(c)
                _initialized_dbs.add(path)
    return c

def _run_schema(c):
    """Create tables + run migrations on an open connection. Idempotent."""
    c.executescript("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY DEFAULT 1,
            persona TEXT DEFAULT '', display_name TEXT DEFAULT '',
            bio TEXT DEFAULT '', motivation TEXT DEFAULT '',
            profession TEXT DEFAULT '', profile_photo TEXT DEFAULT '',
            level INTEGER DEFAULT 1, total_xp INTEGER DEFAULT 0,
            int_xp INTEGER DEFAULT 0, dex_xp INTEGER DEFAULT 0,
            cha_xp INTEGER DEFAULT 0, vit_xp INTEGER DEFAULT 0,
            hp INTEGER DEFAULT 100, max_hp INTEGER DEFAULT 100,
            streak INTEGER DEFAULT 0, last_active TEXT DEFAULT '',
            monthly_goal TEXT DEFAULT '', weekly_goal TEXT DEFAULT '',
            onboarded INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL, xp_value INTEGER DEFAULT 100,
            stat TEXT DEFAULT 'INT', energy_cost INTEGER DEFAULT 10,
            timer_minutes INTEGER DEFAULT 30, task_type TEXT DEFAULT 'daily',
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, description TEXT NOT NULL, icon TEXT DEFAULT '',
            earned_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS daily_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            ctype TEXT NOT NULL,
            target_stat TEXT DEFAULT '',
            target_value INTEGER NOT NULL,
            progress INTEGER DEFAULT 0,
            reward_xp INTEGER DEFAULT 100,
            description TEXT NOT NULL,
            icon TEXT DEFAULT '',
            completed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_challenges_date ON daily_challenges(date);

        CREATE TABLE IF NOT EXISTS login_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            day_num INTEGER NOT NULL,
            reward_xp INTEGER NOT NULL,
            bonus TEXT DEFAULT '',
            claimed_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS loot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            rarity TEXT DEFAULT 'common',
            icon TEXT DEFAULT '',
            effect TEXT DEFAULT '',
            earned_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS daily_spins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            result_type TEXT NOT NULL,
            result_value INTEGER NOT NULL,
            result_label TEXT NOT NULL,
            spun_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_key TEXT NOT NULL UNIQUE,
            quantity INTEGER DEFAULT 1,
            acquired_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS pet (
            id INTEGER PRIMARY KEY DEFAULT 1,
            species TEXT DEFAULT '',
            name TEXT DEFAULT '',
            pet_level INTEGER DEFAULT 0,
            pet_xp INTEGER DEFAULT 0,
            happiness INTEGER DEFAULT 80,
            hunger INTEGER DEFAULT 50,
            last_fed TEXT DEFAULT '',
            last_decay TEXT DEFAULT '',
            hatched INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS bounties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            btype TEXT NOT NULL,
            target_stat TEXT DEFAULT '',
            target_value INTEGER NOT NULL,
            progress INTEGER DEFAULT 0,
            reward_gems INTEGER NOT NULL,
            description TEXT NOT NULL,
            icon TEXT DEFAULT '',
            completed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_bounties_date ON bounties(date);

        CREATE TABLE IF NOT EXISTS gifts_received (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_profile TEXT NOT NULL,
            from_display TEXT DEFAULT '',
            item_key TEXT NOT NULL,
            received_at TEXT DEFAULT (datetime('now','localtime')),
            claimed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS gifts_sent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            to_profile TEXT NOT NULL,
            item_key TEXT NOT NULL,
            sent_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS weekly_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT NOT NULL UNIQUE,
            content TEXT NOT NULL,
            generated_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS daily_summaries (
            day TEXT PRIMARY KEY,
            summary TEXT NOT NULL,
            generated_at TEXT DEFAULT (datetime('now','localtime'))
        );
    """)
    if c.execute("SELECT COUNT(*) FROM user").fetchone()[0] == 0:
        c.execute("INSERT INTO user (id) VALUES (1)")
    if c.execute("SELECT COUNT(*) FROM pet").fetchone()[0] == 0:
        c.execute("INSERT INTO pet (id) VALUES (1)")
    user_cols = {r[1] for r in c.execute("PRAGMA table_info(user)").fetchall()}
    task_cols = {r[1] for r in c.execute("PRAGMA table_info(tasks)").fetchall()}
    for col, td in [("display_name","TEXT DEFAULT ''"),("bio","TEXT DEFAULT ''"),
                    ("motivation","TEXT DEFAULT ''"),("profession","TEXT DEFAULT ''"),
                    ("profile_photo","TEXT DEFAULT ''"),
                    ("gems","INTEGER DEFAULT 0"),
                    ("active_boosts","TEXT DEFAULT '{}'"),
                    ("equipped_frame","TEXT DEFAULT ''")]:
        if col not in user_cols: c.execute(f"ALTER TABLE user ADD COLUMN {col} {td}")
    for col, td in [("energy_cost","INTEGER DEFAULT 10"),("timer_minutes","INTEGER DEFAULT 30"),
                    ("task_type","TEXT DEFAULT 'daily'")]:
        if col not in task_cols: c.execute(f"ALTER TABLE tasks ADD COLUMN {col} {td}")
    c.commit()

def init_db():
    """Initialize the default DB at startup."""
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    _run_schema(c)
    c.close()
    _initialized_dbs.add(DB_PATH)

init_db()

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_user(with_penalty=False):
    c = get_db()
    u = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone())
    today = date.today().isoformat()
    penalty = check_missed_tasks(c)
    if penalty:
        u = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone())
    elif u["last_active"] and u["last_active"] != today and u["hp"] < 100:
        c.execute("UPDATE user SET hp=100 WHERE id=1")
        c.commit()
        u["hp"] = 100
    if u["max_hp"] != 100:
        c.execute("UPDATE user SET max_hp=100, hp=MIN(100, hp) WHERE id=1")
        c.commit()
        u["max_hp"] = 100; u["hp"] = min(100, u["hp"])
    c.close()
    if with_penalty:
        return u, penalty
    return u

def xp_for_level(lv): return int(250 * (lv ** 2.2))

def stat_level_from_xp(xp):
    return min(99, int(math.pow(max(0, xp) / 100, 1/2.2)) + 1)

def stat_xp_for_level(lv):
    return int(100 * math.pow(lv - 1, 2.2))

def stat_xp_for_next(lv):
    return stat_xp_for_level(lv + 1)

def calc_energy(stat, xp):
    rate = ENERGY_COSTS.get(stat, 8)
    cost = int((xp / 100) * rate)
    return max(1, min(cost, 25))

def calc_timer(xp, stat):
    base = xp / (4 if stat == "VIT" else 5)
    return max(10, min(120, int(base)))

def enrich(u):
    u["xp_for_next"] = xp_for_level(u["level"])
    u["personas"] = PERSONAS
    t = title_for_level(u["level"])
    u["title"] = t["name"]; u["title_icon"] = t["icon"]
    u["unlocks"] = unlocks_for_level(u["level"])
    nu = next_unlock(u["level"])
    if nu: u["next_unlock"] = nu
    for s in ("int","dex","cha","vit"):
        xp = u.get(f"{s}_xp", 0); lv = stat_level_from_xp(xp)
        u[f"{s}_level"] = lv
        u[f"{s}_xp_current"] = xp - stat_xp_for_level(lv)
        u[f"{s}_xp_needed"]  = stat_xp_for_next(lv) - stat_xp_for_level(lv)
    # Parse active_boosts JSON into a dict for the UI
    try:
        u["active_boosts"] = json.loads(u.get("active_boosts") or "{}")
    except Exception:
        u["active_boosts"] = {}
    u["gems"] = u.get("gems", 0) or 0
    u["equipped_frame"] = u.get("equipped_frame", "") or ""
    return u

def check_level_up(c):
    u = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone())
    leveled = False; old_level = u["level"]
    while u["total_xp"] >= xp_for_level(u["level"]):
        u["level"] += 1; u["max_hp"] = 100; u["hp"] = 100; leveled = True
    if leveled:
        c.execute("UPDATE user SET level=?,max_hp=?,hp=? WHERE id=1",(u["level"],u["max_hp"],u["hp"]))
    # Collect all new unlocks from levels crossed
    all_new = []
    if leveled:
        for lv in range(old_level + 1, u["level"] + 1):
            all_new.extend(new_unlocks_at_level(lv))
    new_title = title_for_level(u["level"]) if leveled else None
    return leveled, u["level"], all_new, new_title

def check_stat_ups(before, after):
    ups = []
    for s in ("int","dex","cha","vit"):
        ol = stat_level_from_xp(before.get(f"{s}_xp",0)); nl = stat_level_from_xp(after.get(f"{s}_xp",0))
        if nl > ol: ups.append({"stat":s.upper(),"old_level":ol,"new_level":nl})
    return ups

def check_achievements(c):
    u = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone())
    existing = {r["title"] for r in c.execute("SELECT title FROM achievements").fetchall()}
    done_count = c.execute("SELECT COUNT(*) FROM tasks WHERE status='done'").fetchone()[0]
    today = date.today().isoformat()
    today_done = c.execute("SELECT COUNT(*) FROM tasks WHERE status='done' AND date(completed_at)=? AND task_type='daily'",(today,)).fetchone()[0]
    today_pending = c.execute("SELECT COUNT(*) FROM tasks WHERE status='pending' AND task_type='daily'").fetchone()[0]
    ch_done_today = c.execute("SELECT COUNT(*) FROM daily_challenges WHERE date=? AND completed_at IS NOT NULL",(today,)).fetchone()[0]
    ch_total_today = c.execute("SELECT COUNT(*) FROM daily_challenges WHERE date=?",(today,)).fetchone()[0]
    new_ach = []
    tiers = [
        ("First Blood","Complete your first quest","\U0001F5E1\uFE0F", u["total_xp"]>0),
        ("Streak Starter","3-day streak","\U0001F525", u["streak"]>=3),
        ("Streak Master","7-day streak","\U0001F525", u["streak"]>=7),
        ("Streak Legend","14-day streak","\U0001F525", u["streak"]>=14),
        ("Streak Titan","30-day streak","\U0001F31F", u["streak"]>=30),
        ("Streak Immortal","60-day streak","\U0001F3C6", u["streak"]>=60),
        ("Streak God","100-day streak","\U0001F451", u["streak"]>=100),
        ("INT Initiate","1000 INT XP","\U0001F4DA", u["int_xp"]>=1000),
        ("DEX Initiate","1000 DEX XP","\u26A1", u["dex_xp"]>=1000),
        ("CHA Initiate","1000 CHA XP","\U0001F3AD", u["cha_xp"]>=1000),
        ("VIT Initiate","1000 VIT XP","\U0001F4AA", u["vit_xp"]>=1000),
        ("INT Master","5000 INT XP","\U0001F9E0", u["int_xp"]>=5000),
        ("DEX Master","5000 DEX XP","\U0001F3AF", u["dex_xp"]>=5000),
        ("CHA Master","5000 CHA XP","\U0001F31F", u["cha_xp"]>=5000),
        ("VIT Master","5000 VIT XP","\U0001F3CB\uFE0F", u["vit_xp"]>=5000),
        ("Level 5","Reach Level 5","\u2B50", u["level"]>=5),
        ("Level 10","Reach Level 10","\u2B50", u["level"]>=10),
        ("Level 25","Reach Level 25","\U0001F4AB", u["level"]>=25),
        ("Level 50","Reach Level 50","\U0001F308", u["level"]>=50),
        ("Centurion","10000 total XP","\U0001F4AF", u["total_xp"]>=10000),
        ("Epic Grind","50000 total XP","\U0001F480", u["total_xp"]>=50000),
        ("Quest Hunter","50 quests completed","\U0001F3F9", done_count>=50),
        ("Quest Slayer","100 quests completed","\u2694\uFE0F", done_count>=100),
        ("Quest Legend","500 quests completed","\U0001F3C5", done_count>=500),
        ("Perfect Day","Complete every daily quest","\u2728", today_done>=3 and today_pending==0),
        ("Challenger","Complete a daily challenge","\U0001F3AF", ch_done_today>=1),
        ("Triple Threat","All 3 daily challenges done","\U0001F525", ch_total_today>=3 and ch_done_today>=3),
    ]
    for title, desc, icon, cond in tiers:
        if cond and title not in existing:
            c.execute("INSERT INTO achievements (title,description,icon) VALUES (?,?,?)",(title,desc,icon))
            new_ach.append({"title":title,"description":desc,"icon":icon})
    return new_ach

# ── Daily Challenges ─────────────────────────────────────────────────────────
import random as _rand

CHALLENGE_POOL = [
    ("stat_xp","INT",200,120,"Earn 200 INT XP today","\U0001F4DA"),
    ("stat_xp","INT",400,220,"Level up your mind — 400 INT XP","\U0001F9E0"),
    ("stat_xp","DEX",200,120,"Earn 200 DEX XP today","\u26A1"),
    ("stat_xp","DEX",400,220,"Sharpen DEX — 400 DEX XP","\U0001F3AF"),
    ("stat_xp","CHA",200,120,"Earn 200 CHA XP today","\U0001F3AD"),
    ("stat_xp","CHA",400,220,"Charm offensive — 400 CHA XP","\U0001F31F"),
    ("stat_xp","VIT",200,120,"Earn 200 VIT XP today","\U0001F4AA"),
    ("stat_xp","VIT",400,220,"Forge the body — 400 VIT XP","\U0001F3CB\uFE0F"),
    ("any_xp","",500,180,"Earn 500 XP any way you want","\u2728"),
    ("any_xp","",1000,350,"Big day — earn 1000 XP","\U0001F4AB"),
    ("quest_count","",3,150,"Complete 3 quests","\u2705"),
    ("quest_count","",5,280,"Complete 5 quests today","\U0001F3C6"),
    ("quest_count","",7,450,"Crush 7 quests — legendary","\U0001F525"),
]

def ensure_daily_challenges(c):
    today = date.today().isoformat()
    existing = c.execute("SELECT COUNT(*) FROM daily_challenges WHERE date=?",(today,)).fetchone()[0]
    if existing > 0: return
    seed = int(today.replace("-",""))
    rng = _rand.Random(seed)
    picks = []
    pool = list(CHALLENGE_POOL)
    rng.shuffle(pool)
    used_types = set()
    for ch in pool:
        key = (ch[0], ch[1])
        if key in used_types: continue
        picks.append(ch); used_types.add(key)
        if len(picks) >= 3: break
    for ctype, stat, target, reward, desc, icon in picks:
        c.execute("INSERT INTO daily_challenges (date,ctype,target_stat,target_value,reward_xp,description,icon) VALUES (?,?,?,?,?,?,?)",
                  (today, ctype, stat, target, reward, desc, icon))
    c.commit()

def update_challenge_progress(c, task_stat, task_xp):
    """Advance today's challenges. Returns list of newly-completed challenges (with reward XP already granted)."""
    today = date.today().isoformat()
    ensure_daily_challenges(c)
    rows = c.execute("SELECT * FROM daily_challenges WHERE date=? AND completed_at IS NULL",(today,)).fetchall()
    newly = []
    for r in rows:
        r = dict(r)
        inc = 0
        if r["ctype"] == "stat_xp" and r["target_stat"] == task_stat:
            inc = task_xp
        elif r["ctype"] == "any_xp":
            inc = task_xp
        elif r["ctype"] == "quest_count":
            inc = 1
        if inc <= 0: continue
        new_prog = min(r["target_value"], r["progress"] + inc)
        if new_prog >= r["target_value"]:
            c.execute("UPDATE daily_challenges SET progress=?,completed_at=datetime('now','localtime') WHERE id=?",(new_prog, r["id"]))
            c.execute("UPDATE user SET total_xp=total_xp+? WHERE id=1",(r["reward_xp"],))
            gem_reward = 15
            grant_gems(c, gem_reward)
            newly.append({"id":r["id"],"description":r["description"],"icon":r["icon"],"reward_xp":r["reward_xp"],"reward_gems":gem_reward})
        else:
            c.execute("UPDATE daily_challenges SET progress=? WHERE id=?",(new_prog, r["id"]))
    return newly

# ── Login Rewards (7-day cycle) ──────────────────────────────────────────
LOGIN_REWARDS = [
    (1, 50,  "",           "Day 1 — Welcome back!"),
    (2, 75,  "",           "Day 2 — Building momentum"),
    (3, 100, "",           "Day 3 — Hat trick!"),
    (4, 125, "",           "Day 4 — Unstoppable"),
    (5, 150, "",           "Day 5 — Halfway hero"),
    (6, 200, "",           "Day 6 — Almost there..."),
    (7, 500, "jackpot",    "Day 7 — JACKPOT! Massive bonus!"),
]

def claim_login_reward(c):
    """Claim today's login reward. Returns reward dict or None if already claimed."""
    today = date.today().isoformat()
    existing = c.execute("SELECT id FROM login_rewards WHERE date=?",(today,)).fetchone()
    if existing: return None
    # Figure out which day in cycle
    count = c.execute("SELECT COUNT(*) FROM login_rewards").fetchone()[0]
    day_num = (count % 7) + 1
    _, xp, bonus, desc = LOGIN_REWARDS[day_num - 1]
    c.execute("INSERT INTO login_rewards (date,day_num,reward_xp,bonus) VALUES (?,?,?,?)",
              (today, day_num, xp, bonus))
    c.execute("UPDATE user SET total_xp=total_xp+? WHERE id=1", (xp,))
    c.commit()
    return {"day_num": day_num, "reward_xp": xp, "bonus": bonus, "description": desc, "total_days": 7}

def get_login_streak_info(c):
    """Return login reward cycle info for the UI."""
    today = date.today().isoformat()
    count = c.execute("SELECT COUNT(*) FROM login_rewards").fetchone()[0]
    claimed_today = c.execute("SELECT id FROM login_rewards WHERE date=?",(today,)).fetchone() is not None
    current_day = (count % 7) if claimed_today else (count % 7)
    cycle = []
    for day_num, xp, bonus, desc in LOGIN_REWARDS:
        cycle.append({"day": day_num, "xp": xp, "bonus": bonus, "desc": desc,
                       "claimed": day_num <= current_day if claimed_today else day_num <= current_day})
    return {"cycle": cycle, "current_day": current_day, "claimed_today": claimed_today, "total_claimed": count}

# ── Loot Drops ───────────────────────────────────────────────────────────
LOOT_TABLE = [
    # (weight, rarity, name, icon, description, effect)
    (40, "common",    "Copper Coin",       "\U0001FA99", "A humble copper coin",            "xp_25"),
    (25, "common",    "Minor Scroll",      "\U0001F4DC", "A scroll of minor wisdom",        "xp_50"),
    (15, "uncommon",  "Silver Amulet",     "\U0001F4BF", "Gleams with potential",            "xp_100"),
    (8,  "uncommon",  "Focus Crystal",     "\U0001F48E", "Sharpens your mind",              "stat_int_50"),
    (8,  "uncommon",  "Swift Boots",       "\U0001F462", "Move faster, do more",            "stat_dex_50"),
    (6,  "rare",      "Golden Chalice",    "\U0001F3C6", "A prize for the worthy",          "xp_250"),
    (5,  "rare",      "Phoenix Feather",   "\U0001FAB6", "Rise from the ashes",             "hp_full"),
    (4,  "rare",      "Enchanted Quill",   "\U0001FAB6", "Words flow like magic",           "stat_cha_75"),
    (3,  "epic",      "Dragon Scale",      "\U0001F432", "Legendary armor fragment",        "xp_500"),
    (2,  "epic",      "Titan's Heart",     "\u2764\uFE0F", "Boundless vitality",            "stat_vit_150"),
    (1,  "epic",      "Void Crystal",      "\U0001F52E", "Absorbs pure energy",             "xp_750"),
    (0.5,"legendary", "Crown of Ages",     "\U0001F451", "Worn by legends alone",           "xp_1000"),
    (0.3,"legendary", "Infinity Gem",      "\U0001F48E", "Power beyond measure",            "all_stats_100"),
    (0.2,"legendary", "Phoenix Egg",       "\U0001F525", "Rebirth in golden flame",         "xp_2000"),
]

def roll_loot(c, xp_gained, force=False):
    """Maybe drop loot after completing a quest. Higher XP = better chance. Returns loot dict or None."""
    # Base drop chance: 35%, scales with XP
    chance = min(0.65, 0.35 + (xp_gained / 2000))
    # Loot Luck boost doubles chance
    try:
        _bs = get_active_boosts(c)
        if "loot_luck" in _bs:
            chance = min(0.95, chance * _bs["loot_luck"].get("value", 2.0))
    except Exception:
        pass
    if not force and _rand.random() > chance: return None
    # Weighted random pick
    total_w = sum(w for w, *_ in LOOT_TABLE)
    r = _rand.random() * total_w
    cumul = 0
    pick = LOOT_TABLE[0]
    for item in LOOT_TABLE:
        cumul += item[0]
        if r <= cumul: pick = item; break
    _, rarity, name, icon, desc, effect = pick
    # Apply effect
    bonus_xp = 0
    if effect.startswith("xp_"):
        bonus_xp = int(effect.split("_")[1])
        c.execute("UPDATE user SET total_xp=total_xp+? WHERE id=1", (bonus_xp,))
    elif effect.startswith("stat_"):
        parts = effect.split("_")
        stat = parts[1]; amt = int(parts[2])
        c.execute(f"UPDATE user SET {stat}_xp={stat}_xp+?,total_xp=total_xp+? WHERE id=1", (amt, amt))
        bonus_xp = amt
    elif effect == "all_stats_100":
        for s in ("int","dex","cha","vit"):
            c.execute(f"UPDATE user SET {s}_xp={s}_xp+100 WHERE id=1")
        c.execute("UPDATE user SET total_xp=total_xp+400 WHERE id=1")
        bonus_xp = 400
    elif effect == "hp_full":
        c.execute("UPDATE user SET hp=max_hp WHERE id=1")
    # Save to inventory
    c.execute("INSERT INTO loot (name,description,rarity,icon,effect) VALUES (?,?,?,?,?)",
              (name, desc, rarity, icon, effect))
    return {"name": name, "description": desc, "rarity": rarity, "icon": icon,
            "effect": effect, "bonus_xp": bonus_xp}

# ── Daily Spin Wheel ─────────────────────────────────────────────────────
SPIN_SLICES = [
    ("xp",   50,  "50 XP",           16),
    ("xp",   100, "100 XP",          14),
    ("xp",   200, "200 XP",          10),
    ("xp",   500, "500 XP",          4),
    ("xp",   1000,"1000 XP JACKPOT", 1),
    ("stat", 50,  "+50 Random Stat",  12),
    ("stat", 100, "+100 Random Stat", 6),
    ("hp",   100, "Full HP Restore",  10),
    ("loot", 1,   "Guaranteed Loot!", 5),
    ("streak",1,  "Streak Shield",    3),
]

def do_daily_spin(c):
    """Spin the wheel. Returns result or None if already spun today."""
    today = date.today().isoformat()
    already = c.execute("SELECT id FROM daily_spins WHERE date=?",(today,)).fetchone()
    if already: return None
    # Weighted pick
    total = sum(s[3] for s in SPIN_SLICES)
    r = _rand.random() * total; cumul = 0; pick = SPIN_SLICES[0]
    for s in SPIN_SLICES:
        cumul += s[3];
        if r <= cumul: pick = s; break
    rtype, rval, rlabel, _ = pick
    bonus_xp = 0; extra = {}
    if rtype == "xp":
        c.execute("UPDATE user SET total_xp=total_xp+? WHERE id=1", (rval,))
        bonus_xp = rval
    elif rtype == "stat":
        stat = _rand.choice(["int","dex","cha","vit"])
        c.execute(f"UPDATE user SET {stat}_xp={stat}_xp+?,total_xp=total_xp+? WHERE id=1", (rval, rval))
        bonus_xp = rval; extra["stat"] = stat.upper()
    elif rtype == "hp":
        c.execute("UPDATE user SET hp=max_hp WHERE id=1")
    elif rtype == "loot":
        loot = roll_loot(c, 999)  # Force good loot
        if loot: extra["loot"] = loot
    elif rtype == "streak":
        extra["streak_shield"] = True
    c.execute("INSERT INTO daily_spins (date,result_type,result_value,result_label) VALUES (?,?,?,?)",
              (today, rtype, rval, rlabel))
    c.commit()
    return {"type": rtype, "value": rval, "label": rlabel, "bonus_xp": bonus_xp, **extra}

# ── Milestones (progress nudges) ─────────────────────────────────────────
def get_milestones(c):
    """Return upcoming milestone progress for the user."""
    u = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone())
    done_count = c.execute("SELECT COUNT(*) FROM tasks WHERE status='done'").fetchone()[0]
    loot_count = c.execute("SELECT COUNT(*) FROM loot").fetchone()[0]
    milestones = []
    # Quest milestones
    for target, label in [(10,"Rookie"),(25,"Adventurer"),(50,"Quest Hunter"),(100,"Quest Slayer"),(250,"Quest Master"),(500,"Quest Legend")]:
        if done_count < target:
            milestones.append({"label":label,"desc":f"Complete {target} quests","current":done_count,"target":target,"icon":"\u2694\uFE0F"})
            break
    # XP milestones
    for target, label in [(1000,"Thousandaire"),(5000,"XP Hoarder"),(10000,"Centurion"),(25000,"XP Baron"),(50000,"XP Tycoon"),(100000,"XP God")]:
        if u["total_xp"] < target:
            milestones.append({"label":label,"desc":f"Earn {target:,} total XP","current":u["total_xp"],"target":target,"icon":"\u2728"})
            break
    # Streak milestones
    for target, label in [(3,"Streak Starter"),(7,"Week Warrior"),(14,"Fortnight Force"),(30,"Monthly Master"),(60,"Iron Will"),(100,"Streak God")]:
        if u["streak"] < target:
            milestones.append({"label":label,"desc":f"Reach {target}-day streak","current":u["streak"],"target":target,"icon":"\U0001F525"})
            break
    # Level milestones
    for target, label in [(5,"Adventurer"),(10,"Double Digits"),(20,"Champion"),(30,"Master"),(50,"Legend"),(99,"Transcendent")]:
        if u["level"] < target:
            milestones.append({"label":label,"desc":f"Reach Level {target}","current":u["level"],"target":target,"icon":"\u2B50"})
            break
    # Loot milestones
    for target, label in [(5,"Collector"),(15,"Treasure Hunter"),(30,"Loot Goblin"),(50,"Dragon Hoarder")]:
        if loot_count < target:
            milestones.append({"label":label,"desc":f"Find {target} items","current":loot_count,"target":target,"icon":"\U0001F48E"})
            break
    return milestones

def update_streak(c):
    u = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone())
    today = date.today().isoformat(); last = u["last_active"]
    if last == today: return u["streak"]
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    ns = u["streak"]+1 if last == yesterday else 1
    c.execute("UPDATE user SET streak=?,last_active=?,hp=100 WHERE id=1",(ns, today)); return ns

def check_missed_tasks(c):
    """Fail any pending daily tasks from prior days, penalize streak + HP.
    Returns a penalty dict if anything was newly failed, else None."""
    today = date.today().isoformat()
    rows = c.execute(
        "SELECT id,xp_value FROM tasks WHERE task_type='daily' AND status='pending' AND date(created_at)<?",
        (today,)
    ).fetchall()
    if not rows: return None
    missed = len(rows)
    c.execute(
        "UPDATE tasks SET status='failed',completed_at=datetime('now','localtime') "
        "WHERE task_type='daily' AND status='pending' AND date(created_at)<?",
        (today,)
    )
    u = dict(c.execute("SELECT streak,hp FROM user WHERE id=1").fetchone())
    streak_lost = u["streak"]
    hp_dmg = min(u["hp"], 25 * missed)
    new_hp = max(0, u["hp"] - 25 * missed)
    c.execute("UPDATE user SET streak=0,hp=? WHERE id=1", (new_hp,))
    c.commit()
    return {"missed": missed, "hp_lost": hp_dmg, "streak_lost": streak_lost, "new_hp": new_hp}

# ── Gems / Shop / Pet / Bounties / Boosts ────────────────────────────────
SHOP_ITEMS = {
    # Power-ups
    "xp_boost_24h":   {"name":"XP Boost",         "icon":"\U0001F680",       "category":"powerup", "price":30,  "desc":"+50% XP for 24 hours",           "effect":{"type":"xp_mult","value":1.5,"duration_h":24}},
    "streak_shield":  {"name":"Streak Shield",    "icon":"\U0001F6E1\uFE0F", "category":"powerup", "price":50,  "desc":"Protect streak from one missed day","effect":{"type":"streak_shield"}},
    "energy_potion":  {"name":"Energy Potion",    "icon":"\U0001F9EA",       "category":"powerup", "price":20,  "desc":"Instantly restore HP to full",    "effect":{"type":"hp_full"}},
    "loot_luck":      {"name":"Loot Luck",        "icon":"\U0001F340",       "category":"powerup", "price":40,  "desc":"+100% loot drop rate for 12h",    "effect":{"type":"loot_mult","value":2.0,"duration_h":12}},
    "focus_crystal":  {"name":"Focus Crystal",    "icon":"\U0001F48E",       "category":"powerup", "price":60,  "desc":"+75% XP for your next 5 quests",  "effect":{"type":"xp_charges","value":1.75,"charges":5}},
    "quest_reroll":   {"name":"Quest Reroll",     "icon":"\U0001F500",       "category":"powerup", "price":25,  "desc":"Reroll one quest you don't like", "effect":{"type":"quest_reroll"}},
    # Mystery boxes
    "mystery_common":    {"name":"Common Box",    "icon":"\U0001F4E6",       "category":"mystery", "price":30,  "desc":"Random reward — common to rare"},
    "mystery_rare":      {"name":"Rare Box",      "icon":"\U0001F381",       "category":"mystery", "price":100, "desc":"Random reward — rare to epic"},
    "mystery_legendary": {"name":"Legendary Box", "icon":"\u2728",           "category":"mystery", "price":500, "desc":"Random reward — epic to legendary"},
    # Pet items
    "pet_food":       {"name":"Pet Food",         "icon":"\U0001F356",       "category":"pet",     "price":10,  "desc":"Feed your companion — +30 hunger"},
    "pet_treat":      {"name":"Pet Treat",        "icon":"\U0001F36B",       "category":"pet",     "price":25,  "desc":"Hunger + happiness — +40 both"},
    "evolution_stone":{"name":"Evolution Stone",  "icon":"\U0001F48E",       "category":"pet",     "price":300, "desc":"Grant your pet +500 XP"},
    "mystery_egg":    {"name":"Mystery Egg",      "icon":"\U0001F95A",       "category":"pet",     "price":200, "desc":"Hatch a brand new companion"},
    # Cosmetics
    "frame_neon":     {"name":"Neon Frame",       "icon":"\U0001F309",       "category":"cosmetic","price":150, "desc":"Glowing neon profile border"},
    "frame_gold":     {"name":"Gold Frame",       "icon":"\U0001F3C6",       "category":"cosmetic","price":300, "desc":"Regal gold profile border"},
    "frame_rainbow":  {"name":"Rainbow Frame",    "icon":"\U0001F308",       "category":"cosmetic","price":500, "desc":"Animated rainbow profile border"},
}

PET_SPECIES = [
    {"key":"dragon",  "name":"Dragon",  "icon":"\U0001F409", "desc":"Fiery companion — confident & bold"},
    {"key":"phoenix", "name":"Phoenix", "icon":"\U0001F426", "desc":"Reborn daily — your streak ally"},
    {"key":"wolf",    "name":"Wolf",    "icon":"\U0001F43A", "desc":"Loyal hunter — consistency totem"},
    {"key":"owl",     "name":"Owl",     "icon":"\U0001F989", "desc":"Wise study partner — for scholars"},
    {"key":"fox",     "name":"Fox",     "icon":"\U0001F98A", "desc":"Clever & quick — for the nimble"},
]

PET_STAGES = [
    {"key":"egg",       "name":"Egg",       "min_level":0,  "xp_to_next":100,    "xp_mult":1.00, "perk":""},
    {"key":"baby",      "name":"Baby",      "min_level":1,  "xp_to_next":300,    "xp_mult":1.02, "perk":"+2% XP gain"},
    {"key":"juvenile",  "name":"Juvenile",  "min_level":3,  "xp_to_next":700,    "xp_mult":1.05, "perk":"+5% XP gain"},
    {"key":"adult",     "name":"Adult",     "min_level":10, "xp_to_next":1500,   "xp_mult":1.10, "perk":"+10% XP gain"},
    {"key":"ancient",   "name":"Ancient",   "min_level":20, "xp_to_next":999999, "xp_mult":1.15, "perk":"+15% XP, streak immunity"},
]

BOUNTY_POOL = [
    ("quest_count",    "",    3,   15, "Complete 3 quests today",       "\u2705"),
    ("quest_count",    "",    5,   25, "Complete 5 quests today",       "\U0001F3C6"),
    ("stat_xp",        "INT", 200, 20, "Earn 200 INT XP",               "\U0001F4DA"),
    ("stat_xp",        "DEX", 200, 20, "Earn 200 DEX XP",               "\u26A1"),
    ("stat_xp",        "CHA", 200, 20, "Earn 200 CHA XP",               "\U0001F3AD"),
    ("stat_xp",        "VIT", 200, 20, "Earn 200 VIT XP",               "\U0001F4AA"),
    ("any_xp",         "",    500, 25, "Earn 500 total XP today",       "\u2728"),
    ("any_xp",         "",    1000,40, "Earn 1000 total XP today",      "\U0001F4AB"),
    ("challenge_done", "",    1,   30, "Complete 1 daily challenge",    "\U0001F3AF"),
    ("loot_count",     "",    2,   35, "Find 2 loot items today",       "\U0001F48E"),
]

# ── Gems & Boosts helpers ────────────────────────────────────────────────
def get_gems(c):
    r = c.execute("SELECT gems FROM user WHERE id=1").fetchone()
    return r["gems"] if r else 0

def grant_gems(c, amount):
    if amount <= 0: return 0
    c.execute("UPDATE user SET gems=gems+? WHERE id=1", (amount,))
    return amount

def spend_gems(c, amount):
    r = c.execute("SELECT gems FROM user WHERE id=1").fetchone()
    if not r or r["gems"] < amount: return False
    c.execute("UPDATE user SET gems=gems-? WHERE id=1", (amount,))
    return True

def get_active_boosts(c):
    """Return dict of active boost keys -> data. Prunes expired boosts."""
    r = c.execute("SELECT active_boosts FROM user WHERE id=1").fetchone()
    try: boosts = json.loads((r["active_boosts"] if r else None) or "{}")
    except Exception: boosts = {}
    now_iso = datetime.now().isoformat()
    changed = False
    for k in list(boosts.keys()):
        exp = boosts[k].get("expires_at")
        if exp and exp < now_iso:
            del boosts[k]; changed = True
        elif "charges" in boosts[k] and boosts[k]["charges"] <= 0:
            del boosts[k]; changed = True
    if changed:
        c.execute("UPDATE user SET active_boosts=? WHERE id=1", (json.dumps(boosts),))
    return boosts

def add_boost(c, key, data):
    boosts = get_active_boosts(c)
    data = dict(data)
    if "duration_h" in data:
        data["expires_at"] = (datetime.now() + timedelta(hours=data["duration_h"])).isoformat()
    boosts[key] = data
    c.execute("UPDATE user SET active_boosts=? WHERE id=1", (json.dumps(boosts),))

def consume_boost_charge(c, key):
    boosts = get_active_boosts(c)
    if key in boosts and "charges" in boosts[key]:
        boosts[key]["charges"] -= 1
        if boosts[key]["charges"] <= 0:
            del boosts[key]
        c.execute("UPDATE user SET active_boosts=? WHERE id=1", (json.dumps(boosts),))

# ── Pet helpers ──────────────────────────────────────────────────────────
def pet_stage(level):
    cur = PET_STAGES[0]
    for s in PET_STAGES:
        if level >= s["min_level"]: cur = s
    return cur

def get_pet(c):
    r = c.execute("SELECT * FROM pet WHERE id=1").fetchone()
    return dict(r) if r else None

def enrich_pet(p):
    if not p: return None
    stage = pet_stage(p["pet_level"])
    p["stage"] = stage
    species = next((s for s in PET_SPECIES if s["key"] == p["species"]), None)
    p["species_info"] = species or {}
    return p

def apply_pet_decay(c):
    p = get_pet(c)
    if not p or not p["hatched"]: return
    now = datetime.now()
    last = p.get("last_decay") or ""
    try:
        last_dt = datetime.fromisoformat(last) if last else now
    except Exception:
        last_dt = now
    hours = max(0, (now - last_dt).total_seconds() / 3600)
    if hours < 1: return
    dec_hunger = min(int(hours * 2), 50)
    dec_happy  = min(int(hours * 1), 25)
    new_hunger = max(0, p["hunger"] - dec_hunger)
    new_happy  = max(0, p["happiness"] - dec_happy)
    c.execute("UPDATE pet SET hunger=?, happiness=?, last_decay=? WHERE id=1",
              (new_hunger, new_happy, now.isoformat()))

def award_pet_xp(c, amount):
    p = get_pet(c)
    if not p or not p["hatched"] or amount <= 0: return None
    new_xp = p["pet_xp"] + amount
    new_level = p["pet_level"]
    leveled = False
    # Level pet up while it has enough XP, up to level 30
    stage = pet_stage(new_level)
    xp_needed = stage["xp_to_next"]
    while new_xp >= xp_needed and new_level < 30:
        new_xp -= xp_needed
        new_level += 1
        leveled = True
        stage = pet_stage(new_level)
        xp_needed = stage["xp_to_next"]
    c.execute("UPDATE pet SET pet_xp=?, pet_level=? WHERE id=1", (new_xp, new_level))
    if leveled:
        return {"leveled": True, "new_level": new_level, "stage": pet_stage(new_level)}
    return None

def apply_xp_multipliers(c, base_xp):
    """Apply pet + boost XP multipliers. Returns (final_xp, breakdown)."""
    mult = 1.0
    breakdown = []
    pet = get_pet(c)
    if pet and pet["hatched"]:
        st = pet_stage(pet["pet_level"])
        if st["xp_mult"] > 1.0:
            mult *= st["xp_mult"]
            breakdown.append({"source":"pet","label":st["name"],"mult":st["xp_mult"]})
    boosts = get_active_boosts(c)
    if "xp_boost_24h" in boosts:
        v = boosts["xp_boost_24h"].get("value", 1.5)
        mult *= v
        breakdown.append({"source":"xp_boost","label":"XP Boost","mult":v})
    if "focus_crystal" in boosts:
        v = boosts["focus_crystal"].get("value", 1.75)
        mult *= v
        breakdown.append({"source":"focus_crystal","label":"Focus Crystal","mult":v})
        consume_boost_charge(c, "focus_crystal")
    return int(round(base_xp * mult)), breakdown

# ── Inventory helpers ────────────────────────────────────────────────────
def add_to_inventory(c, item_key, qty=1):
    existing = c.execute("SELECT quantity FROM inventory WHERE item_key=?", (item_key,)).fetchone()
    if existing:
        c.execute("UPDATE inventory SET quantity=quantity+? WHERE item_key=?", (qty, item_key))
    else:
        c.execute("INSERT INTO inventory (item_key, quantity) VALUES (?, ?)", (item_key, qty))

def remove_from_inventory(c, item_key, qty=1):
    existing = c.execute("SELECT quantity FROM inventory WHERE item_key=?", (item_key,)).fetchone()
    if not existing or existing["quantity"] < qty: return False
    if existing["quantity"] == qty:
        c.execute("DELETE FROM inventory WHERE item_key=?", (item_key,))
    else:
        c.execute("UPDATE inventory SET quantity=quantity-? WHERE item_key=?", (qty, item_key))
    return True

def get_inventory(c):
    # Fetch from inventory table (purchased items)
    inv_rows = c.execute("SELECT * FROM inventory WHERE quantity>0 ORDER BY acquired_at DESC").fetchall()
    out = []
    for r in inv_rows:
        r = dict(r)
        meta = SHOP_ITEMS.get(r["item_key"], {})
        r.update({
            "name": meta.get("name", r["item_key"]),
            "icon": meta.get("icon", "?"),
            "description": meta.get("desc", ""),
            "category": meta.get("category", "misc"),
            "price": meta.get("price", 0),
            "source": "shop"
        })
        out.append(r)
    
    # Fetch from loot table (dropped items)
    loot_rows = c.execute("SELECT * FROM loot ORDER BY earned_at DESC").fetchall()
    for l in loot_rows:
        l = dict(l)
        out.append({
            "item_id": f"loot_{l['id']}",
            "item_key": l["name"], # For loot, name is the key
            "name": l["name"],
            "icon": l["icon"] or "✨",
            "description": l["description"] or "",
            "quantity": 1,
            "category": "loot",
            "source": "loot",
            "rarity": l["rarity"],
            "acquired_at": l["earned_at"]
        })
    return out

# ── Bounties ─────────────────────────────────────────────────────────────
def ensure_daily_bounties(c):
    today = date.today().isoformat()
    existing = c.execute("SELECT COUNT(*) FROM bounties WHERE date=?", (today,)).fetchone()[0]
    if existing > 0: return
    seed = int(today.replace("-","")) + 7777
    rng = _rand.Random(seed)
    pool = list(BOUNTY_POOL); rng.shuffle(pool)
    picks, used = [], set()
    for b in pool:
        k = (b[0], b[1])
        if k in used: continue
        picks.append(b); used.add(k)
        if len(picks) >= 3: break
    for btype, stat, target, reward, desc, icon in picks:
        c.execute("INSERT INTO bounties (date,btype,target_stat,target_value,reward_gems,description,icon) VALUES (?,?,?,?,?,?,?)",
                  (today, btype, stat, target, reward, desc, icon))
    c.commit()

def update_bounty_progress(c, task_stat=None, task_xp=0, loot_drop=False, challenge_count=0):
    today = date.today().isoformat()
    ensure_daily_bounties(c)
    rows = c.execute("SELECT * FROM bounties WHERE date=? AND completed_at IS NULL",(today,)).fetchall()
    newly = []
    total_gems = 0
    for r in rows:
        r = dict(r)
        inc = 0
        if r["btype"] == "quest_count" and task_xp > 0:
            inc = 1
        elif r["btype"] == "any_xp":
            inc = task_xp
        elif r["btype"] == "stat_xp" and r["target_stat"] == task_stat:
            inc = task_xp
        elif r["btype"] == "loot_count" and loot_drop:
            inc = 1
        elif r["btype"] == "challenge_done":
            inc = challenge_count
        if inc <= 0: continue
        new_prog = min(r["target_value"], r["progress"] + inc)
        if new_prog >= r["target_value"]:
            c.execute("UPDATE bounties SET progress=?, completed_at=datetime('now','localtime') WHERE id=?",
                      (new_prog, r["id"]))
            grant_gems(c, r["reward_gems"])
            total_gems += r["reward_gems"]
            newly.append({"description":r["description"],"icon":r["icon"],"reward_gems":r["reward_gems"]})
        else:
            c.execute("UPDATE bounties SET progress=? WHERE id=?", (new_prog, r["id"]))
    return newly, total_gems

# ── Shop rotation ────────────────────────────────────────────────────────
def get_shop_rotation():
    """Pick today's 8-item rotation. Always includes mystery boxes + pet food."""
    today = date.today().isoformat()
    rng = _rand.Random(int(today.replace("-","")))
    always = ["mystery_common", "mystery_rare", "pet_food", "energy_potion"]
    optional = [k for k in SHOP_ITEMS if k not in always]
    rng.shuffle(optional)
    return always + optional[:4]

def open_mystery_box(c, key):
    """Roll a mystery box reward. Returns reward dict."""
    if key == "mystery_common":
        roll = _rand.random()
        if roll < 0.55:
            xp = _rand.choice([50, 100, 150, 200])
            c.execute("UPDATE user SET total_xp=total_xp+? WHERE id=1",(xp,))
            return {"type":"xp","amount":xp,"label":f"+{xp} XP","icon":"\u2728","rarity":"common"}
        elif roll < 0.9:
            gems = _rand.choice([10, 20, 30])
            grant_gems(c, gems)
            return {"type":"gems","amount":gems,"label":f"+{gems} Gems","icon":"\U0001F48E","rarity":"uncommon"}
        else:
            loot = roll_loot(c, 500, force=True)
            return {"type":"loot","loot":loot,"label":loot["name"] if loot else "Nothing","icon":loot["icon"] if loot else "","rarity":loot["rarity"] if loot else "common"}
    elif key == "mystery_rare":
        roll = _rand.random()
        if roll < 0.3:
            xp = _rand.choice([300, 500, 800, 1200])
            c.execute("UPDATE user SET total_xp=total_xp+? WHERE id=1",(xp,))
            return {"type":"xp","amount":xp,"label":f"+{xp} XP","icon":"\u2728","rarity":"rare"}
        elif roll < 0.65:
            gems = _rand.choice([50, 80, 120, 160])
            grant_gems(c, gems)
            return {"type":"gems","amount":gems,"label":f"+{gems} Gems","icon":"\U0001F48E","rarity":"rare"}
        else:
            loot = roll_loot(c, 1500, force=True)
            return {"type":"loot","loot":loot,"label":loot["name"] if loot else "Nothing","icon":loot["icon"] if loot else "","rarity":loot["rarity"] if loot else "rare"}
    elif key == "mystery_legendary":
        roll = _rand.random()
        if roll < 0.4:
            xp = _rand.choice([1500, 2500, 4000, 6000])
            c.execute("UPDATE user SET total_xp=total_xp+? WHERE id=1",(xp,))
            return {"type":"xp","amount":xp,"label":f"+{xp} XP JACKPOT","icon":"\U0001F4AB","rarity":"epic"}
        elif roll < 0.75:
            gems = _rand.choice([200, 350, 500, 750])
            grant_gems(c, gems)
            return {"type":"gems","amount":gems,"label":f"+{gems} Gems","icon":"\U0001F48E","rarity":"epic"}
        else:
            loot = roll_loot(c, 3000, force=True)
            return {"type":"loot","loot":loot,"label":loot["name"] if loot else "Nothing","icon":loot["icon"] if loot else "","rarity":loot["rarity"] if loot else "epic"}
    return {"type":"nothing","label":"Empty","icon":"\U0001F4A8","rarity":"common"}

# ── LLM ──────────────────────────────────────────────────────────────────────
GM_DAILY = """You are the Game Master for a productivity RPG called LEVEL UP.
Generate actionable daily quests tailored to the user's real life context.

RULES:
- Generate exactly 4 daily quests, each completable in one day.
- Use the user's profession, bio and motivation to make tasks hyper-relevant.
- Assign XP 50-500 based on difficulty. Assign ONE stat: INT/DEX/CHA/VIT.
  INT=thinking/coding/research, DEX=hands-on/building, CHA=social/communication, VIT=health/exercise.
- Assign timer_minutes (10-120) estimating how long the task takes.
- Weight toward persona strengths.
- If on streak, push harder. If recent fails, suggest easy wins.
Respond ONLY with valid JSON: {"quests":[{"description":"...","xp":100,"stat":"INT","timer_minutes":30},...]}"""

GM_WEEKLY = """You are the Game Master for a productivity RPG called LEVEL UP.
Generate weekly goals — bigger, multi-day objectives that span the whole week.

RULES:
- Generate exactly 3 weekly goals.
- Each should represent meaningful progress across 2-7 days.
- Use the user's monthly vision, weekly focus, profession and motivation.
- Assign XP 300-1500. Assign ONE stat: INT/DEX/CHA/VIT.
- No timer_minutes needed for weekly goals.
Respond ONLY with valid JSON: {"goals":[{"description":"...","xp":500,"stat":"INT"},...]}"""

GM_MONTHLY = """You are the Game Master for a productivity RPG called LEVEL UP.
Generate monthly milestones — strategic outcomes for the whole month.

RULES:
- Generate exactly 2-3 monthly milestones.
- These are big wins that define the month's success.
- Base them directly on the user's monthly vision and long-term motivation.
- Assign XP 1000-3000. Assign ONE stat: INT/DEX/CHA/VIT.
Respond ONLY with valid JSON: {"milestones":[{"description":"...","xp":1500,"stat":"INT"},...]}"""

GM_BRAINSTORM_DAILY = """You are the Game Master for a productivity RPG called LEVEL UP.
The user has listed one or more specific tasks/topics for today. Generate quests for EACH listed item.

RULES:
- The user's input may be a COMMA-SEPARATED LIST of distinct tasks — treat each comma-separated item as a SEPARATE quest topic. Do NOT collapse them into one.
- Generate exactly ONE quest per distinct comma-separated item. If they list 4 topics, generate 4 quests. If they list 1 topic, generate 1 quest. NEVER generate fewer quests than items listed.
- Maximum 6 quests total. If no commas, treat the whole input as one theme and return 1-3 quests based on complexity.
- REFERENCE RESOLUTION: if the user's focus uses words like "missed", "didn't finish", "failed", "incomplete", "leftover", "redo", "yesterday's missed", "what I skipped", "the ones I missed" — you MUST draw the task descriptions from the MISSED FROM PRIOR DAYS list provided. Re-phrase them as fresh actionable quests for TODAY (e.g. a missed "Write outline for blog" becomes a new daily quest "Write outline for blog (retry)"). Do not invent new themes.
- If the user says "continue" or "follow up", draw from RECENTLY COMPLETED to extend what they already did.
- Use previous tasks ONLY as continuity reference within the same theme. DO NOT import unrelated themes from prior days unless the user asked.
- Assign XP 50-500 based on difficulty. Assign ONE stat: INT/DEX/CHA/VIT.
  INT=thinking/coding/research, DEX=hands-on/building, CHA=social/communication, VIT=health/exercise.
- Assign timer_minutes (10-120).
Respond ONLY with valid JSON: {"quests":[{"description":"...","xp":100,"stat":"DEX","timer_minutes":30},...]}"""

GM_BRAINSTORM_WEEKLY = """You are the Game Master for a productivity RPG called LEVEL UP.
The user has listed one or more specific goals/topics for this week. Generate weekly goals for EACH listed item.

RULES:
- The user's input may be a COMMA-SEPARATED LIST — treat each comma-separated item as a SEPARATE weekly goal. Do NOT collapse them into one.
- Generate exactly ONE goal per distinct comma-separated item. If they list 3 topics, generate 3 goals. Maximum 5 goals total.
- If no commas, treat the whole input as one theme and return 1-2 goals.
- Use past weekly goals ONLY as continuity reference within the same theme.
- Assign XP 300-1500. Assign ONE stat: INT/DEX/CHA/VIT.
Respond ONLY with valid JSON: {"goals":[{"description":"...","xp":500,"stat":"INT"},...]}"""

GM_BRAINSTORM_MONTHLY = """You are the Game Master for a productivity RPG called LEVEL UP.
The user has listed one or more specific outcomes/topics for this month. Generate milestones for EACH listed item.

RULES:
- The user's input may be a COMMA-SEPARATED LIST — treat each comma-separated item as a SEPARATE milestone. Do NOT collapse them into one.
- Generate exactly ONE milestone per distinct comma-separated item. If they list 4 topics, generate 4 milestones. Maximum 6 milestones total.
- If no commas, treat the whole input as one theme and return 1-2 milestones.
- Assign XP 1000-3000. Assign ONE stat: INT/DEX/CHA/VIT.
Respond ONLY with valid JSON: {"milestones":[{"description":"...","xp":1500,"stat":"INT"},...]}"""

def _llm(system, prompt, fallback):
    try:
        r = ollama.chat(model='gemma4:e4b',
                        messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
                        format="json",
                        think=False)
        raw = (r["message"]["content"] or "").strip()
        # Strip markdown fences (```json ... ``` or ``` ... ```) that some models emit despite format=json
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        # Fallback: extract the first {...} block if there's extra prose
        if not raw.startswith("{"):
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m: raw = m.group(0)
        return json.loads(raw)
    except Exception as e:
        print(f"[LLM] {type(e).__name__}: {e}"); return fallback

GM_DAY_SUMMARIZER = """You are a terse summarizer for a productivity RPG.
Summarize the user's day in 20 words or fewer. One compact line, no preamble, no bullet points.
Capture: dominant theme, what progressed, what stalled. Skip filler words.
Respond ONLY with valid JSON: {"summary":"..."}"""

def _generate_day_summary(c, day_iso):
    """Generate a terse AI summary of a given day's tasks. Stores & returns it."""
    rows = c.execute(
        "SELECT description, status, stat, xp_value FROM tasks "
        "WHERE task_type='daily' AND date(created_at)=? ORDER BY id", (day_iso,)).fetchall()
    if not rows:
        summary = "No quests logged."
    else:
        done = [r["description"] for r in rows if r["status"] == "done"]
        failed = [r["description"] for r in rows if r["status"] == "failed"]
        pending = [r["description"] for r in rows if r["status"] == "pending"]
        prompt = (f"Date: {day_iso}\n"
                  f"Completed ({len(done)}): {json.dumps(done) if done else 'none'}\n"
                  f"Failed ({len(failed)}): {json.dumps(failed) if failed else 'none'}\n"
                  f"Unfinished ({len(pending)}): {json.dumps(pending) if pending else 'none'}")
        d = _llm(GM_DAY_SUMMARIZER, prompt, {"summary": f"{len(done)} done, {len(failed)} missed, {len(pending)} unfinished."})
        summary = (d.get("summary") or "").strip() or f"{len(done)} done, {len(failed)} missed."
        # Hard-cap summary length so prompts stay tiny
        if len(summary) > 200: summary = summary[:197].rstrip() + "..."
    c.execute("INSERT OR REPLACE INTO daily_summaries (day, summary, generated_at) VALUES (?,?,datetime('now','localtime'))",
              (day_iso, summary))
    c.commit()
    return summary

def ensure_recent_summaries(c, days=3):
    """Generate any missing per-day summaries for the last `days` days (excluding today).
    Runs lazily: only fills gaps, cached forever otherwise."""
    today = date.today()
    for i in range(1, days + 1):
        d = (today - timedelta(days=i)).isoformat()
        existing = c.execute("SELECT summary FROM daily_summaries WHERE day=?", (d,)).fetchone()
        if existing: continue
        _generate_day_summary(c, d)

def get_recent_context_summary(c, days=3):
    """Return a short multiline context string: one line per recent day."""
    ensure_recent_summaries(c, days)
    today = date.today()
    lines = []
    for i in range(1, days + 1):
        d = (today - timedelta(days=i)).isoformat()
        row = c.execute("SELECT summary FROM daily_summaries WHERE day=?", (d,)).fetchone()
        if row and row["summary"]:
            lines.append(f"- {d}: {row['summary']}")
    return "\n".join(lines) if lines else "No recent activity."

def recent_task_context(c, task_type, days=7):
    """Return (missed, recent_done) dicts keyed by short date strings, for LLM context."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    missed = [dict(r) for r in c.execute(
        "SELECT description, date(created_at) as d FROM tasks "
        "WHERE task_type=? AND status='failed' AND date(created_at)>=? "
        "ORDER BY created_at DESC LIMIT 20", (task_type, cutoff)).fetchall()]
    recent_done = [dict(r) for r in c.execute(
        "SELECT description, date(completed_at) as d FROM tasks "
        "WHERE task_type=? AND status='done' AND date(created_at)>=? AND date(created_at)<? "
        "ORDER BY completed_at DESC LIMIT 15",
        (task_type, cutoff, date.today().isoformat())).fetchall()]
    return missed, recent_done

def _fmt_task_list(items):
    return json.dumps([f"[{t['d']}] {t['description']}" for t in items]) if items else 'None'

def generate_daily(user, pending, completed, intent="", missed=None, recent_done=None):
    p = PERSONAS.get(user["persona"], PERSONAS["operator"])
    missed = missed or []; recent_done = recent_done or []
    if intent:
        c_tmp = get_db()
        context_summary = get_recent_context_summary(c_tmp, days=3)
        c_tmp.close()
        prompt = f"""User focus for today: '{intent}'
Persona: {p['name']} ({p['desc']})
Profession: {user.get('profession') or 'Not specified'}
Past 3 days (AI summary):
{context_summary}
MISSED FROM PRIOR DAYS (failed, not completed): {_fmt_task_list(missed)}
RECENTLY COMPLETED (prior days): {_fmt_task_list(recent_done)}
Pending from yesterday: {json.dumps([t['description'] for t in pending]) if pending else 'None'}
Completed today: {json.dumps([t['description'] for t in completed]) if completed else 'None'}

If the user's focus references missed/failed/skipped tasks, rebuild today's quests from the MISSED list.
If they reference continuing/following up, extend from RECENTLY COMPLETED.
Otherwise generate ONLY tasks that progress the user's stated focus."""
        d = _llm(GM_BRAINSTORM_DAILY, prompt, {"quests":[
            {"description":intent,"xp":150,"stat":"INT","timer_minutes":30}
        ]})
    else:
        c_tmp = get_db()
        context_summary = get_recent_context_summary(c_tmp, days=3)
        c_tmp.close()
        prompt = f"""Today: {date.today().strftime('%A, %B %d %Y')}
User profile:
Name: {user.get('display_name') or 'User'}
Persona: {p['name']} — {p['desc']}
Profession: {user.get('profession') or 'Not specified'}
Bio: {user.get('bio') or 'Not provided'}
Motivation: {user.get('motivation') or 'Self-improvement'}
Monthly Goal: {user['monthly_goal'] or 'Not set'}
Weekly Goal: {user['weekly_goal'] or 'Not set'}
Level: {user['level']}, Streak: {user['streak']} days
Stats: INT={user['int_xp']} DEX={user['dex_xp']} CHA={user['cha_xp']} VIT={user['vit_xp']}
Past 3 days (AI summary):
{context_summary}
Completed today: {json.dumps([t['description'] for t in completed]) if completed else 'None'}
Generate 4 FRESH quests. Build on unfinished themes from the past 3 days but do NOT repeat completed work. Vary themes across profession, weekly goal, and physical health."""
        d = _llm(GM_DAILY, prompt, {"quests":[
            {"description":"Review your weekly goal and plan next steps","xp":100,"stat":"INT","timer_minutes":25},
            {"description":"Take a 20-minute walk or stretch session","xp":80,"stat":"VIT","timer_minutes":20},
            {"description":"Reach out to one person in your network","xp":120,"stat":"CHA","timer_minutes":15},
            {"description":"Work on one hands-on task for 30 minutes","xp":150,"stat":"DEX","timer_minutes":30},
        ]})
    return d.get("quests", [])

def generate_weekly(user, intent=""):
    p = PERSONAS.get(user["persona"], PERSONAS["operator"])
    if intent:
        prompt = f"""User focus for this week: '{intent}'
Persona: {p['name']} ({p['desc']})
Profession: {user.get('profession','')}

Generate ONLY weekly goals that progress this focus. Do not add unrelated themes."""
        d = _llm(GM_BRAINSTORM_WEEKLY, prompt, {"goals":[
            {"description":intent,"xp":500,"stat":"INT"}
        ]})
    else:
        prompt = f"""Persona: {p['name']}, Profession: {user.get('profession','')}, Bio: {user.get('bio','')},
Monthly Vision: {user['monthly_goal'] or 'Not set'}, Weekly Focus: {user['weekly_goal'] or 'Not set'},
Motivation: {user.get('motivation','')}"""
        d = _llm(GM_WEEKLY, prompt, {"goals":[
            {"description":"Complete a meaningful project milestone this week","xp":500,"stat":"INT"},
            {"description":"Build a positive new habit for 7 consecutive days","xp":400,"stat":"VIT"},
            {"description":"Expand your professional network by 3 connections","xp":350,"stat":"CHA"},
        ]})
    return d.get("goals", [])

def generate_monthly(user, intent=""):
    p = PERSONAS.get(user["persona"], PERSONAS["operator"])
    if intent:
        prompt = f"""User focus for this month: '{intent}'
Persona: {p['name']} ({p['desc']})
Profession: {user.get('profession','')}

Generate ONLY monthly milestones that progress this focus. Do not add unrelated themes."""
        d = _llm(GM_BRAINSTORM_MONTHLY, prompt, {"milestones":[
            {"description":intent,"xp":1500,"stat":"INT"}
        ]})
    else:
        prompt = f"""Persona: {p['name']}, Profession: {user.get('profession','')}, Bio: {user.get('bio','')},
Monthly Vision: {user['monthly_goal'] or 'Not set'}, Motivation: {user.get('motivation','')}"""
        d = _llm(GM_MONTHLY, prompt, {"milestones":[
            {"description":"Ship a complete, usable version of your main project","xp":2000,"stat":"INT"},
            {"description":"Establish a consistent daily routine for the full month","xp":1500,"stat":"VIT"},
        ]})
    return d.get("milestones", [])

def categorize(desc):
    d = _llm("""Categorize a task for a productivity RPG. Respond ONLY JSON:
{"stat":"INT","xp":100,"timer_minutes":30}
Stats: INT=thinking/coding, DEX=hands-on, CHA=social, VIT=health. XP 50-500, timer 10-120.""",
              desc, {"stat":"INT","xp":100,"timer_minutes":30})
    stat = d.get("stat","INT")
    if stat not in ("INT","DEX","CHA","VIT"): stat = "INT"
    return stat, min(500,max(50,d.get("xp",100))), min(120,max(10,d.get("timer_minutes",30)))

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
@app.route("/<slug>")
def index(slug=""):
    # Only accept slug-shaped paths; anything else should 404 via Flask's routing
    if slug and not re.fullmatch(r'[a-z0-9_]{1,32}', slug):
        return "Not found", 404
    return render_template("index.html")

# ── Auth & Identity ────────────────────────────────────────────────────────────
def _slugify(text):
    s = text.lower().strip()
    s = re.sub(r'[^a-z0-9_]', '_', s)
    return s[:32]

@app.route("/api/auth/profiles")
def api_auth_discovery():
    c = sqlite3.connect(LEADERBOARD_DB)
    c.row_factory = sqlite3.Row
    # Join with leaderboard to get levels/titles for the selection screen
    rows = c.execute("""
        SELECT p.username, p.slug, l.level, l.title, l.title_icon, l.profile_photo
        FROM profiles p
        LEFT JOIN leaderboard l ON p.slug = l.profile
        ORDER BY l.level DESC, p.created_at ASC
    """).fetchall()
    c.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    d = request.get_json(silent=True) or {}
    un = (d.get("username") or "").strip()
    if not un: return jsonify({"error": "Username required"}), 400
    
    un_low = un.lower()
    c = sqlite3.connect(LEADERBOARD_DB)
    c.row_factory = sqlite3.Row
    
    # Check exact case-insensitive match
    row = c.execute("SELECT * FROM profiles WHERE LOWER(username) = ?", (un_low,)).fetchone()
    if row:
        c.close()
        return jsonify({"slug": row["slug"], "username": row["username"]})
    
    # Create new profile
    slug = _slugify(un)
    # Ensure slug uniqueness
    if c.execute("SELECT 1 FROM profiles WHERE slug = ?", (slug,)).fetchone():
        slug = f"{slug}_{uuid.uuid4().hex[:6]}"
        
    c.execute("INSERT INTO profiles (username, slug) VALUES (?, ?)", (un, slug))
    c.commit(); c.close()
    return jsonify({"slug": slug, "username": un})

@app.route("/api/user")
def api_user():
    u, penalty = get_user(with_penalty=True)
    data = enrich(u)
    if penalty:
        data["penalty"] = penalty
        broadcast()
    # Auto-sync to leaderboard on every load (so user always appears)
    if u.get("onboarded"):
        try: sync_leaderboard(current_profile(), u)
        except Exception: pass
    return jsonify(data)

@app.route("/api/onboard", methods=["POST"])
def api_onboard():
    d = request.json; c = get_db()
    c.execute("""UPDATE user SET persona=?,display_name=?,profession=?,motivation=?,bio=?,
                 monthly_goal=?,weekly_goal=?,onboarded=1 WHERE id=1""",
              (d.get("persona","operator"),d.get("display_name",""),d.get("profession",""),
               d.get("motivation",""),d.get("bio",""),d.get("monthly_goal",""),d.get("weekly_goal","")))
    c.commit()
    u = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone())
    c.close()
    try: sync_leaderboard(current_profile(), u)
    except Exception: pass
    broadcast()
    return jsonify({"ok":True})

@app.route("/api/user/update", methods=["POST"])
def api_user_update():
    d = request.json; c = get_db()
    allowed = ["display_name","bio","motivation","profession","persona","monthly_goal","weekly_goal"]
    fields,vals = [],[]
    for k in allowed:
        if k in d: fields.append(f"{k}=?"); vals.append(d[k])
    if fields:
        vals.append(1); c.execute(f"UPDATE user SET {','.join(fields)} WHERE id=?", vals); c.commit()
    c.close()
    broadcast()
    return jsonify({"ok":True})

@app.route("/api/user/photo", methods=["POST"])
def api_photo_upload():
    if "photo" not in request.files: return jsonify({"error":"No file"}),400
    f = request.files["photo"]
    ext = (f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else "png")
    if ext not in ("png","jpg","jpeg","gif","webp"): return jsonify({"error":"Invalid type"}),400
    fname = f"profile_{uuid.uuid4().hex[:8]}.{ext}"
    f.save(os.path.join(UPLOAD_DIR, fname))
    c = get_db()
    old = c.execute("SELECT profile_photo FROM user WHERE id=1").fetchone()
    if old and old["profile_photo"]:
        op = os.path.join(UPLOAD_DIR, old["profile_photo"])
        if os.path.exists(op): os.remove(op)
    c.execute("UPDATE user SET profile_photo=? WHERE id=1",(fname,)); c.commit(); c.close()
    broadcast()
    return jsonify({"ok":True,"filename":fname})

@app.route("/api/user/photo", methods=["DELETE"])
def api_photo_delete():
    c = get_db()
    old = c.execute("SELECT profile_photo FROM user WHERE id=1").fetchone()
    if old and old["profile_photo"]:
        op = os.path.join(UPLOAD_DIR, old["profile_photo"])
        if os.path.exists(op): os.remove(op)
    c.execute("UPDATE user SET profile_photo='' WHERE id=1"); c.commit(); c.close()
    broadcast()
    return jsonify({"ok":True})

@app.route("/api/tasks")
def api_tasks():
    c = get_db(); today = date.today().isoformat()
    week_start  = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    month_start = date.today().replace(day=1).isoformat()

    daily   = [dict(r) for r in c.execute("SELECT * FROM tasks WHERE task_type='daily' AND date(created_at)=? ORDER BY status ASC,id DESC",(today,)).fetchall()]
    tomorrow_tasks= [dict(r) for r in c.execute("SELECT * FROM tasks WHERE task_type='daily' AND date(created_at)=? ORDER BY status ASC,id DESC",((date.today() + timedelta(days=1)).isoformat(),)).fetchall()]
    weekly  = [dict(r) for r in c.execute("SELECT * FROM tasks WHERE task_type='weekly' AND date(created_at)>=? ORDER BY status ASC,id DESC",(week_start,)).fetchall()]
    monthly = [dict(r) for r in c.execute("SELECT * FROM tasks WHERE task_type='monthly' AND date(created_at)>=? ORDER BY status ASC,id DESC",(month_start,)).fetchall()]

    next_month = (date.today().replace(day=28)+timedelta(days=4)).replace(day=1)
    c.close()
    return jsonify({
        "daily": daily, "tomorrow": tomorrow_tasks, "weekly": weekly, "monthly": monthly,
        "can_tick_weekly": date.today().weekday() >= 5,
        "can_tick_monthly": (next_month - date.today()).days <= 2,
        "today": today,
    })

@app.route("/api/history")
def api_history():
    c = get_db(); today = date.today().isoformat()
    week_start  = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    month_start = date.today().replace(day=1).isoformat()

    past_daily = [dict(r) for r in c.execute(
        "SELECT *,date(created_at) as d FROM tasks WHERE task_type='daily' AND date(created_at)<? ORDER BY created_at DESC",(today,)).fetchall()]
    past_weekly = [dict(r) for r in c.execute(
        "SELECT * FROM tasks WHERE task_type='weekly' AND date(created_at)<? ORDER BY created_at DESC",(week_start,)).fetchall()]
    past_monthly = [dict(r) for r in c.execute(
        "SELECT * FROM tasks WHERE task_type='monthly' AND date(created_at)<? ORDER BY created_at DESC",(month_start,)).fetchall()]
    summaries = {r["day"]: r["summary"] for r in c.execute("SELECT day, summary FROM daily_summaries").fetchall()}
    c.close()

    by_date = {}
    for t in past_daily:
        d = t.pop("d",""); t.pop("task_date",None)
        if not d: continue
        by_date.setdefault(d, {"date":d,"tasks":[],"xp":0,"completed":0,"total":0,"summary":summaries.get(d,"")})
        by_date[d]["tasks"].append(t); by_date[d]["total"] += 1
        if t["status"] == "done":
            by_date[d]["xp"] += t["xp_value"]; by_date[d]["completed"] += 1

    return jsonify({
        "daily_days": sorted(by_date.values(), key=lambda x: x["date"], reverse=True),
        "weekly": past_weekly, "monthly": past_monthly,
    })

def _shape_daily(q):
    stat = q.get("stat","INT") if q.get("stat") in ("INT","DEX","CHA","VIT") else "INT"
    xp   = min(500, max(50, q.get("xp", q.get("xp_value", 100))))
    tmr  = min(120, max(10, q.get("timer_minutes", 30)))
    return stat, xp, tmr, calc_energy(stat, xp)

def _preview_flag():
    d = request.get_json(silent=True) or {}
    return bool(d.get("preview")) or request.args.get("preview") in ("1","true","yes")

@app.route("/api/tasks/generate", methods=["POST"])
def api_gen_daily():
    d = request.get_json(silent=True) or {}
    intent = d.get("intent", "").strip()
    u = get_user(); c = get_db(); today = date.today().isoformat()
    pending  = [dict(r) for r in c.execute("SELECT description FROM tasks WHERE task_type='daily' AND status='pending' AND date(created_at)<?", (today,)).fetchall()]
    completed= [dict(r) for r in c.execute("SELECT description FROM tasks WHERE task_type='daily' AND status='done' AND date(created_at)=?",   (today,)).fetchall()]
    missed, recent_done = recent_task_context(c, 'daily')
    c.close()
    quests = generate_daily(u, pending, completed, intent, missed, recent_done)
    if _preview_flag():
        out = []
        for i, q in enumerate(quests):
            stat, xp, tmr, en = _shape_daily(q)
            out.append({"tmp_id": -(i+1), "description": q.get("description",""), "xp_value": xp, "stat": stat, "energy_cost": en, "timer_minutes": tmr, "task_type":"daily", "status":"pending"})
        return jsonify(out)
    c = get_db(); created = []
    for q in quests:
        stat, xp, tmr, en = _shape_daily(q)
        cur  = c.execute("INSERT INTO tasks (description,xp_value,stat,energy_cost,timer_minutes,task_type) VALUES (?,?,?,?,?,?)",(q["description"],xp,stat,en,tmr,"daily"))
        created.append({"id":cur.lastrowid,"description":q["description"],"xp_value":xp,"stat":stat,"energy_cost":en,"timer_minutes":tmr,"task_type":"daily","status":"pending"})
    c.commit(); c.close()
    broadcast()
    return jsonify(created)

@app.route("/api/tasks/generate-tomorrow", methods=["POST"])
def api_gen_tomorrow():
    d = request.get_json(silent=True) or {}
    intent = d.get("intent", "").strip()
    u = get_user(); c = get_db(); today = date.today().isoformat()
    pending  = [dict(r) for r in c.execute("SELECT description FROM tasks WHERE task_type='daily' AND status='pending' AND date(created_at)<=?", (today,)).fetchall()]
    completed= [dict(r) for r in c.execute("SELECT description FROM tasks WHERE task_type='daily' AND status='done' AND date(created_at)=?",   (today,)).fetchall()]
    missed, recent_done = recent_task_context(c, 'daily')
    c.close()
    quests = generate_daily(u, pending, completed, intent, missed, recent_done)
    if _preview_flag():
        out = []
        for i, q in enumerate(quests):
            stat, xp, tmr, en = _shape_daily(q)
            out.append({"tmp_id": -(i+1), "description": q.get("description",""), "xp_value": xp, "stat": stat, "energy_cost": en, "timer_minutes": tmr, "task_type":"tomorrow", "status":"pending"})
        return jsonify(out)
    c = get_db(); created = []
    for q in quests:
        stat, xp, tmr, en = _shape_daily(q)
        cur  = c.execute("INSERT INTO tasks (description,xp_value,stat,energy_cost,timer_minutes,task_type,created_at) VALUES (?,?,?,?,?,?,datetime('now','+1 day','localtime'))",(q["description"],xp,stat,en,tmr,"daily"))
        created.append({"id":cur.lastrowid,"description":q["description"],"xp_value":xp,"stat":stat,"energy_cost":en,"timer_minutes":tmr,"task_type":"daily","status":"pending"})
    c.commit(); c.close()
    broadcast()
    return jsonify(created)

@app.route("/api/tasks/generate-weekly", methods=["POST"])
def api_gen_weekly():
    d = request.get_json(silent=True) or {}
    intent = d.get("intent", "").strip()
    u = get_user(); goals = generate_weekly(u, intent)
    if _preview_flag():
        out = []
        for i, g in enumerate(goals):
            stat = g.get("stat","INT") if g.get("stat") in ("INT","DEX","CHA","VIT") else "INT"
            xp = min(1500, max(200, g.get("xp",500))); en = calc_energy(stat, xp)
            out.append({"tmp_id": -(i+1), "description": g.get("description",""), "xp_value": xp, "stat": stat, "energy_cost": en, "timer_minutes": 60, "task_type":"weekly", "status":"pending"})
        return jsonify(out)
    c = get_db(); created = []
    for g in goals:
        stat = g.get("stat","INT") if g.get("stat") in ("INT","DEX","CHA","VIT") else "INT"
        xp   = min(1500,max(200,g.get("xp",500)))
        en   = calc_energy(stat,xp)
        cur  = c.execute("INSERT INTO tasks (description,xp_value,stat,energy_cost,timer_minutes,task_type) VALUES (?,?,?,?,?,?)",(g["description"],xp,stat,en,60,"weekly"))
        created.append({"id":cur.lastrowid,"description":g["description"],"xp_value":xp,"stat":stat,"energy_cost":en,"timer_minutes":60,"task_type":"weekly","status":"pending"})
    c.commit(); c.close()
    broadcast()
    return jsonify(created)

@app.route("/api/tasks/generate-monthly", methods=["POST"])
def api_gen_monthly():
    d = request.get_json(silent=True) or {}
    intent = d.get("intent", "").strip()
    u = get_user(); milestones = generate_monthly(u, intent)
    if _preview_flag():
        out = []
        for i, m in enumerate(milestones):
            stat = m.get("stat","INT") if m.get("stat") in ("INT","DEX","CHA","VIT") else "INT"
            xp = min(3000, max(500, m.get("xp",1500))); en = calc_energy(stat, xp)
            out.append({"tmp_id": -(i+1), "description": m.get("description",""), "xp_value": xp, "stat": stat, "energy_cost": en, "timer_minutes": 120, "task_type":"monthly", "status":"pending"})
        return jsonify(out)
    c = get_db(); created = []
    for m in milestones:
        stat = m.get("stat","INT") if m.get("stat") in ("INT","DEX","CHA","VIT") else "INT"
        xp   = min(3000,max(500,m.get("xp",1500)))
        en   = calc_energy(stat,xp)
        cur  = c.execute("INSERT INTO tasks (description,xp_value,stat,energy_cost,timer_minutes,task_type) VALUES (?,?,?,?,?,?)",(m["description"],xp,stat,en,120,"monthly"))
        created.append({"id":cur.lastrowid,"description":m["description"],"xp_value":xp,"stat":stat,"energy_cost":en,"timer_minutes":120,"task_type":"monthly","status":"pending"})
    c.commit(); c.close()
    broadcast()
    return jsonify(created)

@app.route("/api/tasks/add", methods=["POST"])
def api_task_add():
    d = request.json; desc = d.get("description","").strip()
    typ = d.get("task_type","daily")
    if not desc: return jsonify({"error":"Empty"}),400
    if typ not in ("daily","tomorrow","weekly","monthly"): typ = "daily"
    stat,xp,tmr = categorize(desc); en = calc_energy(stat,xp)
    c = get_db()
    if typ == "tomorrow":
        cur = c.execute("INSERT INTO tasks (description,xp_value,stat,energy_cost,timer_minutes,task_type,created_at) VALUES (?,?,?,?,?,?,datetime('now','+1 day','localtime'))",(desc,xp,stat,en,tmr,"daily"))
    else:
        cur = c.execute("INSERT INTO tasks (description,xp_value,stat,energy_cost,timer_minutes,task_type) VALUES (?,?,?,?,?,?)",(desc,xp,stat,en,tmr,typ))
    tid = cur.lastrowid; c.commit(); c.close()
    broadcast()
    return jsonify({"id":tid,"description":desc,"xp_value":xp,"stat":stat,"energy_cost":en,"timer_minutes":tmr,"task_type":typ,"status":"pending"})

@app.route("/api/tasks/add-batch", methods=["POST"])
def api_task_add_batch():
    """Accept pre-shaped quests (from a preview) and persist the selected ones."""
    d = request.get_json(silent=True) or {}
    quests = d.get("quests") or []
    if not isinstance(quests, list) or not quests:
        return jsonify({"error": "No quests"}), 400
    c = get_db(); created = []
    for q in quests:
        desc = (q.get("description") or "").strip()
        if not desc: continue
        typ = q.get("task_type","daily")
        if typ not in ("daily","tomorrow","weekly","monthly"): typ = "daily"
        stat = q.get("stat","INT") if q.get("stat") in ("INT","DEX","CHA","VIT") else "INT"
        # Clamp XP by bucket
        xp_raw = q.get("xp_value", q.get("xp", 100))
        if typ == "monthly":   xp = min(3000, max(500, xp_raw))
        elif typ == "weekly":  xp = min(1500, max(200, xp_raw))
        else:                  xp = min(500,  max(50,  xp_raw))
        tmr = min(120, max(10, q.get("timer_minutes", 30 if typ in ("daily","tomorrow") else 60)))
        en  = calc_energy(stat, xp)
        if typ == "tomorrow":
            cur = c.execute("INSERT INTO tasks (description,xp_value,stat,energy_cost,timer_minutes,task_type,created_at) VALUES (?,?,?,?,?,?,datetime('now','+1 day','localtime'))",(desc,xp,stat,en,tmr,"daily"))
        else:
            cur = c.execute("INSERT INTO tasks (description,xp_value,stat,energy_cost,timer_minutes,task_type) VALUES (?,?,?,?,?,?)",(desc,xp,stat,en,tmr,typ))
        created.append({"id":cur.lastrowid,"description":desc,"xp_value":xp,"stat":stat,"energy_cost":en,"timer_minutes":tmr,"task_type":typ,"status":"pending"})
    c.commit(); c.close()
    broadcast()
    return jsonify(created)

@app.route("/api/tasks/<int:tid>/complete", methods=["POST"])
def api_complete(tid):
    c = get_db()
    t = c.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone()
    if not t: c.close(); return jsonify({"error":"Not found"}),404
    t = dict(t)
    if t["status"] == "done": c.close(); return jsonify({"error":"Already done"}),400
    typ = t.get("task_type","daily")
    if typ == "weekly" and date.today().weekday() < 5:
        c.close(); return jsonify({"error":"Weekly goals unlock on Saturday & Sunday"}),400
    if typ == "monthly":
        nm = (date.today().replace(day=28)+timedelta(days=4)).replace(day=1)
        if (nm-date.today()).days > 2:
            c.close(); return jsonify({"error":"Monthly goals unlock in the last 2 days of the month"}),400

    ub = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone())
    c.execute("UPDATE tasks SET status='done',completed_at=datetime('now','localtime') WHERE id=?",(tid,))

    # Decay pet, apply XP multipliers from pet + boosts
    apply_pet_decay(c)
    base_xp = t["xp_value"]
    final_xp, xp_breakdown = apply_xp_multipliers(c, base_xp)

    sc = t["stat"].lower()+"_xp"
    c.execute(f"UPDATE user SET total_xp=total_xp+?,{sc}={sc}+? WHERE id=1",(final_xp, final_xp))
    en = t.get("energy_cost",10)
    c.execute("UPDATE user SET hp=MAX(0,hp-?) WHERE id=1",(en,))
    streak = update_streak(c)

    # Gem trickle per quest (1-5 gems based on XP)
    quest_gems = max(1, min(5, base_xp // 100))
    grant_gems(c, quest_gems)

    completed_challenges = update_challenge_progress(c, t["stat"], final_xp)
    loot_drop = roll_loot(c, final_xp)

    # Update today's bounty progress
    completed_bounties, bounty_gems = update_bounty_progress(
        c, task_stat=t["stat"], task_xp=final_xp,
        loot_drop=bool(loot_drop), challenge_count=len(completed_challenges)
    )

    # Award pet XP (pet gains ~10% of the quest's final XP)
    pet_xp_gain = max(1, final_xp // 10)
    pet_level_up = award_pet_xp(c, pet_xp_gain)
    # Auto-heal pet on quest completion: replenish hunger + happiness so it stays alive
    # while the user is active. Gains scale with quest XP.
    p_cur = c.execute("SELECT hatched, hunger, happiness FROM pet WHERE id=1").fetchone()
    if p_cur and p_cur["hatched"]:
        heal = max(8, min(25, final_xp // 20))
        joy  = max(5, min(20, final_xp // 25))
        new_hunger = min(100, (p_cur["hunger"] or 0) + heal)
        new_happy  = min(100, (p_cur["happiness"] or 0) + joy)
        c.execute("UPDATE pet SET hunger=?, happiness=?, last_fed=datetime('now','localtime') WHERE id=1",
                  (new_hunger, new_happy))

    leveled, lv, new_unlocks, new_title = check_level_up(c)
    level_up_gems = 0
    if leveled:
        level_up_gems = (lv - ub["level"]) * 25
        grant_gems(c, level_up_gems)

    new_ach = check_achievements(c)
    ach_gems = len(new_ach) * 10
    if ach_gems: grant_gems(c, ach_gems)

    challenge_gems = sum(ch.get("reward_gems", 15) for ch in completed_challenges)
    total_gems_earned = quest_gems + bounty_gems + level_up_gems + ach_gems + challenge_gems

    quests_done = c.execute("SELECT COUNT(*) FROM tasks WHERE status='done'").fetchone()[0]
    c.commit()
    ua = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone())
    pet_now = enrich_pet(get_pet(c))
    c.close()
    # Sync leaderboard
    try: sync_leaderboard(current_profile(), ua, quests_done)
    except Exception: pass
    resp = jsonify({"ok":True,"xp_gained":final_xp,"base_xp":base_xp,"xp_breakdown":xp_breakdown,
                    "stat":t["stat"],"energy_cost":en,
                    "leveled_up":leveled,"new_level":lv,"streak":streak,
                    "new_achievements":new_ach,"stat_level_ups":check_stat_ups(ub,ua),
                    "completed_challenges":completed_challenges,
                    "completed_bounties":completed_bounties,
                    "gems_earned":total_gems_earned,
                    "gems_breakdown":{"quest":quest_gems,"bounties":bounty_gems,
                                      "level_up":level_up_gems,"achievements":ach_gems,
                                      "challenges":challenge_gems},
                    "pet_level_up":pet_level_up,"pet":pet_now,
                    "new_unlocks":new_unlocks,"new_title":new_title,
                    "loot_drop":loot_drop,
                    "user":enrich(ua)})
    broadcast()
    return resp

@app.route("/api/tasks/<int:tid>", methods=["DELETE"])
def api_task_del(tid):
    c = get_db(); c.execute("DELETE FROM tasks WHERE id=?",(tid,)); c.commit(); c.close()
    broadcast()
    return jsonify({"ok":True})

@app.route("/api/leaderboard")
def api_leaderboard():
    c = sqlite3.connect(LEADERBOARD_DB)
    c.row_factory = sqlite3.Row
    _snapshot_leaderboard_if_needed(c)
    rows = c.execute("SELECT * FROM leaderboard ORDER BY total_xp DESC LIMIT 50").fetchall()
    c.close()
    my_profile = current_profile() or "default"
    out = []
    for i, r in enumerate(rows):
        d = dict(r)
        d["rank"] = i + 1
        d["is_me"] = (d["profile"] == my_profile)
        out.append(d)
    return jsonify({"leaderboard": out, "my_profile": my_profile})

@app.route("/api/leaderboard/history")
def api_leaderboard_history():
    """List available snapshot dates, or fetch a specific snapshot with ?date=YYYY-MM-DD."""
    c = sqlite3.connect(LEADERBOARD_DB)
    c.row_factory = sqlite3.Row
    _snapshot_leaderboard_if_needed(c)
    want = request.args.get("date","").strip()
    if want:
        row = c.execute("SELECT data, created_at FROM leaderboard_history WHERE snap_date=?",(want,)).fetchone()
        c.close()
        if not row:
            return jsonify({"error":"No snapshot for that date","dates":[]}), 404
        data = json.loads(row["data"])
        my_profile = current_profile() or "default"
        for d in data:
            d["is_me"] = (d.get("profile") == my_profile)
        return jsonify({"date": want, "created_at": row["created_at"],
                        "leaderboard": data, "my_profile": my_profile})
    dates = [r["snap_date"] for r in c.execute(
        "SELECT snap_date FROM leaderboard_history ORDER BY snap_date DESC LIMIT 60").fetchall()]
    c.close()
    return jsonify({"dates": dates})

@app.route("/api/challenges")
def api_challenges():
    c = get_db()
    ensure_daily_challenges(c)
    today = date.today().isoformat()
    rows = c.execute("SELECT * FROM daily_challenges WHERE date=? ORDER BY id",(today,)).fetchall()
    c.close()
    out = []
    for r in rows:
        r = dict(r)
        out.append({
            "id": r["id"], "ctype": r["ctype"], "target_stat": r["target_stat"],
            "target_value": r["target_value"], "progress": r["progress"],
            "reward_xp": r["reward_xp"], "description": r["description"],
            "icon": r["icon"], "completed": bool(r["completed_at"]),
        })
    return jsonify({"challenges": out})

@app.route("/api/achievements")
def api_achievements():
    c = get_db()
    a = [dict(r) for r in c.execute("SELECT * FROM achievements ORDER BY earned_at DESC").fetchall()]
    c.close(); return jsonify({"achievements":a})

@app.route("/api/login-reward", methods=["POST"])
def api_login_reward():
    c = get_db()
    reward = claim_login_reward(c)
    c.close()
    if not reward: return jsonify({"already_claimed": True})
    broadcast()
    return jsonify(reward)

@app.route("/api/login-info")
def api_login_info():
    c = get_db()
    info = get_login_streak_info(c)
    c.close()
    return jsonify(info)

@app.route("/api/spin", methods=["POST"])
def api_spin():
    c = get_db()
    result = do_daily_spin(c)
    if not result:
        c.close()
        return jsonify({"already_spun": True})
    c.commit(); c.close()
    broadcast()
    return jsonify(result)

@app.route("/api/spin-available")
def api_spin_available():
    c = get_db()
    today = date.today().isoformat()
    available = c.execute("SELECT id FROM daily_spins WHERE date=?",(today,)).fetchone() is None
    c.close()
    return jsonify({"available": available})

@app.route("/api/milestones")
def api_milestones():
    c = get_db()
    ms = get_milestones(c)
    c.close()
    return jsonify({"milestones": ms})

@app.route("/api/today-stats")
def api_today_stats():
    c = get_db()
    today = date.today().isoformat()
    quests_done = c.execute("SELECT COUNT(*) FROM tasks WHERE status='done' AND date(completed_at)=?",(today,)).fetchone()[0]
    xp_earned = c.execute("SELECT COALESCE(SUM(xp_value),0) FROM tasks WHERE status='done' AND date(completed_at)=?",(today,)).fetchone()[0]
    loot_found = c.execute("SELECT COUNT(*) FROM loot WHERE date(earned_at)=?",(today,)).fetchone()[0]
    c.close()
    return jsonify({"quests_done": quests_done, "xp_earned": xp_earned, "loot_found": loot_found})

@app.route("/api/loot")
def api_loot():
    c = get_db()
    items = [dict(r) for r in c.execute("SELECT * FROM loot ORDER BY earned_at DESC LIMIT 50").fetchall()]
    c.close()
    return jsonify({"loot": items})

# ── Shop / Inventory / Pet / Bounties / Gifts / Weekly Report ─────────────
@app.route("/api/shop")
def api_shop():
    c = get_db()
    gems = get_gems(c)
    boosts = get_active_boosts(c)
    equipped = c.execute("SELECT equipped_frame FROM user WHERE id=1").fetchone()
    equipped_frame = equipped["equipped_frame"] if equipped else ""
    c.close()
    items = []
    for key in get_shop_rotation():
        meta = SHOP_ITEMS.get(key)
        if not meta: continue
        items.append({"key": key, **meta})
    return jsonify({"items": items, "gems": gems, "active_boosts": boosts,
                    "equipped_frame": equipped_frame})

@app.route("/api/shop/buy", methods=["POST"])
def api_shop_buy():
    d = request.get_json(silent=True) or {}
    key = d.get("item_key") or ""
    meta = SHOP_ITEMS.get(key)
    if not meta: return jsonify({"error":"Unknown item"}), 400
    if key not in get_shop_rotation():
        return jsonify({"error":"Not in today's rotation"}), 400
    c = get_db()
    if not spend_gems(c, meta["price"]):
        c.close(); return jsonify({"error":"Not enough gems"}), 400
    add_to_inventory(c, key, 1)
    c.commit()
    gems = get_gems(c)
    c.close()
    broadcast()
    return jsonify({"ok": True, "gems": gems, "item": {"key": key, **meta}})

@app.route("/api/inventory")
def api_inventory():
    c = get_db()
    inv = get_inventory(c)
    boosts = get_active_boosts(c)
    c.close()
    return jsonify({"inventory": inv, "active_boosts": boosts})

@app.route("/api/inventory/use", methods=["POST"])
def api_inventory_use():
    d = request.get_json(silent=True) or {}
    key = d.get("item_key") or ""
    meta = SHOP_ITEMS.get(key)
    if not meta:
        # Loot items are trophies — their effect was applied on drop. Check the loot table.
        c = get_db()
        loot_row = c.execute("SELECT id, name, rarity FROM loot WHERE name=? ORDER BY earned_at DESC LIMIT 1", (key,)).fetchone()
        c.close()
        if loot_row:
            return jsonify({"error": f"{loot_row['name']} is a trophy — its bonus was already granted when you found it. Keep it as proof of your victory."}), 400
        return jsonify({"error":"Unknown item"}), 400
    c = get_db()
    existing = c.execute("SELECT quantity FROM inventory WHERE item_key=?", (key,)).fetchone()
    if not existing or existing["quantity"] <= 0:
        c.close(); return jsonify({"error":"You don't own this"}), 400

    result = {"item_key": key, "name": meta["name"], "icon": meta["icon"]}
    cat = meta["category"]
    try:
        if cat == "powerup":
            eff = dict(meta.get("effect", {}))
            et = eff.get("type")
            if et == "hp_full":
                c.execute("UPDATE user SET hp=max_hp WHERE id=1")
                result["hp_restored"] = True
            elif et in ("xp_mult", "loot_mult"):
                add_boost(c, key, eff); result["boost_activated"] = True
            elif et == "xp_charges":
                add_boost(c, key, eff); result["boost_activated"] = True
            elif et == "streak_shield":
                add_boost(c, key, {"type":"streak_shield"}); result["shield_active"] = True
            elif et == "quest_reroll":
                add_boost(c, key, {"type":"quest_reroll"}); result["reroll_ready"] = True
            else:
                c.close(); return jsonify({"error":"Can't use this"}), 400
        elif cat == "pet":
            pet = get_pet(c)
            if not pet or not pet["hatched"]:
                c.close(); return jsonify({"error":"You need a hatched pet first"}), 400
            if key == "pet_food":
                nh = min(100, pet["hunger"] + 30)
                c.execute("UPDATE pet SET hunger=?, last_fed=? WHERE id=1", (nh, datetime.now().isoformat()))
                result["pet_fed"] = True; result["hunger"] = nh
            elif key == "pet_treat":
                nh = min(100, pet["hunger"] + 40)
                hp = min(100, pet["happiness"] + 40)
                c.execute("UPDATE pet SET hunger=?, happiness=?, last_fed=? WHERE id=1",
                          (nh, hp, datetime.now().isoformat()))
                result["pet_treated"] = True; result["hunger"] = nh; result["happiness"] = hp
            elif key == "evolution_stone":
                lvl = award_pet_xp(c, 500)
                result["pet_xp_granted"] = 500; result["pet_level_up"] = lvl
            elif key == "mystery_egg":
                c.execute("UPDATE pet SET species='', name='', pet_level=0, pet_xp=0, hatched=0, happiness=80, hunger=50, last_fed='', last_decay='' WHERE id=1")
                result["new_egg"] = True
            else:
                c.close(); return jsonify({"error":"Unknown pet item"}), 400
        elif cat == "mystery":
            reward = open_mystery_box(c, key)
            result["mystery_reward"] = reward
        elif cat == "cosmetic":
            c.execute("UPDATE user SET equipped_frame=? WHERE id=1", (key,))
            result["equipped_frame"] = key
        remove_from_inventory(c, key, 1)
        c.commit()
    except Exception as e:
        c.close(); return jsonify({"error": str(e)}), 500

    u = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone())
    pet_now = enrich_pet(get_pet(c))
    gems = u["gems"]
    c.close()
    broadcast()
    return jsonify({"ok":True, "result":result, "gems":gems, "user":enrich(u), "pet":pet_now})

@app.route("/api/pet")
def api_pet():
    c = get_db()
    apply_pet_decay(c)
    c.commit()
    pet = enrich_pet(get_pet(c))
    c.close()
    return jsonify({"pet": pet, "species": PET_SPECIES, "stages": PET_STAGES})

@app.route("/api/pet/hatch", methods=["POST"])
def api_pet_hatch():
    d = request.get_json(silent=True) or {}
    species = d.get("species", "")
    name = (d.get("name", "") or "").strip()[:20]
    if not any(s["key"] == species for s in PET_SPECIES):
        return jsonify({"error":"Invalid species"}), 400
    c = get_db()
    pet = get_pet(c)
    if pet and pet["hatched"]:
        c.close(); return jsonify({"error":"You already have a pet"}), 400
    c.execute("UPDATE pet SET species=?, name=?, pet_level=1, pet_xp=0, hatched=1, happiness=90, hunger=80, last_decay=? WHERE id=1",
              (species, name or "Buddy", datetime.now().isoformat()))
    c.commit()
    pet = enrich_pet(get_pet(c))
    c.close()
    broadcast()
    return jsonify({"ok":True, "pet":pet})

@app.route("/api/pet/name", methods=["POST"])
def api_pet_name():
    d = request.get_json(silent=True) or {}
    name = (d.get("name","") or "").strip()[:20]
    if not name: return jsonify({"error":"Name required"}), 400
    c = get_db()
    c.execute("UPDATE pet SET name=? WHERE id=1", (name,))
    c.commit(); c.close()
    broadcast()
    return jsonify({"ok":True, "name":name})

@app.route("/api/bounties")
def api_bounties():
    c = get_db()
    ensure_daily_bounties(c)
    today = date.today().isoformat()
    rows = c.execute("SELECT * FROM bounties WHERE date=? ORDER BY id",(today,)).fetchall()
    c.close()
    out = []
    for r in rows:
        r = dict(r)
        out.append({
            "id": r["id"], "btype": r["btype"], "target_stat": r["target_stat"],
            "target_value": r["target_value"], "progress": r["progress"],
            "reward_gems": r["reward_gems"], "description": r["description"],
            "icon": r["icon"], "completed": bool(r["completed_at"]),
        })
    return jsonify({"bounties": out})

@app.route("/api/gifts")
def api_gifts():
    c = get_db()
    rows = c.execute("SELECT * FROM gifts_received WHERE claimed_at IS NULL ORDER BY received_at DESC").fetchall()
    c.close()
    out = []
    for r in rows:
        r = dict(r)
        meta = SHOP_ITEMS.get(r["item_key"], {})
        out.append({**r, "name": meta.get("name", r["item_key"]),
                    "icon": meta.get("icon", "?"), "desc": meta.get("desc", "")})
    return jsonify({"gifts": out})

@app.route("/api/gifts/claim", methods=["POST"])
def api_gifts_claim():
    d = request.get_json(silent=True) or {}
    gid = d.get("gift_id")
    c = get_db()
    row = c.execute("SELECT * FROM gifts_received WHERE id=? AND claimed_at IS NULL",(gid,)).fetchone()
    if not row:
        c.close(); return jsonify({"error":"Not found or already claimed"}), 404
    row = dict(row)
    add_to_inventory(c, row["item_key"], 1)
    c.execute("UPDATE gifts_received SET claimed_at=datetime('now','localtime') WHERE id=?", (gid,))
    c.commit(); c.close()
    broadcast()
    return jsonify({"ok":True, "item_key": row["item_key"]})

@app.route("/api/gift/send", methods=["POST"])
def api_gift_send():
    d = request.get_json(silent=True) or {}
    to_profile = (d.get("to_profile") or "").strip().lower()
    to_profile = _PROFILE_RE.sub('', to_profile)[:32]
    item_key = d.get("item_key") or ""
    if not to_profile: return jsonify({"error":"No recipient"}), 400
    if item_key not in SHOP_ITEMS: return jsonify({"error":"Invalid item"}), 400
    sender_profile = current_profile() or "default"
    if to_profile == sender_profile:
        return jsonify({"error":"Can't gift yourself"}), 400

    # Daily send limit: 3
    c = get_db()
    today = date.today().isoformat()
    sent_today = c.execute("SELECT COUNT(*) FROM gifts_sent_log WHERE date(sent_at)=?", (today,)).fetchone()[0]
    if sent_today >= 3:
        c.close(); return jsonify({"error":"Daily gift limit reached (3/day)"}), 400

    if not remove_from_inventory(c, item_key, 1):
        c.close(); return jsonify({"error":"You don't own this"}), 400

    u = dict(c.execute("SELECT display_name FROM user WHERE id=1").fetchone())
    from_display = u.get("display_name") or sender_profile

    c.execute("INSERT INTO gifts_sent_log (to_profile, item_key) VALUES (?,?)", (to_profile, item_key))
    c.commit(); c.close()

    # Write into recipient's DB (ensure it's initialized first)
    recipient_db = db_path_for(to_profile if to_profile != "default" else "")
    if not os.path.exists(recipient_db):
        return jsonify({"error":"Recipient profile not found"}), 404
    rc = sqlite3.connect(recipient_db)
    rc.execute("PRAGMA journal_mode=WAL")
    rc.execute("""CREATE TABLE IF NOT EXISTS gifts_received (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_profile TEXT NOT NULL, from_display TEXT DEFAULT '',
        item_key TEXT NOT NULL,
        received_at TEXT DEFAULT (datetime('now','localtime')),
        claimed_at TEXT)""")
    rc.execute("INSERT INTO gifts_received (from_profile, from_display, item_key) VALUES (?,?,?)",
               (sender_profile, from_display, item_key))
    rc.commit(); rc.close()
    broadcast()
    return jsonify({"ok":True, "sent_today": sent_today + 1})

# ── AI Weekly Report ─────────────────────────────────────────────────────
WEEKLY_REPORT_SYS = """You are the Game Master for a productivity RPG called LEVEL UP.
Write a warm, personalized weekly retrospective for the player.
RULES:
- Open with a one-line celebratory hook using their display name.
- Call out their single BIGGEST win this week — most XP-heavy stat, most impressive quest, or biggest streak.
- Point out ONE specific weakness and suggest ONE concrete action for next week.
- Acknowledge their stated motivation and tie their effort back to WHY it matters to THEM.
- End with one line of hype.
Use markdown headings (##) and short bullet points. Keep it under 220 words. No generic platitudes — reference real tasks when possible."""

def gather_weekly_stats(c, week_start):
    u = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone())
    rows = c.execute(
        "SELECT * FROM tasks WHERE date(completed_at)>=? AND status='done' ORDER BY completed_at",
        (week_start,)).fetchall()
    done_tasks = [dict(r) for r in rows]
    failed = c.execute("SELECT COUNT(*) FROM tasks WHERE date(created_at)>=? AND status='failed'",(week_start,)).fetchone()[0]
    stat_xp = {"INT":0,"DEX":0,"CHA":0,"VIT":0}
    for t in done_tasks:
        s = t["stat"] if t["stat"] in stat_xp else "INT"
        stat_xp[s] += t["xp_value"]
    total_xp = sum(stat_xp.values())
    ch_done = c.execute("SELECT COUNT(*) FROM daily_challenges WHERE date>=? AND completed_at IS NOT NULL",(week_start,)).fetchone()[0]
    bounties_done = c.execute("SELECT COUNT(*) FROM bounties WHERE date>=? AND completed_at IS NOT NULL",(week_start,)).fetchone()[0]
    loot_found = c.execute("SELECT COUNT(*) FROM loot WHERE date(earned_at)>=?",(week_start,)).fetchone()[0]
    return {"user":u, "week_start":week_start, "done_tasks":done_tasks, "failed":failed,
            "stat_xp":stat_xp, "total_xp":total_xp, "ch_done":ch_done,
            "bounties_done":bounties_done, "loot_found":loot_found}

def generate_weekly_report_ai(stats):
    u = stats["user"]
    p = PERSONAS.get(u.get("persona","operator"), PERSONAS["operator"])
    tasks_sample = [t["description"] for t in stats["done_tasks"][:15]]
    prompt = f"""Player: {u.get('display_name') or 'Hero'}
Persona: {p['name']} ({p['desc']})
Profession: {u.get('profession','N/A')}
Motivation: {u.get('motivation','self-improvement')}
Monthly vision: {u.get('monthly_goal','N/A')}
Weekly focus: {u.get('weekly_goal','N/A')}
Level: {u.get('level',1)}  |  Streak: {u.get('streak',0)} days
Week starting: {stats['week_start']}

THIS WEEK'S STATS:
- Total XP earned: {stats['total_xp']:,}
- Per-stat XP — INT: {stats['stat_xp']['INT']}, DEX: {stats['stat_xp']['DEX']}, CHA: {stats['stat_xp']['CHA']}, VIT: {stats['stat_xp']['VIT']}
- Quests completed: {len(stats['done_tasks'])}
- Quests failed/missed: {stats['failed']}
- Daily challenges done: {stats['ch_done']}
- Bounties done: {stats['bounties_done']}
- Loot items found: {stats['loot_found']}

Sample completed quests: {json.dumps(tasks_sample)}

Write the weekly retrospective now. Markdown, under 220 words. Be specific — quote real quests where possible."""
    try:
        r = ollama.chat(model='qwen3.5:9b',
                        messages=[{"role":"system","content":WEEKLY_REPORT_SYS},
                                  {"role":"user","content":prompt}],
                        think=False)
        return r["message"]["content"]
    except Exception as e:
        print(f"[WEEKLY REPORT] {e}")
        top_stat = max(stats["stat_xp"].items(), key=lambda x: x[1])
        return f"""## Week of {stats['week_start']}

**{u.get('display_name') or 'Hero'}**, you banked **{stats['total_xp']:,} XP** across **{len(stats['done_tasks'])} quests** this week.

### Biggest Win
Your **{top_stat[0]}** stat surged by {top_stat[1]} XP — that's where your energy flowed.

### Stats
- INT: {stats['stat_xp']['INT']} · DEX: {stats['stat_xp']['DEX']} · CHA: {stats['stat_xp']['CHA']} · VIT: {stats['stat_xp']['VIT']}
- Challenges: {stats['ch_done']} · Bounties: {stats['bounties_done']} · Loot: {stats['loot_found']}

Keep pushing — next week can be even bigger."""

@app.route("/api/weekly-report/history")
def api_weekly_report_history():
    c = get_db()
    rows = c.execute("SELECT week_start, generated_at FROM weekly_reports ORDER BY week_start DESC").fetchall()
    c.close()
    return jsonify({"weeks": [{"week_start": r["week_start"], "generated_at": r["generated_at"]} for r in rows]})

@app.route("/api/weekly-report")
def api_weekly_report():
    today = date.today()
    weekday = today.weekday()  # Mon=0 .. Sun=6
    is_weekend = weekday >= 5  # Sat/Sun
    force = request.args.get("regen") in ("1","true","yes")
    want_week = (request.args.get("week") or "").strip()
    c = get_db()
    # Explicit historical week request — never regenerates, just fetches cached
    if want_week:
        cached = c.execute("SELECT content, generated_at FROM weekly_reports WHERE week_start=?", (want_week,)).fetchone()
        c.close()
        if not cached:
            return jsonify({"week_start": want_week, "available": False,
                            "message": "No report stored for that week."}), 404
        return jsonify({"week_start": want_week, "content": cached["content"],
                        "generated_at": cached["generated_at"], "cached": True, "historical": True})
    week_start = (today - timedelta(days=weekday)).isoformat()
    cached = c.execute("SELECT content FROM weekly_reports WHERE week_start=?", (week_start,)).fetchone()
    if cached and not force:
        content = cached["content"]
        c.close()
        return jsonify({"week_start": week_start, "content": content, "cached": True,
                        "is_weekend": is_weekend})
    # Gate fresh generation to the weekend only
    if not is_weekend:
        c.close()
        days_until = (5 - weekday) % 7 or 7
        return jsonify({"week_start": week_start, "available": False,
                        "is_weekend": False,
                        "available_on": "Saturday",
                        "days_until": days_until,
                        "message": ("Weekly reports are generated every Saturday and Sunday so your week "
                                    "has enough quests to analyze. Come back in "
                                    f"{days_until} day{'s' if days_until!=1 else ''} "
                                    "for your personalized retrospective.")})
    stats = gather_weekly_stats(c, week_start)
    c.close()
    report = generate_weekly_report_ai(stats)
    c = get_db()
    c.execute("""INSERT INTO weekly_reports (week_start, content) VALUES (?,?)
                 ON CONFLICT(week_start) DO UPDATE SET
                 content=excluded.content, generated_at=datetime('now','localtime')""",
              (week_start, report))
    c.commit(); c.close()
    return jsonify({"week_start": week_start, "content": report, "cached": False,
                    "is_weekend": True,
                    "stats": {"total_xp": stats["total_xp"], "done": len(stats["done_tasks"]),
                              "failed": stats["failed"], "stat_xp": stats["stat_xp"]}})

@app.route("/api/reset", methods=["POST"])
def api_reset():
    c = get_db()
    c.executescript("""DELETE FROM tasks; DELETE FROM achievements; DELETE FROM daily_challenges;
        DELETE FROM login_rewards; DELETE FROM loot; DELETE FROM daily_spins;
        DELETE FROM inventory; DELETE FROM bounties;
        DELETE FROM gifts_received; DELETE FROM gifts_sent_log;
        DELETE FROM weekly_reports;
        UPDATE pet SET species='',name='',pet_level=0,pet_xp=0,happiness=80,hunger=50,
            hatched=0,last_fed='',last_decay='';
        UPDATE user SET persona='',display_name='',bio='',motivation='',profession='',
        profile_photo='',level=1,total_xp=0,int_xp=0,dex_xp=0,cha_xp=0,vit_xp=0,
        hp=100,max_hp=100,streak=0,last_active='',monthly_goal='',weekly_goal='',onboarded=0,
        gems=0,active_boosts='{}',equipped_frame='';""")
    c.commit(); c.close()
    for f in os.listdir(UPLOAD_DIR): os.remove(os.path.join(UPLOAD_DIR,f))
    broadcast("reset")
    return jsonify({"ok":True})

@app.route("/api/events")
def api_events():
    """SSE endpoint — each connected client subscribes here, scoped to profile."""
    profile = current_profile()
    q = queue.Queue(maxsize=50)
    item = (profile, q)
    with sse_lock:
        sse_clients.append(item)
    def stream():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    msg = q.get(timeout=25)
                    yield msg
                except queue.Empty:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            with sse_lock:
                if item in sse_clients:
                    sse_clients.remove(item)
    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                             "Connection": "keep-alive"})

def open_dashboard(icon, item):
    webbrowser.open("http://localhost:5050")

def exit_app(icon, item):
    icon.stop()
    os._exit(0)

def create_image():
    # Elegant custom icon with purple upward arrow
    image = Image.new('RGB', (64, 64), color=(30, 27, 75))
    d = ImageDraw.Draw(image)
    d.polygon([(32, 12), (16, 32), (48, 32)], fill=(124, 58, 237))
    d.rectangle([(26, 32), (38, 52)], fill=(124, 58, 237))
    return image

def _startup_generate_summaries():
    """Run once on script start: ensure the last 3 days have AI summaries for every profile DB.
    Skips silently if Ollama is unreachable or no DBs exist yet."""
    try:
        import glob
        db_files = glob.glob(os.path.join(BASE_DIR, "levelup*.db"))
        for db_file in db_files:
            try:
                with sqlite3.connect(db_file) as conn:
                    conn.row_factory = sqlite3.Row
                    # Table may not exist yet on an older DB
                    conn.execute("""CREATE TABLE IF NOT EXISTS daily_summaries (
                        day TEXT PRIMARY KEY, summary TEXT NOT NULL,
                        generated_at TEXT DEFAULT (datetime('now','localtime')))""")
                    ensure_recent_summaries(conn, days=3)
                    print(f"[STARTUP] summaries ready for {os.path.basename(db_file)}")
            except Exception as e:
                print(f"[STARTUP] skipped {os.path.basename(db_file)}: {e}")
    except Exception as e:
        print(f"[STARTUP] summary generation skipped: {e}")

if __name__ == "__main__":
    print("[LEVEL UP] starting in system tray... http://localhost:5050")
    # Start flask silently in a background daemon thread
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5050, debug=False, use_reloader=False, threaded=True), daemon=True).start()
    # Generate any missing day-summaries for the last 3 days in a background thread
    # (runs once at startup; does nothing on days already summarized, so it acts as a "new day" trigger)
    threading.Thread(target=_startup_generate_summaries, daemon=True).start()
    
    # Auto-open browser on startup
    webbrowser.open("http://localhost:5050")
    
    # Boot the system tray item
    icon = pystray.Icon("LevelUp", create_image(), "Level Up RPG", menu=pystray.Menu(
        pystray.MenuItem('Open Dashboard', open_dashboard),
        pystray.MenuItem('Quit', exit_app)
    ))
    icon.run()
