from crewai import Agent, Task, Crew, LLM
from crewai.process import Process
from json_repair import repair_json
import json

# ---- 1. Connect to your Ollama server ----
import os

import litellm
litellm.drop_params = True

llm = LLM(
    model="groq/llama-3.1-8b-instant",
    api_key=os.environ.get("GROQ_API_KEY", "")
)
)

# ---- 2. Define the agent ----
scene_planner_agent = Agent(
    role="Scene Planner",
    goal="Turn one chapter's synopsis into a clear, filmable scene blueprint",
    backstory=(
        "You plan scenes for novels, one chapter at a time. You decide "
        "who is in the scene, where it happens, what the conflict is, "
        "and how the scene should end - but you never write the actual "
        "prose. That's for someone else."
    ),
    llm=llm,
    verbose=True
)

def plan_scene(chapter, character_names, region_names, previous_chapter_ending=None):

    # Build the "pick up from here" block when we have a previous chapter
    if previous_chapter_ending:
        continuity_block = (
            "CONTINUITY REQUIREMENT - the previous chapter ended as follows:\n"
            "---\n"
            f"{previous_chapter_ending}\n"
            "---\n"
            "Your scene plan MUST pick up directly from that ending. "
            "Characters must be in the same location and emotional state "
            "they were in at the end of the previous chapter unless the "
            "synopsis explicitly says they moved or changed. "
            "Do NOT jump to a new location or a new situation without "
            "a plausible in-story reason that follows from the above.\n\n"
        )
    else:
        continuity_block = ""

    task_description = (
        f"Chapter {chapter['chapter_number']}: {chapter['title']}\n"
        f"Synopsis: {chapter['synopsis']}\n\n"
        f"{continuity_block}"
        f"Characters available in this story: {character_names}\n"
        f"Regions available in this story: {region_names}\n\n"
        "Plan this ONE scene. Pick only the characters from the list "
        "above who actually belong in this chapter, and only a "
        "location that fits one of the regions above.\n\n"
        "Respond with ONLY valid JSON, no extra text, no markdown "
        "formatting, in exactly this shape:\n"
        "{\n"
        '  "objective": "...",\n'
        '  "characters": ["..."],\n'
        '  "location": "...",\n'
        '  "conflict": "...",\n'
        '  "emotion": "...",\n'
        '  "ending_condition": "...",\n'
        '  "required_memories": ["..."],\n'
        '  "required_plot_threads": ["..."]\n'
        "}\n\n"
        "IMPORTANT: every string value must be plain text with no stray "
        "punctuation right after the closing quote. Double check the "
        "JSON is valid before responding."
    )

    max_attempts = 2
    scene_blueprint = None

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            task_description += (
                "\n\nYour previous attempt produced BROKEN JSON - there "
                "was a stray character (like an extra period or quote) "
                "right after one of the string values. Carefully check "
                "every value ends cleanly with just a closing quote "
                "before the comma or closing brace."
            )

        task = Task(
            description=task_description,
            expected_output="A single JSON object matching the shape described above.",
            agent=scene_planner_agent
        )

        crew = Crew(
            agents=[scene_planner_agent],
            tasks=[task],
            process=Process.sequential
        )

        result = crew.kickoff()
        raw_text = str(result).strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            raw_text = raw_text.replace("json", "", 1).strip()

        try:
            scene_blueprint = json.loads(raw_text)
            break
        except json.JSONDecodeError:
            print(f"Attempt {attempt}: normal JSON parsing failed. Trying json-repair...")
            try:
                scene_blueprint = repair_json(raw_text, return_objects=True)
                if isinstance(scene_blueprint, dict) and scene_blueprint:
                    print("json-repair fixed it.")
                    break
                else:
                    scene_blueprint = None
            except Exception:
                scene_blueprint = None

            if scene_blueprint is None and attempt == max_attempts:
                print("Here is the raw text from the final attempt:")
                print(raw_text)

    return scene_blueprint
