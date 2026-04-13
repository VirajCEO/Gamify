import os, json, sqlite3, math, uuid, threading, time, queue, webbrowser
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

# ── SSE (Server-Sent Events) for real-time multi-device sync ─────────────────
sse_clients = []  # list of queue.Queue
sse_lock = threading.Lock()

def broadcast(event_type="sync"):
    """Push an event to all connected SSE clients."""
    data = f"event: {event_type}\ndata: {{\"ts\":{int(time.time())}}}\n\n"
    with sse_lock:
        dead = []
        for q in sse_clients:
            try:
                q.put_nowait(data)
            except queue.Full:
                dead.append(q)
        for q in dead:
            sse_clients.remove(q)

PERSONAS = {
    "visionary": {"name":"The Visionary","desc":"Strategy & Networking","weights":{"CHA":1.5,"INT":1.3,"DEX":0.8,"VIT":1.0},"icon":"\u2728"},
    "operator":  {"name":"The Operator", "desc":"Execution & Technical Depth","weights":{"DEX":1.5,"INT":1.3,"CHA":0.8,"VIT":1.0},"icon":"\u2699\ufe0f"},
    "scholar":   {"name":"The Scholar",  "desc":"Research & Learning","weights":{"INT":1.8,"DEX":1.0,"CHA":0.8,"VIT":1.0},"icon":"\ud83d\udcda"},
    "vitalist":  {"name":"The Vitalist", "desc":"Physical Performance & Recovery","weights":{"VIT":1.8,"DEX":1.0,"INT":0.8,"CHA":0.8},"icon":"\ud83d\udcaa"},
}

ENERGY_COSTS = {"INT": 12, "DEX": 10, "CHA": 6, "VIT": -15}

# ── Stat levelling ──────────────────────────────────────────────────────────
def stat_level_from_xp(xp):
    return min(99, int(math.sqrt(max(0, xp) / 50)) + 1)

def stat_xp_for_level(lv):  return 50 * ((lv - 1) ** 2)
def stat_xp_for_next(lv):   return 50 * (lv ** 2)

# ── Database ─────────────────────────────────────────────────────────────────
def get_db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c

