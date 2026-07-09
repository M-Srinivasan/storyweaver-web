from langchain_groq import ChatGroq
from crewai import Agent, Task, Crew, LLM
from crewai.process import Process
from json_repair import repair_json
import json

# ---- 1. Connect to your Ollama server ----
import os

# Old setup (commented out):
# llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.environ.get("GROQ_API_KEY", "")
)

# ---- 2. Define the agent ----
story_bible_updater_agent = Agent(
    role="Story Bible Updater",
    goal="Figure out exactly what changed in the story after this chapter",
    backstory=(
        "You read a finished chapter and report what changed - "
        "character emotions, health, location, and status, whether "
        "time passed, any important new memory worth remembering, and "
        "any plot threads that started or resolved. You do not rewrite "
        "the chapter and you do not invent changes that didn't happen."
    ),
    llm=llm,
    verbose=True
)

def get_story_bible_updates(chapter_text, scene_blueprint, story_bible):

    characters_in_scene = scene_blueprint.get("characters", [])
    current_day = story_bible["timeline"]["current_day"]

    task_description = (
        f"Here is the chapter that was just written:\n\n{chapter_text}\n\n"
        f"Characters who were in this scene: {characters_in_scene}\n"
        f"The story's current day count before this chapter: {current_day}\n\n"
        "Based ONLY on what actually happened in the chapter above, "
        "report what changed:\n"
        "- For each character who was in the scene, their new emotion, "
        "health, location, and status (if unchanged, repeat the old "
        "value rather than guessing something new).\n"
        "- Whether any time passed, and the new current_day number.\n"
        "- One important new memory worth remembering long-term, if "
        "anything significant happened (or an empty string if not).\n"
        "- Any brand new plot thread that started, or any plot thread "
        "that got resolved in this chapter.\n\n"
        "Respond with ONLY valid JSON, no extra text, no markdown "
        "formatting. Here is a REAL EXAMPLE showing the exact shape "
        "(use your own actual values, never literally write \"...\"):\n"
        "{\n"
        '  "character_updates": [\n'
        '    {"name": "Edric", "emotion": "determined but wary", '
        '"health": "bruised but able to walk", "location": "the Celestial Spire", '
        '"status": "searching for answers"}\n'
        "  ],\n"
        f'  "current_day": {current_day},\n'
        '  "timeline_event": "Edric explored the spire and found a hidden clue",\n'
        '  "new_memory": "Edric saw a shadow cross the spire and felt a flicker of recognition",\n'
        '  "new_active_plot_threads": ["Edric suspects his dreams are connected to his lost memories"],\n'
        '  "resolved_plot_threads": []\n'
        "}\n\n"
        "Every field must contain real descriptive text based on what "
        "actually happened in the chapter above. Never write the "
        'literal characters "..." as a value - that is only a '
        "placeholder in this example, not something to copy."
    )

    task = Task(
        description=task_description,
        expected_output="A single JSON object matching the shape described above.",
        agent=story_bible_updater_agent
    )

    crew = Crew(
        agents=[story_bible_updater_agent],
        tasks=[task],
        process=Process.sequential
    )

    result = crew.kickoff()
    raw_text = str(result).strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json", "", 1).strip()

    try:
        updates = json.loads(raw_text)
    except json.JSONDecodeError:
        print("Normal JSON parsing failed. Trying json-repair...")
        try:
            updates = repair_json(raw_text, return_objects=True)
            if not (isinstance(updates, dict) and updates):
                updates = None
        except Exception:
            updates = None

        if updates is None:
            print("Could not read the AI's response as JSON. Here is the raw text:")
            print(raw_text)
    return updates

def find_character_in_bible(name, story_bible):
    all_characters = (
        story_bible["characters"]["main"]
        + story_bible["characters"]["side"]
        + story_bible["characters"]["passing"]
    )
    for character in all_characters:
        if character.get("name") == name:
            return character
    return None

def apply_updates(story_bible, updates):

    for change in updates.get("character_updates", []):
        character = find_character_in_bible(change.get("name"), story_bible)
        if character is not None:
            character.setdefault("current_state", {})
            character["current_state"]["emotion"] = change.get("emotion", character["current_state"].get("emotion", ""))
            character["current_state"]["health"] = change.get("health", character["current_state"].get("health", ""))
            character["current_state"]["location"] = change.get("location", character["current_state"].get("location", ""))
            character["current_state"]["status"] = change.get("status", character["current_state"].get("status", ""))

    # Update timeline
    story_bible["timeline"]["current_day"] = updates.get("current_day", story_bible["timeline"]["current_day"])
    timeline_event = updates.get("timeline_event", "")
    if timeline_event:
        story_bible["timeline"]["events"].append(timeline_event)

    # Add new memory
    new_memory = updates.get("new_memory", "")
    if new_memory:
        story_bible["memory"].append(new_memory)

    # Update plot threads
    for thread in updates.get("new_active_plot_threads", []):
        if thread and thread not in story_bible["plot_threads"]["active"]:
            story_bible["plot_threads"]["active"].append(thread)

    for thread in updates.get("resolved_plot_threads", []):
        if thread in story_bible["plot_threads"]["active"]:
            story_bible["plot_threads"]["active"].remove(thread)
        if thread and thread not in story_bible["plot_threads"]["resolved"]:
            story_bible["plot_threads"]["resolved"].append(thread)

    return story_bible
