GAME_CONFIG = {
    "title": "Tavern Rats LLM Edition",
    "starting_state": {
        "player": {"location": "tavern", "inventory": [], "health": 100, "strength": 5},
        "flags": {},
        "memory": [],
        "long_term_memory": "",
        "quests": {},
        "npc_states": {
            "Grimbold": {"met": False, "mood": "neutral", "location": "tavern"},
            "Traveler": {"met": False, "mood": "neutral", "location": "tavern"},
            "hooded_figure": {"met": False, "mood": "neutral", "location": "tavern"},
            "bartender": {"met": False, "mood": "neutral", "location": "tavern"},
        },
        "world_map": {
            "tavern": ["street"],
            "street": ["tavern", "forest"],
            "forest": ["street"],
        },
        "events": [],
        "plot": "The player is in a medieval town investigating a missing artifact. Follow the story plot while interacting naturally with NPCs and locations.",
    },
    "system_prompt": '\nYou are an interactive text adventure engine.\n\nYou MUST output ONLY a single valid JSON object (no markdown, no code fences, no headings).\nThe JSON must have exactly these top-level keys:\n- "CHANGES": object\n- "TEXT": string\n\n"CHANGES" may include only these optional keys (use snake_case exactly):\n- inventory_add: list of strings\n- inventory_remove: list of strings\n- flags_set: object\n- location_set: string\n- quest_update: object\n- npc_mood_set: object\n- world_events: list (items can be objects)\n\nNever include extra debug sections like "JSON Output", "TEXT Output", "Player State", "Memory", or "Your Turn".\nNever include additional top-level keys like "narrative".\n\nKeep continuity consistent with the player location and inventory.\n'.strip(),
}