def init_db():
    c = get_db()
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
    """)
    if c.execute("SELECT COUNT(*) FROM user").fetchone()[0] == 0:
        c.execute("INSERT INTO user (id) VALUES (1)")
    # migrations
    user_cols = {r[1] for r in c.execute("PRAGMA table_info(user)").fetchall()}
    task_cols = {r[1] for r in c.execute("PRAGMA table_info(tasks)").fetchall()}
    for col, td in [("display_name","TEXT DEFAULT ''"),("bio","TEXT DEFAULT ''"),
                    ("motivation","TEXT DEFAULT ''"),("profession","TEXT DEFAULT ''"),
                    ("profile_photo","TEXT DEFAULT ''")]:
        if col not in user_cols: c.execute(f"ALTER TABLE user ADD COLUMN {col} {td}")
    for col, td in [("energy_cost","INTEGER DEFAULT 10"),("timer_minutes","INTEGER DEFAULT 30"),
                    ("task_type","TEXT DEFAULT 'daily'")]:
        if col not in task_cols: c.execute(f"ALTER TABLE tasks ADD COLUMN {col} {td}")
    c.commit(); c.close()

init_db()

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_user():
    c = get_db()
    u = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone())
    today = date.today().isoformat()
    if u["last_active"] and u["last_active"] != today and u["hp"] < 100:
        c.execute("UPDATE user SET hp=100 WHERE id=1")
        c.commit()
        u["hp"] = 100
    if u["max_hp"] != 100:
        c.execute("UPDATE user SET max_hp=100, hp=MIN(100, hp) WHERE id=1")
        c.commit()
        u["max_hp"] = 100; u["hp"] = min(100, u["hp"])
    c.close()
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
    for s in ("int","dex","cha","vit"):
        xp = u.get(f"{s}_xp", 0); lv = stat_level_from_xp(xp)
        u[f"{s}_level"] = lv
        u[f"{s}_xp_current"] = xp - stat_xp_for_level(lv)
        u[f"{s}_xp_needed"]  = stat_xp_for_next(lv) - stat_xp_for_level(lv)
    return u

def check_level_up(c):
    u = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone())
    leveled = False
    while u["total_xp"] >= xp_for_level(u["level"]):
        u["level"] += 1; u["max_hp"] = 100; u["hp"] = 100; leveled = True
    if leveled:
        c.execute("UPDATE user SET level=?,max_hp=?,hp=? WHERE id=1",(u["level"],u["max_hp"],u["hp"]))
    return leveled, u["level"]

def check_stat_ups(before, after):
    ups = []
    for s in ("int","dex","cha","vit"):
        ol = stat_level_from_xp(before.get(f"{s}_xp",0)); nl = stat_level_from_xp(after.get(f"{s}_xp",0))
        if nl > ol: ups.append({"stat":s.upper(),"old_level":ol,"new_level":nl})
    return ups

def check_achievements(c):
    u = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone())
    existing = {r["title"] for r in c.execute("SELECT title FROM achievements").fetchall()}
    new_ach = []
    for title, desc, cond in [
        ("First Blood","Complete your first quest", u["total_xp"]>0),
        ("Streak Starter","3-day streak", u["streak"]>=3),
        ("Streak Master","7-day streak", u["streak"]>=7),
        ("Streak Legend","14-day streak", u["streak"]>=14),
        ("INT Initiate","1000 INT XP", u["int_xp"]>=1000),
        ("DEX Initiate","1000 DEX XP", u["dex_xp"]>=1000),
        ("CHA Initiate","1000 CHA XP", u["cha_xp"]>=1000),
        ("VIT Initiate","1000 VIT XP", u["vit_xp"]>=1000),
        ("Level 5","Reach Level 5", u["level"]>=5),
        ("Level 10","Reach Level 10", u["level"]>=10),
        ("Centurion","10000 total XP", u["total_xp"]>=10000),
    ]:
        if cond and title not in existing:
            c.execute("INSERT INTO achievements (title,description,icon) VALUES (?,?,?)",(title,desc,""))
            new_ach.append({"title":title,"description":desc})
    return new_ach

def update_streak(c):
    u = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone())
    today = date.today().isoformat(); last = u["last_active"]
    if last == today: return u["streak"]
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    ns = u["streak"]+1 if last == yesterday else 1
    c.execute("UPDATE user SET streak=?,last_active=?,hp=100 WHERE id=1",(ns, today)); return ns

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

def _llm(system, prompt, fallback):
    try:
        r = ollama.chat(model='llama3.1:8b',
                        messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
                        format="json")
        return json.loads(r["message"]["content"])
    except Exception as e:
        print(f"[LLM] {e}"); return fallback

def generate_daily(user, pending, completed, intent=""):
    p = PERSONAS.get(user["persona"], PERSONAS["operator"])
    prompt = f"""User profile:
Name: {user.get('display_name') or 'User'}
Persona: {p['name']} — {p['desc']}
Profession: {user.get('profession') or 'Not specified'}
Bio: {user.get('bio') or 'Not provided'}
Motivation: {user.get('motivation') or 'Self-improvement'}
Monthly Goal: {user['monthly_goal'] or 'Not set'}
Weekly Goal: {user['weekly_goal'] or 'Not set'}
Level: {user['level']}, Streak: {user['streak']} days
Stats: INT={user['int_xp']} DEX={user['dex_xp']} CHA={user['cha_xp']} VIT={user['vit_xp']}
Pending yesterday: {json.dumps([t['description'] for t in pending]) if pending else 'None'}
Completed today: {json.dumps([t['description'] for t in completed]) if completed else 'None'}"""
    if intent:
        prompt += f"\n\nCRITICAL INSTRUCTION: The user precisely stated they want to focus on: '{intent}'. Ensure the 4 generated tasks explicitly focus on progressing this specific intent while assigning sensible logical stats and XP."
    d = _llm(GM_DAILY, prompt, {"quests":[
        {"description":"Review your weekly goal and plan next steps","xp":100,"stat":"INT","timer_minutes":25},
        {"description":"Take a 20-minute walk or stretch session","xp":80,"stat":"VIT","timer_minutes":20},
        {"description":"Reach out to one person in your network","xp":120,"stat":"CHA","timer_minutes":15},
        {"description":"Work on one hands-on task for 30 minutes","xp":150,"stat":"DEX","timer_minutes":30},
    ]})
    return d.get("quests", [])

def generate_weekly(user, intent=""):
    p = PERSONAS.get(user["persona"], PERSONAS["operator"])
    prompt = f"""Persona: {p['name']}, Profession: {user.get('profession','')}, Bio: {user.get('bio','')},
