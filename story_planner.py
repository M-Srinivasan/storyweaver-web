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
    model="groq/llama-3.1-8b-instant",
    api_key=os.environ.get("GROQ_API_KEY", "")
)

# ---- 2. Define the agent ----
story_planner_agent = Agent(
    role="Story Planner",
    goal="Turn a story idea into a clear chapter-by-chapter outline",
    backstory=(
        "You are an experienced novel outliner. You never write actual "
        "prose - you only plan structure: chapters, what happens in "
        "each one, and how the story ends."
    ),
    llm=llm,
    verbose=True
)

def plan_story(user_description, number_of_chapters=5):

    task_description = (
        f'Here is the user\'s story idea:\n\n"{user_description}"\n\n'
        f"Create an outline with exactly {number_of_chapters} chapters.\n\n"
        "Respond with ONLY valid JSON, no extra text, no markdown "
        "formatting, in exactly this shape:\n"
        "{\n"
        '  "genre": "...",\n'
        '  "chapters": [\n'
        '    {"chapter_number": 1, "title": "...", "synopsis": "..."}\n'
        "  ],\n"
        '  "ending": "..."\n'
        "}\n\n"
        "IMPORTANT: there are only TWO top-level keys besides genre and "
        'chapters. "ending" must be its own top-level key with a plain '
        'text string value - it must NEVER be placed inside the '
        '"chapters" list, and it must never be a nested object with its '
        "own keys. The chapters list must contain ONLY chapter objects, "
        "nothing else."
    )

    max_attempts = 2
    outline = None

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            task_description += (
                "\n\nYour previous attempt produced BROKEN JSON - you "
                'put "ending" inside the chapters list instead of as '
                "its own top-level key, or you made it a nested object "
                "instead of a plain string. Fix this: \"ending\" must be "
                "a separate top-level key with a plain string value, "
                "and \"chapters\" must contain only chapter objects."
            )

        task = Task(
            description=task_description,
            expected_output="A single JSON object matching the shape described above.",
            agent=story_planner_agent
        )

        crew = Crew(
            agents=[story_planner_agent],
            tasks=[task],
            process=Process.sequential
        )

        result = crew.kickoff()
        raw_text = str(result).strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            raw_text = raw_text.replace("json", "", 1).strip()

        try:
            outline = json.loads(raw_text)
            break
        except json.JSONDecodeError:
            print(f"Attempt {attempt}: normal JSON parsing failed. Trying json-repair...")
            try:
                outline = repair_json(raw_text, return_objects=True)
                if isinstance(outline, dict) and outline:
                    print("json-repair fixed it.")
                    break
                else:
                    outline = None
            except Exception:
                outline = None

            if outline is None and attempt == max_attempts:
                print("Here is the raw text from the final attempt:")
                print(raw_text)

    return outline
