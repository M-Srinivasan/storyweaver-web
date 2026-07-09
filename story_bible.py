import json
import os

def create_empty_story_bible():
    """
    Creates a blank story bible with every required fields
    """

    story_bible = {
        "metadata":{
            "title": "",
            "genre": "",
            "realism-tier":"",
            "pov":"",
            "tense":"",
            "writing_style":"",
        },
        "story_structure": {
            "chapters": [],
            "ending": ""
        },
        "world": {
            "world_rules": "",
            "regions": [],
            "actions":{
                "possible":[],
                "impossible": [],
                "conditional": []
            }
        },
        "characters":{
            "main" :[],
            "side": [],
            "passing": []
        },
        'timeline': {
            "current_day": 1,
            "events": []
        },
        "relationships": [],
        "plot_threads": {
            "active": [],
            "resolved": []
        },
        "memory": [],
        "chapter_summaries": []
    }

    return story_bible


def save_story_bible(story_bible, file_path = "data/story_bible.json"):
    folder = os.path.dirname(file_path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder)
    with open(file_path, 'w') as f:
        json.dump(story_bible, f, indent=4)
    
    print(f"story_bible is saved to data folder , location : {file_path},so Do whatever fuck you want")

def load_story_bible(file_path = "data/story_bible.json"):
    with open(file_path, 'r') as f:
        story_bible = json.load(f)
    
    return story_bible