Monthly Vision: {user['monthly_goal'] or 'Not set'}, Weekly Focus: {user['weekly_goal'] or 'Not set'},
Motivation: {user.get('motivation','')}"""
    if intent:
        prompt += f"\n\nCRITICAL INSTRUCTION: The user precisely stated they want this week to focus on: '{intent}'. Ensure the generated weekly goals explicitly focus on progressing this specific intent."
    d = _llm(GM_WEEKLY, prompt, {"goals":[
        {"description":"Complete a meaningful project milestone this week","xp":500,"stat":"INT"},
        {"description":"Build a positive new habit for 7 consecutive days","xp":400,"stat":"VIT"},
        {"description":"Expand your professional network by 3 connections","xp":350,"stat":"CHA"},
    ]})
    return d.get("goals", [])

def generate_monthly(user, intent=""):
    p = PERSONAS.get(user["persona"], PERSONAS["operator"])
    prompt = f"""Persona: {p['name']}, Profession: {user.get('profession','')}, Bio: {user.get('bio','')},
Monthly Vision: {user['monthly_goal'] or 'Not set'}, Motivation: {user.get('motivation','')}"""
    if intent:
        prompt += f"\n\nCRITICAL INSTRUCTION: The user precisely stated they want this month to focus on: '{intent}'. Ensure the generated monthly milestones explicitly focus on progressing this specific intent."
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
def index(): return render_template("index.html")

@app.route("/api/user")
def api_user(): return jsonify(enrich(get_user()))

@app.route("/api/onboard", methods=["POST"])
def api_onboard():
    d = request.json; c = get_db()
    c.execute("""UPDATE user SET persona=?,display_name=?,profession=?,motivation=?,bio=?,
                 monthly_goal=?,weekly_goal=?,onboarded=1 WHERE id=1""",
              (d.get("persona","operator"),d.get("display_name",""),d.get("profession",""),
               d.get("motivation",""),d.get("bio",""),d.get("monthly_goal",""),d.get("weekly_goal","")))
    c.commit(); c.close()
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
    weekly  = [dict(r) for r in c.execute("SELECT * FROM tasks WHERE task_type='weekly' AND date(created_at)>=? ORDER BY status ASC,id DESC",(week_start,)).fetchall()]
    monthly = [dict(r) for r in c.execute("SELECT * FROM tasks WHERE task_type='monthly' AND date(created_at)>=? ORDER BY status ASC,id DESC",(month_start,)).fetchall()]

    next_month = (date.today().replace(day=28)+timedelta(days=4)).replace(day=1)
    c.close()
    return jsonify({
        "daily": daily, "weekly": weekly, "monthly": monthly,
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
    c.close()

    by_date = {}
    for t in past_daily:
        d = t.pop("d",""); t.pop("task_date",None)
        if not d: continue
        by_date.setdefault(d, {"date":d,"tasks":[],"xp":0,"completed":0,"total":0})
        by_date[d]["tasks"].append(t); by_date[d]["total"] += 1
        if t["status"] == "done":
            by_date[d]["xp"] += t["xp_value"]; by_date[d]["completed"] += 1

    return jsonify({
        "daily_days": sorted(by_date.values(), key=lambda x: x["date"], reverse=True),
        "weekly": past_weekly, "monthly": past_monthly,
    })

@app.route("/api/tasks/generate", methods=["POST"])
def api_gen_daily():
    d = request.get_json(silent=True) or {}
    intent = d.get("intent", "").strip()
    u = get_user(); c = get_db(); today = date.today().isoformat()
    pending  = [dict(r) for r in c.execute("SELECT description FROM tasks WHERE task_type='daily' AND status='pending' AND date(created_at)<?", (today,)).fetchall()]
    completed= [dict(r) for r in c.execute("SELECT description FROM tasks WHERE task_type='daily' AND status='done' AND date(created_at)=?",   (today,)).fetchall()]
    c.close()
    quests = generate_daily(u, pending, completed, intent)
    c = get_db(); created = []
    for q in quests:
        stat = q.get("stat","INT") if q.get("stat") in ("INT","DEX","CHA","VIT") else "INT"
        xp   = min(500,max(50,q.get("xp",100)))
        tmr  = min(120,max(10,q.get("timer_minutes",30)))
        en   = calc_energy(stat,xp)
        cur  = c.execute("INSERT INTO tasks (description,xp_value,stat,energy_cost,timer_minutes,task_type) VALUES (?,?,?,?,?,?)",(q["description"],xp,stat,en,tmr,"daily"))
        created.append({"id":cur.lastrowid,"description":q["description"],"xp_value":xp,"stat":stat,"energy_cost":en,"timer_minutes":tmr,"task_type":"daily","status":"pending"})
    c.commit(); c.close()
    broadcast()
    return jsonify(created)

@app.route("/api/tasks/generate-weekly", methods=["POST"])
def api_gen_weekly():
    d = request.get_json(silent=True) or {}
    intent = d.get("intent", "").strip()
    u = get_user(); goals = generate_weekly(u, intent)
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
    if typ not in ("daily","weekly","monthly"): typ = "daily"
    stat,xp,tmr = categorize(desc); en = calc_energy(stat,xp)
    c = get_db()
    cur = c.execute("INSERT INTO tasks (description,xp_value,stat,energy_cost,timer_minutes,task_type) VALUES (?,?,?,?,?,?)",(desc,xp,stat,en,tmr,typ))
    tid = cur.lastrowid; c.commit(); c.close()
    broadcast()
    return jsonify({"id":tid,"description":desc,"xp_value":xp,"stat":stat,"energy_cost":en,"timer_minutes":tmr,"task_type":typ,"status":"pending"})

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
    sc = t["stat"].lower()+"_xp"
    c.execute(f"UPDATE user SET total_xp=total_xp+?,{sc}={sc}+? WHERE id=1",(t["xp_value"],t["xp_value"]))
    en = t.get("energy_cost",10)
    c.execute("UPDATE user SET hp=MAX(0,hp-?) WHERE id=1",(en,))
    streak = update_streak(c); leveled, lv = check_level_up(c); new_ach = check_achievements(c)
    c.commit()
    ua = dict(c.execute("SELECT * FROM user WHERE id=1").fetchone()); c.close()
    resp = jsonify({"ok":True,"xp_gained":t["xp_value"],"stat":t["stat"],"energy_cost":en,
                    "leveled_up":leveled,"new_level":lv,"streak":streak,
                    "new_achievements":new_ach,"stat_level_ups":check_stat_ups(ub,ua),
                    "user":enrich(ua)})
    broadcast()
    return resp

@app.route("/api/tasks/<int:tid>", methods=["DELETE"])
def api_task_del(tid):
    c = get_db(); c.execute("DELETE FROM tasks WHERE id=?",(tid,)); c.commit(); c.close()
    broadcast()
    return jsonify({"ok":True})

@app.route("/api/achievements")
def api_achievements():
    c = get_db()
    a = [dict(r) for r in c.execute("SELECT * FROM achievements ORDER BY earned_at DESC").fetchall()]
    c.close(); return jsonify({"achievements":a})

@app.route("/api/reset", methods=["POST"])
def api_reset():
    c = get_db()
    c.executescript("""DELETE FROM tasks; DELETE FROM achievements;
        UPDATE user SET persona='',display_name='',bio='',motivation='',profession='',
        profile_photo='',level=1,total_xp=0,int_xp=0,dex_xp=0,cha_xp=0,vit_xp=0,
        hp=100,max_hp=100,streak=0,last_active='',monthly_goal='',weekly_goal='',onboarded=0;""")
    c.commit(); c.close()
    for f in os.listdir(UPLOAD_DIR): os.remove(os.path.join(UPLOAD_DIR,f))
    broadcast("reset")
    return jsonify({"ok":True})

@app.route("/api/events")
def api_events():
    """SSE endpoint — each connected client subscribes here."""
    q = queue.Queue(maxsize=50)
    with sse_lock:
        sse_clients.append(q)
    def stream():
        try:
            # send initial heartbeat
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    msg = q.get(timeout=25)
                    yield msg
                except queue.Empty:
                    # keepalive ping every 25s to prevent proxy timeouts
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            with sse_lock:
                if q in sse_clients:
                    sse_clients.remove(q)
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

if __name__ == "__main__":
    print("[LEVEL UP] starting in system tray... http://localhost:5050")
    # Start flask silently in a background daemon thread
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5050, debug=False, use_reloader=False, threaded=True), daemon=True).start()
    
    # Auto-open browser on startup
    webbrowser.open("http://localhost:5050")
    
    # Boot the system tray item
    icon = pystray.Icon("LevelUp", create_image(), "Level Up RPG", menu=pystray.Menu(
        pystray.MenuItem('Open Dashboard', open_dashboard),
        pystray.MenuItem('Quit', exit_app)
    ))
    icon.run()
