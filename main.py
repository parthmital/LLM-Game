from game import GAME_CONFIG
from engine import load_state, save_state, add_memory, call_llm, apply_state_changes

state = load_state(GAME_CONFIG["starting_state"])
state["system_prompt"] = GAME_CONFIG["system_prompt"]
turn_counter = 0
auto_save_interval = 5
print(GAME_CONFIG["title"])
print("Type 'quit' to exit.\n")
while True:
    user_input = input("> ").strip()
    if not user_input:
        continue
    if user_input.lower() == "quit":
        save_state(state)
        break
    llm_text, changes = call_llm(state, user_input)
    apply_state_changes(state, changes)
    print(llm_text)
    add_memory(state, user_input, llm_text)
    turn_counter += 1
    if turn_counter % auto_save_interval == 0:
        save_state(state)
