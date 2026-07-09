"""
Its ONLY job: take the Scene Blueprint (what should happen) and the
Context Package (the real facts it's allowed to use) and turn that into
an actual chapter of writing.
"""

from langchain_groq import ChatGroq
from crewai import Agent, Task, Crew, LLM
from crewai.process import Process


# ---- 1. Connect to your Ollama server ----
import os

# Old setup (commented out):
# llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.environ.get("GROQ_API_KEY", "")
)


# ---- 2. Define the agent ----
writing_agent = Agent(
    role="Writing Agent",
    goal="Turn a scene blueprint and its facts into engaging, well-written prose",
    backstory=(
        "You are a skilled novelist. You are given exactly what happens "
        "in this scene, which characters are in it, where it takes "
        "place, and what world rules apply. You never invent characters, "
        "places, or facts that were not given to you. You write "
        "immersive, professional prose - showing emotion and action, "
        "not just stating facts."
    ),
    llm=llm,
    verbose=True
)


def write_chapter(chapter_info, scene_blueprint, context_package, style_info,
                  failure_notes=None, previous_chapter_ending=None):

    character_lines = []
    for character in context_package.get("characters", []):
        character_lines.append(
            f"- {character.get('name')}: appearance = {character.get('appearance_tags')}, "
            f"behavior = {character.get('behavior_tags')}"
        )
    character_text = "\n".join(character_lines) if character_lines else "No characters provided."

    location = context_package.get("location", {})
    location_text = (
        f"{location.get('name')} - {location.get('terrain', '')}. "
        f"Signature location: {location.get('signature_location', 'none')}"
    )

    world_rules_text = "\n".join(
        f"- {rule}" for rule in context_package.get("world_rules", [])
    ) or "No specific world rules given."

    pov = style_info.get("pov") or "third person"
    tense = style_info.get("tense") or "past"
    writing_style = style_info.get("writing_style") or "clear, immersive, and genre-appropriate"
    genre = style_info.get("genre") or "general fiction"

    failure_notes_text = ""
    if failure_notes:
        failure_notes_text = (
            "\nIMPORTANT - your previous attempt at this chapter had "
            "these problems, fix them this time:\n"
            + "\n".join(f"- {note}" for note in failure_notes)
            + "\n"
        )

    # Build the continuity bridge block
    if previous_chapter_ending:
        continuity_text = (
            "CONTINUITY — the previous chapter ended with these exact words:\n"
            "---\n"
            f"{previous_chapter_ending}\n"
            "---\n"
            "You MUST begin this chapter so that it flows naturally and "
            "directly from the passage above. Keep the same character "
            "names, the same location, and carry forward their emotional "
            "state. Do not teleport characters to a new place or invent "
            "events that bridge the gap — write the continuation as if "
            "the reader just finished reading those lines.\n\n"
        )
    else:
        continuity_text = ""

    task = Task(
        description=(
            f"{continuity_text}"
            f"Write Chapter {chapter_info['chapter_number']}: {chapter_info['title']}\n\n"
            f"Chapter synopsis (what this chapter is broadly about): "
            f"{chapter_info['synopsis']}\n\n"
            f"Scene objective: {scene_blueprint.get('objective')}\n"
            f"Conflict: {scene_blueprint.get('conflict')}\n"
            f"Emotional direction: {scene_blueprint.get('emotion')}\n"
            f"Ending condition (the scene must end at this point): "
            f"{scene_blueprint.get('ending_condition')}\n\n"
            f"Characters allowed in this scene (do not add others):\n{character_text}\n\n"
            f"Location:\n{location_text}\n\n"
            f"World rules that must never be broken:\n{world_rules_text}\n\n"
            f"Genre: {genre}\n"
            f"Point of view: {pov}\n"
            f"Tense: {tense}\n"
            f"Writing style: {writing_style}\n"
            f"{failure_notes_text}\n"
            "Write the full chapter now. Do not invent characters, "
            "locations, or facts beyond what was given above. Do not "
            "include any notes, explanations, or headers - just the "
            "chapter's prose."
        ),
        expected_output="The full text of the chapter, ready to read.",
        agent=writing_agent
    )

    crew = Crew(
        agents=[writing_agent],
        tasks=[task],
        process=Process.sequential
    )

    result = crew.kickoff()

    chapter_text = str(result).strip()
    return chapter_text
