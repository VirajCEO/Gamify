# LEVEL UP — AI Productivity RPG

> Turn your daily tasks into quests. Gain XP. Level up your life.

**LEVEL UP** is a local-first, AI-driven productivity app that gamifies your day using RPG mechanics. An LLM acts as your personal Game Master — it reads your goals, learns your persona, and generates hyper-relevant daily, weekly, and monthly quests. Complete them to earn XP, level up your stats, maintain streaks, and unlock achievements.

Everything runs on your machine. No cloud. No subscriptions. No data leaving your device.

---

## Features

### Core RPG Engine
- **4 Personas** — Visionary, Operator, Scholar, Vitalist. Each weights quest generation differently.
- **4 Stats** — INT (Intelligence), DEX (Dexterity), CHA (Charisma), VIT (Vitality).
- **Leveling System** — Earn XP per completed task. Overall level + individual stat levels.
- **HP / Energy Bar** — INT/DEX tasks drain energy; VIT tasks restore it.
- **Daily Streaks** — Maintain consecutive active days for streak bonuses.
- **Achievements** — Unlock hard-coded milestone badges (First Blood, Streak Master, Centurion, etc.)

### AI Game Master (via Ollama)
- Generates **4 Daily Quests** every morning, tailored to your goals, persona, profession, and recent history.
- Generates **3 Weekly Goals** and **2–3 Monthly Milestones**.
- **Brainstorm mode** — type a focus area and the AI generates quests around it.
- **Quick Add** — type any task; the AI auto-categorizes it, assigns XP and a stat tag.
- **Dynamic scaling** — harder quests on streaks, easier wins after failures.
- Fully local via [Ollama](https://ollama.com) — works offline with `llama3.1:8b` (or any compatible model).

### UI / UX
- Polished dark & light theme with animated stat bars, XP bars, and HP bar.
- Task-level countdown timers.
- Confetti + sound on task completion.
- "Level Up!" full-screen overlay animation.
- Profile page with photo upload, bio, motivation, and persona selection.
- Past task history viewer (by day, week, month).
- Real-time multi-device sync via Server-Sent Events (SSE) — open on phone + desktop simultaneously.

### System Tray App
- Runs silently in the Windows system tray.
- Auto-opens the dashboard in your default browser on launch.
- "Open Dashboard" and "Quit" tray menu items.

### Voice Bot *(bonus module)*
- Separate real-time voice assistant powered by local STT + LLM + TTS.
- **Speech-to-Text**: [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) with SenseVoice (multilingual) and Dolphin (Hindi).
- **LLM**: Ollama (`llama3.1:8b`).
- **Text-to-Speech**: [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) — English, Japanese, Hindi.
- Silero VAD for accurate speech segmentation.
- Streamed audio playback chunk-by-chunk for minimal latency.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, Flask 3.x |
| Database | SQLite (via `sqlite3`, WAL mode) |
| LLM | [Ollama](https://ollama.com) (`llama3.1:8b`) |
| Real-time sync | Server-Sent Events (SSE) |
| Voice STT | [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) |
| Voice TTS | [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) |
| Voice transport | Flask-SocketIO (WebSocket) |
| System tray | pystray + Pillow |
| Frontend | Vanilla JS, HTML5, CSS (no framework) |

---

## Prerequisites

- **Python 3.11+**
- **[Ollama](https://ollama.com)** installed and running
- The `llama3.1:8b` model pulled in Ollama

```bash
# Install Ollama (see https://ollama.com for your OS)
ollama pull llama3.1:8b
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/level-up-rpg.git
cd level-up-rpg
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
python app.py
```

The app starts in the system tray and opens `http://localhost:5050` in your browser automatically.

---

## requirements.txt

Create this file in the project root if it doesn't exist:

```
flask>=3.0
ollama>=0.6
pystray>=0.19
Pillow>=10.0
```

> **Voice Bot** has additional dependencies — see [Voice Bot Setup](#voice-bot-setup) below.

---

## Auto-Start on Windows Boot

The repo includes `Gamify_AutoStart.vbs` — a VBScript that launches the app silently at login with no console window or terminal flash.

### How it works

```vbscript
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\viraj\OneDrive\Desktop\Gamify"
WshShell.Run "pythonw app.py", 0, False
```

- Uses **`pythonw`** instead of `python` — identical runtime, but suppresses the console window entirely.
- Window style `0` = fully hidden.
- `False` = fire-and-forget (doesn't wait for the process to finish).

### Setup

**1. Edit the path in the script**

Open `Gamify_AutoStart.vbs` in Notepad and update `CurrentDirectory` to wherever you cloned the repo:

```vbscript
WshShell.CurrentDirectory = "C:\path\to\your\level-up-rpg"
```

**2. Make sure `pythonw` is on your PATH**

`pythonw.exe` lives next to `python.exe` — if `python` works in your terminal, `pythonw` works too. If you're using a virtual environment, point the script to the venv's `pythonw.exe` instead:

```vbscript
WshShell.Run "C:\path\to\your\level-up-rpg\venv\Scripts\pythonw.exe app.py", 0, False
```

**3. Add the script to Windows Startup**

Press `Win + R`, type:
```
shell:startup
```
Then **copy a shortcut** to `Gamify_AutoStart.vbs` into the folder that opens (do not move the original).

Next time you log in, LEVEL UP starts automatically in the background — just look for the icon in your system tray.

### Stopping the app

Right-click the tray icon → **Quit**, or open Task Manager and end the `pythonw` process.

---

## Usage

### First Launch — Onboarding

1. Enter your name, profession, and a short bio.
2. Write your **Monthly Vision** (1 sentence) and **Weekly Focus** (1 sentence).
3. Pick a **Persona** that matches your current life phase.
4. Click **Enter the Arena**.

### Daily Workflow

| Action | How |
|---|---|
| Generate today's quests | Click **Auto Generate** (Daily tab) |
| Focus on a specific topic | Type in the intent box → **Brainstorm** |
| Add your own task | Type in Quick Add → **Add** |
| Complete a task | Click the checkbox — get XP + dopamine hit |
| Start a task timer | Click the ⏱ timer on any task |

### Quest Tabs

- **Daily** — Today's quests. Regenerate anytime.
- **Weekly** — Unlocks Saturday & Sunday for completion.
- **Monthly** — Unlocks the last 2 days of the month.

### Settings

Click your avatar (top-left) to edit your profile, goals, persona, and profile photo.

---

## Project Structure

```
level-up-rpg/
├── app.py                      # Main Flask app — routes, DB, LLM, SSE, tray
├── voice_bot.py                # Standalone voice assistant (port 5002)
├── Gamify_AutoStart.vbs        # Windows silent auto-start script
├── templates/
│   ├── index.html              # Main dashboard (single-page app)
│   └── voice_bot.html          # Voice bot UI
├── static/
│   └── uploads/                # User profile photos (git-ignored)
├── STT/
│   └── models/                 # sherpa-onnx model files (git-ignored, ~1 GB)
├── levelup.db                  # SQLite database (git-ignored, auto-created)
├── requirements.txt
├── requirements.md             # Original design spec
└── README.md
```

---

## Voice Bot Setup

The voice bot is a separate Flask-SocketIO server (`voice_bot.py`, port 5002). It requires additional model files that must be downloaded manually.

### 1. Install extra dependencies

```bash
pip install flask-socketio sherpa-onnx kokoro soundfile numpy unidic-lite
```

### 2. Download STT models

Place models inside `STT/models/`:

| Model | Language | Download |
|---|---|---|
| `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17` | EN / JA | [k2-fsa releases](https://github.com/k2-fsa/sherpa-onnx/releases) |
| `sherpa-onnx-dolphin-base-ctc-multi-lang-int8-2025-04-02` | HI / Multi | [k2-fsa releases](https://github.com/k2-fsa/sherpa-onnx/releases) |
| `silero_vad.onnx` | VAD | [snakers4/silero-vad](https://github.com/snakers4/silero-vad) |

Expected structure:
```
STT/models/
├── sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/
│   ├── model.int8.onnx
│   └── tokens.txt
├── sherpa-onnx-dolphin-base-ctc-multi-lang-int8-2025-04-02/
│   ├── model.int8.onnx
│   └── tokens.txt
└── silero_vad.onnx
```

### 3. Run the voice bot

```bash
python voice_bot.py
# Opens at http://localhost:5002
```

### Supported Languages

| Code | Language | STT Engine | TTS Voice |
|---|---|---|---|
| `en` | English | SenseVoice | Kokoro `af_heart` |
| `ja` | Japanese | SenseVoice | Kokoro `jf_alpha` |
| `hi` | Hindi | Dolphin CTC | Kokoro `hf_alpha` |

---

## Database Schema

The SQLite database (`levelup.db`) is auto-created on first run.

```sql
-- User profile and stats (single-row, id=1)
CREATE TABLE user (
    id INTEGER PRIMARY KEY DEFAULT 1,
    persona TEXT,           -- visionary | operator | scholar | vitalist
    display_name TEXT,
    bio TEXT,
    motivation TEXT,
    profession TEXT,
    profile_photo TEXT,     -- filename in static/uploads/
    level INTEGER DEFAULT 1,
    total_xp INTEGER DEFAULT 0,
    int_xp INTEGER DEFAULT 0,
    dex_xp INTEGER DEFAULT 0,
    cha_xp INTEGER DEFAULT 0,
    vit_xp INTEGER DEFAULT 0,
    hp INTEGER DEFAULT 100,
    max_hp INTEGER DEFAULT 100,
    streak INTEGER DEFAULT 0,
    last_active TEXT,
    monthly_goal TEXT,
    weekly_goal TEXT,
    onboarded INTEGER DEFAULT 0
);

-- Quests (daily / weekly / monthly)
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    xp_value INTEGER DEFAULT 100,
    stat TEXT DEFAULT 'INT',        -- INT | DEX | CHA | VIT
    energy_cost INTEGER DEFAULT 10,
    timer_minutes INTEGER DEFAULT 30,
    task_type TEXT DEFAULT 'daily', -- daily | weekly | monthly
    status TEXT DEFAULT 'pending',  -- pending | done
    created_at TEXT,
    completed_at TEXT
);

-- Earned achievements
CREATE TABLE achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    icon TEXT,
    earned_at TEXT
);
```

---

## API Reference

All endpoints are served by `app.py` on port `5050`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/user` | Get user profile + computed stat levels |
| POST | `/api/onboard` | Complete onboarding |
| POST | `/api/user/update` | Update profile fields |
| POST | `/api/user/photo` | Upload profile photo |
| DELETE | `/api/user/photo` | Remove profile photo |
| GET | `/api/tasks` | Get today's daily / this week's weekly / this month's monthly tasks |
| GET | `/api/history` | Get past tasks grouped by day/week/month |
| POST | `/api/tasks/generate` | AI-generate daily quests (body: `{"intent":"..."}`) |
| POST | `/api/tasks/generate-weekly` | AI-generate weekly goals |
| POST | `/api/tasks/generate-monthly` | AI-generate monthly milestones |
| POST | `/api/tasks/add` | Quick-add a task (AI categorizes it) |
| POST | `/api/tasks/<id>/complete` | Complete a task — awards XP, checks level-up |
| DELETE | `/api/tasks/<id>` | Delete a task |
| GET | `/api/achievements` | List earned achievements |
| GET | `/api/events` | SSE stream for real-time multi-device sync |
| POST | `/api/reset` | Reset all progress (destructive) |

---

## LLM Prompts

The Game Master uses three system prompts, defined at the top of `app.py`:

| Constant | Purpose |
|---|---|
| `GM_DAILY` | Generate 4 daily quests as JSON |
| `GM_WEEKLY` | Generate 3 weekly goals as JSON |
| `GM_MONTHLY` | Generate 2–3 monthly milestones as JSON |

All prompts request structured JSON output. If the LLM call fails (Ollama not running, model not found, invalid JSON), the app falls back to a hardcoded set of generic quests — it never crashes.

To swap the model, change the `model` parameter in the `_llm()` function in `app.py`:

```python
r = ollama.chat(model='llama3.1:8b', ...)  # change to any Ollama model
```

---

## Configuration

There is no config file yet — key values live at the top of `app.py`:

| Variable | Default | Description |
|---|---|---|
| `DB_PATH` | `levelup.db` (next to app.py) | SQLite database location |
| `UPLOAD_DIR` | `static/uploads/` | Profile photo storage |
| `ENERGY_COSTS` | `INT:12, DEX:10, CHA:6, VIT:-15` | HP drain per 100 XP |
| Port | `5050` | Flask server port (last line of `app.py`) |

---

## .gitignore

Create a `.gitignore` in the project root:

```gitignore
# Database
levelup.db

# Uploaded profile photos
static/uploads/

# STT model files (large binaries, download separately)
STT/models/
TTS/models/

# Python
__pycache__/
*.py[cod]
*.pyo
venv/
.venv/
*.egg-info/

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
```

---

## Contributing

Contributions are welcome! Here are good places to start:

- **New personas** — add entries to the `PERSONAS` dict in `app.py`
- **New achievements** — add tuples to `check_achievements()` in `app.py`
- **Model swap** — test with other Ollama models (Mistral, Phi-3, Gemma 3)
- **Mobile layout** — the CSS grid currently targets desktop (1400 px max-width)
- **Export / import** — let users back up and restore their `levelup.db`
- **Weekly title generation** — the spec calls for an AI-generated weekly title (not yet implemented)

### Development setup

```bash
git clone https://github.com/YOUR_USERNAME/level-up-rpg.git
cd level-up-rpg
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
# Start Ollama in a separate terminal: ollama serve
python app.py
```

The Flask app runs with `debug=False` and `use_reloader=False` because it manages a system tray process. For development, you can start it directly without the tray:

```python
# In app.py, replace the __main__ block temporarily:
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
```

---

## Roadmap

- [ ] `requirements.txt` + proper packaging
- [ ] Config file (`.env` or `config.toml`) for port, model, energy costs
- [ ] AI-generated weekly title ("The Silicon Architect", "The Relentless Executor")
- [ ] Mobile-responsive layout
- [ ] Multi-user support
- [ ] Export / import progress (JSON or CSV)
- [ ] Webhook / notification support (push alert on streak break)
- [ ] macOS / Linux system tray support

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

- [Ollama](https://ollama.com) — local LLM inference
- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) — on-device speech recognition
- [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) — open-weight TTS model
- [Silero VAD](https://github.com/snakers4/silero-vad) — voice activity detection
- [pystray](https://github.com/moses-palmer/pystray) — system tray integration
