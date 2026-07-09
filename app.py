"""
app.py — Story Weaver Web Server
Serves the UI and runs the story generation pipeline in a background thread,
streaming every log line to the browser via Server-Sent Events (SSE).
"""
import json
import os
import queue
import threading
import webbrowser
from flask import Flask, render_template, request, jsonify, Response, stream_with_context

import litellm

_original_completion = litellm.completion
_original_acompletion = litellm.acompletion

def _patched_completion(*args, **kwargs):
    if "messages" in kwargs:
        for m in kwargs["messages"]:
            if "cache_breakpoint" in m:
                del m["cache_breakpoint"]
    return _original_completion(*args, **kwargs)

async def _patched_acompletion(*args, **kwargs):
    if "messages" in kwargs:
        for m in kwargs["messages"]:
            if "cache_breakpoint" in m:
                del m["cache_breakpoint"]
    return await _original_acompletion(*args, **kwargs)

litellm.completion = _patched_completion
litellm.acompletion = _patched_acompletion
# ── project modules ──────────────────────────────────────────────────────────
from story_bible import create_empty_story_bible, save_story_bible
from story_planner import plan_story
from world_builder import build_world
from character_builder import build_characters
from scene_planner import plan_scene
from context_composer import compose_context
from writing_agent import write_chapter
from story_validator import validate_chapter
from story_bible_updater import get_story_bible_updates, apply_updates
app = Flask(__name__)
# ── global state shared between the generation thread and SSE stream ─────────
_event_queue: queue.Queue = queue.Queue()
_generation_running = False
_chapters_done: list = []          # list of {"number": int, "title": str, "text": str}
_story_outline: list = []          # list of chapter dicts from planner
# ── helpers ──────────────────────────────────────────────────────────────────
def _emit(event_type: str, data):
    """Push a JSON event onto the queue for SSE delivery."""
    _event_queue.put({"type": event_type, "data": data})
def _log(msg: str):
    """Push a plain log message."""
    _emit("log", msg)
def _chapter_ready(number: int, title: str, text: str):
    """Push a finished chapter."""
    _chapters_done.append({"number": number, "title": title, "text": text})
    _emit("chapter", {"number": number, "title": title, "text": text})
