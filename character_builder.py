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
    model="gemini/gemini-1.5-pro",
    api_key=os.environ.get("GEMINI_API_KEY", ""),
    fallbacks=[
        {
            "model": "groq/llama-3.1-8b-instant",
            "api_key": os.environ.get("GROQ_API_KEY", "")
        }
    ]
)

# ---- 2. Define the agent ----
character_builder_agent = Agent(
    role="Character Builder",
    goal="Create believable characters that fit inside the story's world rules",
    backstory=(
        "You create novel characters in three tiers: main (full detail), "
        "side (recurring but lighter), and passing (appears once or "
        "twice, bare minimum detail). Appearance and personality are "
        "short tags, not paragraphs. If a character has any skill or "
        "trait that this world marks as 'conditional', you must give "
        "that character a clear justification for having it. You never "
        "invent world rules or write story prose."
    ),
    llm=llm,
    verbose=True
)

def build_characters(user_description, genre, world_rules, conditional_actions,
                      number_of_main=1, number_of_side=2, number_of_passing=2):

    task_description = (
        f'Here is the story idea:\n\n"{user_description}"\n\n'
        f"Genre: {genre}\n\n"
        f"World rules the characters must obey:\n{world_rules}\n\n"
        "Actions that are conditional in this world (impossible "
        "unless a character has a specific justification):\n"
        f"{conditional_actions}\n\n"
        f"Create exactly {number_of_main} main character(s), "
        f"{number_of_side} side character(s), and "
        f"{number_of_passing} passing character(s).\n\n"
        "For main and side characters: give appearance_tags (short "
        "words, not sentences), behavior_tags (short words), a "
        "background, goals, and current_state. If you give any "
        "character a skill or trait that matches one of the "
        "conditional actions above, you MUST add it to their "
        "justifications list explaining where it comes from.\n\n"
        "For passing characters: only name, appearance_tags, "
        "occupation, location, and purpose (why they appear at all).\n\n"
        "Respond with ONLY valid JSON, no extra text, no markdown "
        "formatting, in exactly this shape:\n"
        "{\n"
        '  "main": [\n'
        '    {"name": "...", "appearance_tags": ["..."], '
        '"behavior_tags": ["..."], "background": "...", "goals": "...", '
        '"justifications": [{"trait_or_skill": "...", "source": "..."}], '
        '"current_state": {"emotion": "...", "health": "...", '
        '"location": "...", "status": "..."}}\n'
        "  ],\n"
        '  "side": [ ... same shape as main ... ],\n'
        '  "passing": [\n'
        '    {"name": "...", "appearance_tags": ["..."], '
        '"occupation": "...", "location": "...", "purpose": "..."}\n'
        "  ]\n"
        "}\n\n"
        "IMPORTANT: the whole response must be ONE single JSON object "
        'with exactly three keys - "main", "side", and "passing" - all '
        "inside one pair of outer curly braces. Do not close the outer "
        "object early and do not put \"passing\" outside the braces."
    )

    max_attempts = 2
    character_data = None

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            task_description += (
                "\n\nYour previous attempt produced BROKEN JSON - it "
                "closed the outer object too early and left \"passing\" "
                "outside the braces. Fix this: return one single valid "
                "JSON object containing all three keys."
            )

        task = Task(
            description=task_description,
            expected_output="A single JSON object matching the shape described above.",
            agent=character_builder_agent
        )

        crew = Crew(
            agents=[character_builder_agent],
            tasks=[task],
            process=Process.sequential
        )

        result = crew.kickoff()
        raw_text = str(result).strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            raw_text = raw_text.replace("json", "", 1).strip()

        try:
            character_data = json.loads(raw_text)
            break
        except json.JSONDecodeError:
            print(f"Attempt {attempt}: normal JSON parsing failed. Trying json-repair...")
            try:
                character_data = repair_json(raw_text, return_objects=True)
                if isinstance(character_data, dict) and character_data:
                    print("json-repair fixed it.")
                    break
                else:
                    character_data = None
            except Exception:
                character_data = None

            if character_data is None and attempt == max_attempts:
                print("Here is the raw text from the final attempt:")
                print(raw_text)

    return character_data
