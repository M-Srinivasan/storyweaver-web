# StoryWeaver — AI Novel Generator

> A multi-agent AI system that writes a full novel — world, characters, and every chapter — from a single sentence. Runs 100% locally. No API keys. No cloud costs.

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
| LLM | [Ollama](https://ollama.com) — `llama3.1` running locally |
| Agents | [CrewAI](https://crewai.com) |
| Backend | Python + Flask (SSE streaming) |
| Frontend | Vanilla HTML / CSS / JS |

## ⚡ Quick Start

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/download) installed

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/storyweaver.git
cd storyweaver

# 2. Pull the model (one-time download, ~4.7 GB)
ollama pull llama3.1

# 3. Create a virtual environment and install dependencies
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt

# 4. Run
python app.py
```

Open **http://localhost:5000** in your browser.

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

All model settings are in the individual agent files. The model is configured as `ollama/llama3.1:latest`. To use a different model:

```python
# In writing_agent.py, world_builder.py, etc.
# Change this line:
model="ollama/llama3.1:latest",
# To e.g.:
model="ollama/mistral:latest",
# or for a faster/smaller model:
model="ollama/llama3.2:3b",
```

## 📋 Requirements

```
crewai
json-repair
flask
```

---

*Built with CrewAI + Ollama. All inference runs on your machine.*