# ── story generation (runs in a thread) ──────────────────────────────────────
def run_generation(form_data: dict):
    global _generation_running, _story_outline, _chapters_done
    _chapters_done = []
    _story_outline = []
    _generation_running = True
    try:
        user_description   = form_data["user_description"]
        number_of_chapters = int(form_data["number_of_chapters"])
        number_of_main     = int(form_data["number_of_main"])
        number_of_side     = int(form_data["number_of_side"])
        number_of_passing  = int(form_data["number_of_passing"])
        pov                = form_data["pov"]
        tense              = form_data["tense"]
        writing_style      = form_data.get("writing_style", "clear, immersive, and genre-appropriate") or \
                             "clear, immersive, and genre-appropriate"
        if number_of_passing > number_of_side:
            number_of_passing = number_of_side
        # ── story bible setup ─────────────────────────────────────────────────
        story_bible = create_empty_story_bible()
        story_bible["metadata"]["pov"]           = pov
        story_bible["metadata"]["tense"]         = tense
        story_bible["metadata"]["writing_style"] = writing_style
        style_info = {
            "pov": pov, "tense": tense,
            "writing_style": writing_style, "genre": ""
        }
        # ── step 1: story outline ─────────────────────────────────────────────
        _log("🗺️  Story Planner is building your outline…")
        _emit("stage", "Planning your story outline")
        outline = plan_story(user_description, number_of_chapters=number_of_chapters)
        if outline is None:
            _log("❌ Story Planner failed — try running again.")
            _emit("error", "Story Planner returned invalid JSON.")
            return
        story_bible["metadata"]["genre"]             = outline.get("genre", "")
        story_bible["story_structure"]["chapters"]   = outline.get("chapters", [])
        story_bible["story_structure"]["ending"]     = outline.get("ending", "")
        style_info["genre"]                          = outline.get("genre", "")
        _story_outline                               = outline.get("chapters", [])
        _log(f"✅ Outline done — genre: {outline.get('genre', 'unknown')}")
        _emit("outline", {
            "genre":   outline.get("genre", ""),
            "ending":  outline.get("ending", ""),
            "chapters": [
                {"number": c["chapter_number"], "title": c["title"], "synopsis": c["synopsis"]}
                for c in _story_outline
            ]
        })
        # ── step 2: world ──────────────────────────────────────────────────────
        _log("🌍  World Builder is designing your world…")
        _emit("stage", "Building the world")
        world_data = build_world(user_description, genre=story_bible["metadata"]["genre"], number_of_regions=3)
        if world_data is None:
            _log("❌ World Builder failed.")
            _emit("error", "World Builder returned invalid JSON.")
            return
        story_bible["metadata"]["realism_tier"] = world_data.get("realism_tier", "")
        story_bible["world"]["world_rules"]     = world_data.get("world_rules", [])
        story_bible["world"]["regions"]         = world_data.get("regions", [])
        story_bible["world"]["actions"]         = world_data.get("actions", {"possible": [], "impossible": [], "conditional": []})
        _log(f"✅ World built — realism: {world_data.get('realism_tier', '')}")
        # ── step 3: characters ────────────────────────────────────────────────
        _log("👥  Character Builder is creating your cast…")
        _emit("stage", "Creating characters")
        character_data = build_characters(
            user_description,
            genre=story_bible["metadata"]["genre"],
            world_rules=story_bible["world"]["world_rules"],
            conditional_actions=story_bible["world"]["actions"].get("conditional", []),
            number_of_main=number_of_main,
            number_of_side=number_of_side,
            number_of_passing=number_of_passing
        )
        if character_data is None:
            _log("❌ Character Builder failed.")
            _emit("error", "Character Builder returned invalid JSON.")
            return
        story_bible["characters"]["main"]    = character_data.get("main", [])
        story_bible["characters"]["side"]    = character_data.get("side", [])
        story_bible["characters"]["passing"] = character_data.get("passing", [])
        main_names = [c.get("name") for c in story_bible["characters"]["main"]]
        _log(f"✅ Characters created — main cast: {', '.join(main_names)}")
        # shared lists
        all_character_names = (
            [c.get("name") for c in story_bible["characters"]["main"]]
            + [c.get("name") for c in story_bible["characters"]["side"]]
            + [c.get("name") for c in story_bible["characters"]["passing"]]
        )
        all_region_names = [r.get("name") for r in story_bible["world"]["regions"]]
        os.makedirs("data", exist_ok=True)
        chapters = story_bible["story_structure"]["chapters"]
        total    = len(chapters)
        previous_chapter_ending = None
        # ── step 4: chapter loop ──────────────────────────────────────────────
        for idx, chapter in enumerate(chapters, 1):
            chapter_num = chapter["chapter_number"]
            chapter_title = chapter["title"]
            _emit("stage", f"Writing Chapter {chapter_num} of {total}: {chapter_title}")
            _log(f"\n📖  Chapter {chapter_num}/{total}: {chapter_title}")
            # scene planning
            _log(f"   🔭 Scene Planner is mapping chapter {chapter_num}…")
            scene_blueprint = plan_scene(
                chapter, all_character_names, all_region_names,
                previous_chapter_ending=previous_chapter_ending
            )
            if scene_blueprint is None:
                _log(f"   ⚠️  Scene Planner failed for chapter {chapter_num} — skipping.")
                continue
            context_package = compose_context(scene_blueprint, story_bible)
            # write + validate loop
            max_attempts  = 4
            chapter_text  = None
            failure_notes = None
            for attempt in range(1, max_attempts + 1):
                _log(f"   ✍️  Writing attempt {attempt}…")
                chapter_text = write_chapter(
                    chapter, scene_blueprint, context_package,
                    style_info, failure_notes=failure_notes,
                    previous_chapter_ending=previous_chapter_ending
                )
                _log(f"   🔍 Validating attempt {attempt}…")
                validation_result = validate_chapter(
                    chapter_text, scene_blueprint, context_package,
                    previous_chapter_ending=previous_chapter_ending
                )
                if validation_result is None:
                    _log("   ✅ Validator skipped (no JSON) — accepting.")
                    break
                if validation_result.get("pass"):
                    _log("   ✅ Validator passed.")
                    break
                else:
                    failures = validation_result.get("failures", [])
                    _log(f"   ❌ Validator failed ({len(failures)} issue(s)):")
                    for f in failures:
                        _log(f"      • {f.get('type')}: {f.get('detail')}")
                    failure_notes = [f"{f.get('type')}: {f.get('detail')}" for f in failures]
                    if attempt == max_attempts:
                        _log("   ⚠️  Max attempts reached — saving best effort.")
            # save to disk
            chapter_filename = f"data/chapter_{chapter_num}.txt"
            with open(chapter_filename, "w", encoding="utf-8") as file_out:
                file_out.write(chapter_text)
            # extract handoff
            if chapter_text:
                words = chapter_text.split()
                previous_chapter_ending = " ".join(words[-400:]) if len(words) > 400 else chapter_text
            # push chapter to UI
            _chapter_ready(chapter_num, chapter_title, chapter_text)
            _log(f"   💾 Chapter {chapter_num} saved.")
            # update story bible
            _log(f"   📚 Updating Story Bible…")
            updates = get_story_bible_updates(chapter_text, scene_blueprint, story_bible)
            if updates:
                story_bible = apply_updates(story_bible, updates)
            save_story_bible(story_bible)
        _emit("done", {"total_chapters": total})
        _log(f"\n🎉 All {total} chapters complete! Your story is ready.")
    except Exception as exc:
        _log(f"❌ Unexpected error: {exc}")
        _emit("error", str(exc))
    finally:
        _generation_running = False
# ── Flask routes ──────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")
@app.route("/generate", methods=["POST"])
def generate():
    global _generation_running
    if _generation_running:
        return jsonify({"error": "Generation already in progress."}), 409
    form_data = request.get_json(force=True)
    # clear queue
    while not _event_queue.empty():
        try:
            _event_queue.get_nowait()
        except queue.Empty:
            break
    thread = threading.Thread(target=run_generation, args=(form_data,), daemon=True)
    thread.start()
    return jsonify({"status": "started"})
@app.route("/stream")
def stream():
    """SSE endpoint — browser listens here for live events."""
    def event_generator():
        yield "retry: 1000\n\n"          # reconnect interval
        while True:
            try:
                event = _event_queue.get(timeout=30)
                payload = json.dumps(event)
                yield f"data: {payload}\n\n"
                if event.get("type") in ("done", "error"):
                    break
            except queue.Empty:
                yield ": keep-alive\n\n"  # prevent connection drop
    return Response(
        stream_with_context(event_generator()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
@app.route("/chapters")
def get_chapters():
    return jsonify(_chapters_done)
@app.route("/status")
def status():
    return jsonify({"running": _generation_running})
# ── entry point ───────────────────────────────────────────────────────────────
def start_server(host="127.0.0.1", port=5000, open_browser=True):
    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    app.run(host=host, port=port, debug=False, threaded=True)
if __name__ == "__main__":
    start_server()
