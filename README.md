# StoryWeaver — AI Novel Generator

> A multi-agent AI system that writes a full novel — world, characters, and every chapter — from a single sentence. Now powered by Gemini/Groq via API and ready to be hosted on Render.

---

## ✨ What it does

1. You type one sentence describing a story
2. Seven AI agents go to work:
   - **Story Planner** — builds the chapter-by-chapter outline
   - **World Builder** — designs the world, locations, lore
   - **Character Builder** — creates every character with backstories
   - **Scene Planner** (per chapter) — plans scene beats
   - **Writing Agent** (per chapter) — writes the full chapter
   - **Validator** (per chapter) — checks consistency
   - **Story Bible Updater** (per chapter) — keeps continuity
3. You watch each chapter appear live as it's written
4. Read your novel in the built-in dark editorial reader

## 🖥️ Stack

| Layer | Tech |
|-------|------|
| LLM | Gemini 1.5 Flash / Groq via API |
| Agents | [CrewAI](https://crewai.com) |
| Backend | Python + Flask (SSE streaming) |
| Frontend | Vanilla HTML / CSS / JS |

## ⚡ Quick Start

### Prerequisites
- Python 3.10+
- API Key for Gemini (`GEMINI_API_KEY`) or Groq (`GROQ_API_KEY`)

```bash
# 1. Clone
git clone https://github.com/M-Srinivasan/storyweaver-web.git
cd storyweaver-web

# 2. Set up environment variables
# Set your GEMINI_API_KEY or GROQ_API_KEY in your environment

# 3. Create a virtual environment and install dependencies
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt

# 4. Run
python app.py
```

Open **http://localhost:5000** in your browser.

### Hosting on Render
This project can be easily deployed to [Render](https://render.com/). Make sure to set your `GEMINI_API_KEY` (or the respective key for your chosen model) in the Environment variables in Render's dashboard. A `.python-version` file is included to ensure compatibility and avoid build errors.

## 🌐 Share via ngrok

To make it accessible from any device:

```bash
# Terminal 1: start the app
python app.py

# Terminal 2: create a public tunnel
ngrok http 5000
```

Copy the `https://xxxx.ngrok-free.app` URL and share it.

## 📁 Project Structure

```
storyweaver/
├── app.py                  # Flask server + SSE streaming
├── story_planner.py        # Story outline agent
├── world_builder.py        # World creation agent
├── character_builder.py    # Character creation agent
├── scene_planner.py        # Per-chapter scene planning
├── writing_agent.py        # Per-chapter writing agent
├── story_validator.py      # Consistency checker
├── story_bible_updater.py  # Continuity updater
├── story_bible.py          # Story bible data model
├── context_composer.py     # Assembles context for each agent
├── style_guide.py          # Writing style utilities
├── templates/
│   └── index.html          # Web UI
├── static/
│   ├── style.css           # Dark editorial-fantasy theme
│   ├── script.js           # Vanilla JS (SSE client)
│   └── hero.png            # AI-generated hero illustration
├── requirements.txt
└── README.md
```

## ⚙️ Configuration

All model settings are in the individual agent files. The model is currently configured to use Gemini (`gemini/gemini-1.5-flash`). To use a different model:

```python
# In writing_agent.py, world_builder.py, etc.
# Change this line:
model="gemini/gemini-1.5-flash",
# To e.g.:
model="groq/llama-3.1-8b-instant",
# (Make sure you provide the corresponding API key in your environment)
```

## 📋 Requirements

```
crewai
json-repair
flask
```

---

*Built with CrewAI. Hosted on Render.*
