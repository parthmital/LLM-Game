ALLOWED_CHANGE_KEYS = {
    "inventory_add",
    "inventory_remove",
    "flags_set",
    "location_set",
    "quest_update",
    "npc_mood_set",
    "world_events",
}

def validate_llm_output(output: dict, state: dict) -> None:
    if not isinstance(output, dict):
        raise ValueError("Output is not a dict")

    if set(output.keys()) != {"TEXT", "CHANGES"}:
        raise ValueError("Output must have only TEXT and CHANGES")

    changes = output["CHANGES"]

    for key in changes:
        if key not in ALLOWED_CHANGE_KEYS:
            raise ValueError(f"Illegal change key: {key}")

    # Movement validation
    if "location_set" in changes:
        current = state["player"]["location"]
        target = changes["location_set"]
        if target not in state["world_map"][current]:
            raise ValueError("Illegal movement")

    # Flag validation (defensive!)
    if "flags_set" in changes:
        for k, v in changes["flags_set"].items():
            if k == "guard_alert":
                if not isinstance(v, int) or not (0 <= v <= 5):
                    raise ValueError("guard_alert out of range")

            if k == "rat_reputation":
                if not isinstance(v, int) or not (-3 <= v <= 3):
                    raise ValueError("rat_reputation out of range")
