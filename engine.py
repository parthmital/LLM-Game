# import json, os, requests
# from dotenv import load_dotenv

# load_dotenv()
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# JAN_URL = "http://127.0.0.1:1337/v1/chat/completions"
# HEADERS = {
#     "Authorization": f"Bearer {OPENAI_API_KEY}",
#     "Content-Type": "application/json",
# }


# def load_state(default_state, name="save"):
#     path = f"{name}.json"
#     if os.path.exists(path):
#         with open(path, "r", encoding="utf-8") as f:
#             return json.load(f)
#     return json.loads(json.dumps(default_state))


# def save_state(state, name="save"):
#     path = f"{name}.json"
#     with open(path, "w", encoding="utf-8") as f:
#         json.dump(state, f, indent=2, ensure_ascii=False)


# def apply_state_changes(state, changes):
#     if not isinstance(changes, dict) or not changes:
#         return
#     for item in changes.get("inventory_add") or []:
#         if item not in state["player"]["inventory"]:
#             state["player"]["inventory"].append(item)
#     for item in changes.get("inventory_remove") or []:
#         if item in state["player"]["inventory"]:
#             state["player"]["inventory"].remove(item)
#     flags = changes.get("flags_set") or {}
#     if isinstance(flags, dict):
#         state["flags"].update(flags)
#     loc = changes.get("location_set")
#     if isinstance(loc, str) and loc:
#         state["player"]["location"] = loc
#     quests = changes.get("quest_update") or {}
#     if isinstance(quests, dict):
#         for q, v in quests.items():
#             state["quests"][q] = v
#     npc_moods = changes.get("npc_mood_set") or {}
#     if isinstance(npc_moods, dict):
#         for npc, mood in npc_moods.items():
#             if npc in state["npc_states"]:
#                 state["npc_states"][npc]["mood"] = mood
#     events = changes.get("world_events") or []
#     if isinstance(events, list):
#         state["events"].extend(events)



# Memory management is now handled by LangChain's ConversationSummaryMemory in llm_interface.py


# def _find_first_json_object(text):
#     s = text
#     start = s.find("{")
#     if start == -1:
#         raise json.JSONDecodeError("No JSON object found", s, 0)
#     depth = 0
#     for i in range(start, len(s)):
#         c = s[i]
#         if c == "{":
#             depth += 1
#         elif c == "}":
#             depth -= 1
#             if depth == 0:
#                 return json.loads(s[start : i + 1])
#     raise json.JSONDecodeError("Unbalanced braces", s, start)


# def _parse_llm_output(full_text):
#     raw = (full_text or "").strip()
#     if not raw:
#         return "", {}
#     try:
#         obj = _find_first_json_object(raw)
#         if isinstance(obj, dict) and ("CHANGES" in obj or "TEXT" in obj):
#             changes = obj.get("CHANGES", {}) or {}
#             llm_text = obj.get("TEXT", "") or ""
#             if not isinstance(changes, dict):
#                 changes = {}
#             if not llm_text:
#                 llm_text = raw
#             return llm_text, changes
#     except Exception:
#         pass
#     return raw, {}


# def call_llm(state, player_input):
#     user_content = f"""
# Return ONLY one valid JSON object with exactly two top-level keys:
# - "CHANGES": object
# - "TEXT": string

# No markdown, no headings, no extra keys.

# Plot: {state.get("plot","")}
# Player State: {json.dumps(state["player"],ensure_ascii=False)}
# Long-Term Memory: {state.get("long_term_memory","")}
# Player Input: {player_input}
# """.strip()
#     payload = {
#         "model": "Llama-3_2-3B-Instruct-Q4_K_M",
#         "messages": [
#             {"role": "system", "content": state.get("system_prompt", "")},
#             {"role": "user", "content": user_content},
#         ],
#         "temperature": 0.5,
#         "max_tokens": 500,
#     }
#     try:
#         resp = requests.post(JAN_URL, headers=HEADERS, json=payload, timeout=60)
#         resp.raise_for_status()
#         data = resp.json()
#         if isinstance(data, dict):
#             full_text = data["choices"][0]["message"]["content"]
#         elif isinstance(data, list):
#             if data and isinstance(data[0], dict) and "choices" in data[0]:
#                 full_text = data[0]["choices"][0]["message"]["content"]
#             else:
#                 preview = json.dumps(data, ensure_ascii=False)[:800]
#                 return f"[LLM ERROR] Unexpected JSON list response: {preview}", {}
#         else:
#             return f"[LLM ERROR] Unexpected response type: {type(data)}", {}
#         return _parse_llm_output(str(full_text))
#     except Exception as e:
#         body = ""
#         try:
#             body = resp.text[:800]
#         except Exception:
#             pass
#         return f"[LLM ERROR] {str(e)} {body}".strip(), {}


from validator import validate_llm_output

def apply_changes(state: dict, changes: dict) -> None:
    player = state["player"]

    if "inventory_add" in changes:
        player["inventory"].extend(changes["inventory_add"])

    if "inventory_remove" in changes:
        for item in changes["inventory_remove"]:
            if item in player["inventory"]:
                player["inventory"].remove(item)

    if "flags_set" in changes:
        state["flags"].update(changes["flags_set"])

    if "location_set" in changes:
        player["location"] = changes["location_set"]

    if "quest_update" in changes:
        for q, update in changes["quest_update"].items():
            state["quests"][q].update(update)

    if "npc_mood_set" in changes:
        for npc, mood in changes["npc_mood_set"].items():
            if npc in state["npc_states"]:
                state["npc_states"][npc]["mood"] = mood

    if "world_events" in changes:
        state["events"].extend(changes["world_events"])


def process_turn(state: dict, llm, game_state_text: str, player_input: str) -> str:
    # Store last LLM text for summarization
    output = llm.call(game_state_text, player_input, state=state)
    validate_llm_output(output, state)
    apply_changes(state, output["CHANGES"])
    # Store last LLM text for memory summarization
    state["last_llm_text"] = output["TEXT"]
    return output["TEXT"]
