from crewai import Agent, Task, Crew, LLM
from crewai.process import Process
from json_repair import repair_json
import json


# ---- 1. Connect to your Ollama server ----
import os

# Old setup (commented out):
# llm = LLM(
#     model="ollama/llama3.1:latest",
#     base_url="http://192.168.1.16:11434" #"http://localhost:11434"
# )

# New setup: Gemini Primary with Groq Fallback
llm = LLM(
    model="gemini/gemini-1.5-flash",
    api_key=os.environ.get("GEMINI_API_KEY", ""),
    fallbacks=[
        {
            "model": "groq/llama-3.1-8b-instant",
            "api_key": os.environ.get("GROQ_API_KEY", "")
        }
    ]
)


# ---- 2. Define the agent ----
world_builder_agent = Agent(
    role="World Builder",
    goal="Design a believable world with clear rules that fits the story's genre",
    backstory=(
        "You are a world-building expert for novels. You decide what is "
        "physically or magically possible in this story's world, and you "
        "design distinct regions so the setting feels real, not generic. "
        "You never invent characters or write story prose."
    ),
    llm=llm,
    verbose=True
)


def build_world(user_description, genre, number_of_regions=3):
    task_description = (
        f'Here is the story idea:\n\n"{user_description}"\n\n'
        f'Genre: {genre}\n\n'
        f"Design the world for this story with exactly {number_of_regions} regions.\n\n"
        "First decide the realism_tier - one of:\n"
        '  "hard-realistic" (real-world physics only)\n'
        '  "soft-fantastical" (mostly real, a few special rules)\n'
        '  "high-fantasy" (magic/sci-fi systems allowed)\n\n'
        "Then list world_rules that every character must obey.\n\n"
        "Then design each region with a name, terrain, culture, ruling "
        "system, ONE signature_location (a landmark unique to that "
        "region), and any festivals_or_events.\n\n"
        "Finally list actions in three groups:\n"
        "  possible - anything any character can do\n"
        "  impossible - things no one can ever do in this world\n"
        "  conditional - things that are impossible UNLESS a character "
        "has a specific justification (e.g. a bloodline, an item, "
        "special training). For each conditional action, name what "
        "kind of justification would allow it.\n\n"
        "Respond with ONLY valid JSON, no extra text, no markdown "
        "formatting, in exactly this shape:\n"
        "{\n"
        '  "realism_tier": "...",\n'
        '  "world_rules": ["..."],\n'
        '  "regions": [\n'
        '    {"name": "...", "terrain": "...", "culture": "...", '
        '"ruling_system": "...", "signature_location": "...", '
        '"festivals_or_events": ["..."]}\n'
        "  ],\n"
        '  "actions": {\n'
        '    "possible": ["..."],\n'
        '    "impossible": ["..."],\n'
        '    "conditional": [\n'
        '      {"action": "...", "requires_justification_from": "..."}\n'
        "    ]\n"
        "  }\n"
        "}\n\n"
        "IMPORTANT: double check every list and object has a matching "
        "closing bracket or brace before you finish. The whole response "
        "must be ONE single valid JSON object."
    )

    max_attempts = 2
    world_data = None

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            task_description += (
                "\n\nYour previous attempt produced BROKEN JSON - a "
                "list or object was missing its closing bracket or "
                "brace. Carefully check every [ has a matching ] and "
                "every { has a matching } before responding."
            )

        task = Task(
            description=task_description,
            expected_output="A single JSON object matching the shape described above.",
            agent=world_builder_agent
        )

        crew = Crew(
            agents=[world_builder_agent],
            tasks=[task],
            process=Process.sequential
        )

        result = crew.kickoff()
        raw_text = str(result).strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            raw_text = raw_text.replace("json", "", 1).strip()

        try:
            world_data = json.loads(raw_text)
            break
        except json.JSONDecodeError:
            print(f"Attempt {attempt}: normal JSON parsing failed. Trying json-repair...")
            try:
                world_data = repair_json(raw_text, return_objects=True)
                if isinstance(world_data, dict) and world_data:
                    print("json-repair fixed it.")
                    break
                else:
                    world_data = None
            except Exception:
                world_data = None

            if world_data is None and attempt == max_attempts:
                print("Here is the raw text from the final attempt:")
                print(raw_text)

    return world_data