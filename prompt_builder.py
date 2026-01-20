def build_game_state_snapshot(state: dict) -> str:
    player = state["player"]
    flags = state["flags"]
    location = player["location"]

    visible_npcs = {
        name: npc
        for name, npc in state["npc_states"].items()
        if npc["location"] == location
    }

    return f"""
CURRENT LOCATION: {location}

PLAYER:
- Health: {player['health']}
- Gold: {player['gold']}
- Inventory: {player['inventory']}

FLAGS:
{flags}

QUEST:
{state['quests']['main_reliquary']}

NPCs PRESENT:
{visible_npcs}

ADJACENT LOCATIONS:
{state['world_map'][location]}

RECENT EVENTS:
{state['events'][-5:]}
""".strip()
