# Story Weaver — AI Novel Generator

[![Render](https://img.shields.io/badge/Live%20Demo%20on%20Render-%2346E3B7.svg?style=for-the-badge&logo=render&logoColor=white)](https://storyweaver-web.onrender.com)

> A multi-agent AI system that writes a full novel — world, characters, and every chapter — from a single sentence. Powered by **CrewAI** and **Groq (Llama 3.1)** for lightning-fast inference, featuring a beautiful UI, chapter downloads, and live Server-Sent Events (SSE) streaming.

---

## ✨ What it does

1. **You type one sentence** describing a story idea.
2. **Seven AI agents go to work:**
   - **Story Planner** — Builds the chapter-by-chapter outline.
   - **World Builder** — Designs the world, locations, and magical laws.
   - **Character Builder** — Creates every character with deep backstories.
   - **Scene Planner** (per chapter) — Maps out scene beats and emotional direction.
   - **Writing Agent** (per chapter) — Writes the full chapter prose.
   - **Validator** (per chapter) — Checks consistency and forces rewrites if agents break rules.
   - **Story Bible Updater** (per chapter) — Keeps continuity and memories alive.
3. You watch each chapter appear **live** as it is written.
4. Download your finished novel seamlessly!

## 🖥️ Stack

| Layer | Tech |
|-------|------|
| **LLM Inference** | Groq (`llama-3.1-8b-instant`) |
| **Agent Framework** | [CrewAI](https://crewai.com) + LiteLLM |
| **Backend** | Python + Flask |
| **Frontend** | Vanilla HTML / CSS / JS (SSE streaming) |

---

## ⚡ Quick Start (Local Setup)

### Prerequisites
- Python 3.10+
- A Groq API Key (You can get one for free at [Groq.com](https://console.groq.com/))

### 1. Clone & Install
```bash
git clone https://github.com/M-Srinivasan/storyweaver-web.git
cd storyweaver-web

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up Your API Key (The Easy Way)
Instead of dealing with terminal environment variables, you can create a simple text file in the project folder to auto-load your API key!
1. Create a file named `Story_Weaver_APIKEY.txt` in the root folder.
2. Add the following line to it:
   ```text
   Groq_API key = gsk_your_api_key_here
   ```
*(The backend will automatically find this file and securely load your key every time you run it!)*

### 3. Run the App
```bash
python app.py
```
Open **http://127.0.0.1:5000** in your browser to start weaving!

---

## ☁️ Hosting on Render

This project is fully configured to be deployed easily on [Render.com](https://render.com/).

### Important Deployment Instructions:
1. Connect your GitHub repository to Render as a **Web Service**.
2. **Environment Variables**: Add your `GROQ_API_KEY` in the Render environment variables tab.
3. **Start Command (CRITICAL)**: By default, Render uses `gunicorn`, which forcefully buffers streaming data and causes a 30-second timeout disconnect during generation. 
   To fix this, change your Start Command in Render to:
   ```bash
   python app.py
   ```
   *(The `app.py` file is smart enough to detect it is on Render and will automatically bind to the correct network ports natively, bypassing all timeouts!)*

---

## 📁 Project Structure

```text
storyweaver-web/
├── app.py                  # Flask server + SSE streaming & Port binding
├── story_planner.py        # Story outline agent
├── world_builder.py        # World creation agent
├── character_builder.py    # Character creation agent
├── scene_planner.py        # Per-chapter scene planning
├── writing_agent.py        # Per-chapter writing agent
├── story_validator.py      # Consistency checker
├── story_bible_updater.py  # Continuity updater
├── story_bible.py          # Story bible data model
├── context_composer.py     # Assembles context for each agent
├── templates/
│   └── index.html          # Web UI
├── static/
│   ├── style.css           # UI Styling
│   └── script.js           # Vanilla JS (SSE client & frontend logic)
├── requirements.txt
└── README.md
```

---
*Built with CrewAI. Hosted on Render.*
