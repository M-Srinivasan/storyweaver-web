"""
style_guide.py

This is NOT an AI agent, and it does NOT call your Ollama server.

Its job: ask YOU directly, once, at the very start of the book, for a
few style preferences - point of view, tense, and general tone. These
get stored once in the Story Bible's metadata, and every chapter from
here on reuses them automatically. You never repeat yourself, and the
Writing Agent never has to guess your style choices.
"""


def get_style_preferences():
    """
    Asks the user a few quick questions and returns a dictionary like:

    {
        "pov": "first person" or "third person",
        "tense": "past" or "present",
        "writing_style": "..."
    }
    """

    print("\nLet's set the writing style for this book - you'll only answer this once.\n")

    print("Point of view options: 1) First person   2) Third person")
    pov_choice = input("Choose 1 or 2 (press enter for default: third person): ").strip()
    pov = "first person" if pov_choice == "1" else "third person"

    print("\nTense options: 1) Past   2) Present")
    tense_choice = input("Choose 1 or 2 (press enter for default: past): ").strip()
    tense = "present" if tense_choice == "2" else "past"

    writing_style = input(
        "\nDescribe the tone/style you want "
        "(e.g. 'dark fantasy, slow paced, George R. R. Martin feel') "
        "or press enter to skip: "
    ).strip()
    if not writing_style:
        writing_style = "clear, immersive, and genre-appropriate"

    return {
        "pov": pov,
        "tense": tense,
        "writing_style": writing_style
    }
