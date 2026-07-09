from langchain_groq import ChatGroq
from crewai import Agent, Task, Crew, LLM
from crewai.process import Process
from json_repair import repair_json
import json

# ---- 1. Connect to your Ollama server ----
import os

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.environ.get("GROQ_API_KEY", "")
)

# ---- 2. Define the agent ----
story_validator_agent = Agent(
    role="Story Validator",
    goal="Check a written chapter against the facts it was supposed to follow",
    backstory=(
        "You are a strict continuity and world-rule checker for novels. "
        "You never rewrite or fix anything yourself - you only report "
        "whether a chapter passes or fails, and exactly why, so someone "
        "else can fix it."
    ),
    llm=llm,
    verbose=True
)

def validate_chapter(chapter_text, scene_blueprint, context_package, previous_chapter_ending=None):
    allowed_characters = []
    for character in context_package.get("characters", []):
        allowed_characters.append({
            "name": character.get("name"),
            "behavior_tags": character.get("behavior_tags", []),
            "justifications": character.get("justifications", [])
        })

    # Build optional continuity check block
    if previous_chapter_ending:
        continuity_check = (
            f"The previous chapter ended with this passage:\n"
            f"---\n{previous_chapter_ending}\n---\n"
            "Also check for:\n"
            "5. continuity_break - a character's name suddenly changes "
            "between the previous chapter ending and this chapter, OR "
            "a character appears in a completely different location with "
            "no plausible explanation, OR a major event from the previous "
            "chapter (fight, injury, decision) is completely ignored with "
            "no acknowledgement.\n"
            "Flag continuity_break only for clear, obvious breaks — not "
            "for small stylistic differences.\n\n"
        )
    else:
        continuity_check = ""

    task = Task(
        description=(
            f"Here is the chapter that was written:\n\n{chapter_text}\n\n"
            f"Here is what the chapter was SUPPOSED to do:\n"
            f"Objective: {scene_blueprint.get('objective')}\n"
            f"Ending condition (must be reached by the end): "
            f"{scene_blueprint.get('ending_condition')}\n\n"
            f"Characters allowed, with their normal traits and any "
            f"justifications on file for special skills:\n{allowed_characters}\n\n"
            f"World rules that must never be broken:\n"
            f"{context_package.get('world_rules', [])}\n\n"
            f"{continuity_check}"
            "Check the chapter for these problems ONLY:\n"
            "1. unjustified_action - a character uses magic, a "
            "supernatural ability, or a superhuman physical feat that "
            "is NOT covered by any entry in their justifications list. "
            "Do NOT flag normal human emotions, personality growth, or "
            "ordinary behavior (feeling guilt, changing their mind, "
            "showing a new emotion) as unjustified - behavior_tags "
            "describe a character's general personality, not an "
            "exhaustive list of every emotion they are allowed to have.\n"
            "2. world_rule_violation - the chapter clearly and "
            "directly contradicts one of the world rules above.\n"
            "3. missing_ending - the chapter does not move toward the "
            "ending condition AT ALL. If the chapter makes real "
            "progress toward it, even partially or implicitly, this "
            "does NOT count as a failure - only flag this if the "
            "chapter ignores the ending condition completely.\n"
            "4. unauthorized_character - the chapter includes a named "
            "character who is not in the allowed list above.\n\n"
            "Be lenient. If you are unsure whether something is a "
            "real problem, do not flag it - only report clear, "
            "obvious issues.\n\n"
            "Respond with ONLY valid JSON, no extra text, no markdown "
            "formatting, in exactly this shape:\n"
            "{\n"
            '  "pass": true,\n'
            '  "failures": [\n'
            '    {"type": "...", "detail": "..."}\n'
            "  ]\n"
            "}\n"
            'If there are no problems, return "pass": true and an empty '
            "failures list."
        ),
        expected_output="A single JSON object matching the shape described above.",
        agent=story_validator_agent
    )

    crew = Crew(
        agents=[story_validator_agent],
        tasks=[task],
        process=Process.sequential
    )

    result = crew.kickoff()

    raw_text = str(result).strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json", "", 1).strip()

    try:
        validation_result = json.loads(raw_text)
    except json.JSONDecodeError:
        print("Normal JSON parsing failed. Trying json-repair...")
        try:
            validation_result = repair_json(raw_text, return_objects=True)
            if not (isinstance(validation_result, dict) and validation_result):
                validation_result = None
        except Exception:
            validation_result = None

        if validation_result is None:
            print("Could not read the AI's response as JSON. Here is the raw text:")
            print(raw_text)

    return validation_result
