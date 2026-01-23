# Tavern Rats: The Reliquary Heist (LLM Edition)

A text adventure game implementing a Large Language Model-driven narrative system with state management, NPC interaction, and dynamic story progression.

## Technical Architecture

### Core System Design

The game implements a turn-based text adventure engine with LLM-powered narrative generation. The architecture follows a modular design pattern with clear separation of concerns between game logic, LLM integration, and state validation.

### State Management System

**Immutable State Architecture**: The game uses deep copying to prevent unintended state mutations. All state changes are applied through validated operations that ensure game rule compliance.

**State Structure**:

- `player`: Health, location, inventory, gold, strength
- `flags`: Binary and numerical flags tracking game progression
- `npc_states`: Individual NPC states including mood, location, and metadata
- `quests`: Quest tracking with stage progression
- `world_map`: Adjacency graph defining movement constraints
- `events`: Chronological event log for context
- `memory`: Short-term conversation history
- `long_term_memory`: LLM-summarized conversation context

### LLM Integration Framework

**Dual-LLM Architecture**:

- Primary LLM: OpenRouter GPT-OSS-120B for narrative generation
- Summarizer LLM: GPT-3.5-Turbo for memory compression

**LangChain Integration**:

- `ConversationSummaryMemory` for context management
- `ChatPromptTemplate` for structured prompt formatting
- JSON-based response parsing with validation

**Memory Management**:

- Automatic conversation summarization to maintain context within token limits
- Rolling window of recent turns (10-turn retention)
- Persistent long-term memory storage across game sessions

### Game Engine Components

**Main Loop (`main.py`)**:

- Game initialization and state loading
- Turn processing pipeline
- Error handling and graceful degradation
- End condition detection

**Engine Core (`engine.py`)**:

- `process_turn()`: Primary turn processing function
- `apply_changes()`: State mutation with validation
- Integration with LLM interface and validator

**LLM Interface (`llm_interface.py`)**:

- `LLMInterface` class encapsulating API communication
- Dual-LLM configuration and management
- Memory context integration
- JSON response parsing with error handling

**Prompt Builder (`prompt_builder.py`)**:

- `build_game_state_snapshot()`: Context generation
- Dynamic NPC visibility filtering
- Location-aware context assembly
- Event history truncation

**Validator (`validator.py`)**:

- `validate_llm_output()`: Response validation
- Movement constraint enforcement
- Flag range validation
- Change key whitelisting

### Game World Implementation

**Location System**: 17 interconnected locations with adjacency constraints:

- Town areas (tavern, square, market, apothecary, guardhouse, chapel)
- Underground areas (alleyway, sewers, warehouse basement)
- Docks and forest regions

**NPC System**: 8 NPCs with individual state tracking:

- Location-based presence detection
- Mood state management
- Interaction history tracking
- Behavioral metadata storage

**Quest System**: Multi-stage quest tracking with:

- Stage progression monitoring
- Objective completion detection
- Failure state handling
- Conditional branching

### Data Structures and Algorithms

**World Representation**: Adjacency list graph for location connectivity
**State Validation**: Whitelist-based change validation with range checking
**Memory Compression**: LLM-based summarization for context management
**Event Logging**: Append-only event storage with truncation

### Configuration System

**Game Configuration (`game.py`)**:

- `GAME_CONFIG`: Central configuration dictionary
- Starting state definition
- NPC behavior parameters
- World map structure
- System prompts and narrative parameters

**LLM Configuration**:

- Model selection and parameters
- API endpoint configuration
- Memory management settings
- Response formatting rules

### Error Handling and Validation

**Validation Layer**:

- Response structure validation (TEXT/CHANGES format)
- Movement constraint enforcement
- Flag range validation (guard_alert: 0-5, rat_reputation: -3 to 3)
- Change key whitelisting

**Error Recovery**:

- Graceful degradation on LLM failures
- State rollback on invalid changes
- Debug mode with full tracebacks
- Save corruption recovery

### Performance Considerations

**Memory Management**:

- Automatic summarization to prevent context overflow
- Event history truncation (last 5 events)
- Recent turn window management (10 turns)

**State Optimization**:

- Deep copying for immutability
- JSON serialization for persistence
- Efficient state diff application

## Implementation Details

### Turn Processing Pipeline

1. **Context Generation**: Build game state snapshot with visible NPCs, adjacent locations, and recent events
2. **LLM Invocation**: Send formatted prompt to primary LLM with memory context
3. **Response Validation**: Validate JSON structure and change constraints
4. **State Application**: Apply validated changes to game state
5. **Memory Update**: Store turn in conversation memory and update summary

### Movement System

Movement is constrained by the adjacency graph defined in `world_map`. The validator ensures that location changes are only allowed between connected nodes, preventing invalid teleportation.

### NPC Interaction System

NPCs are dynamically filtered based on player location. Each NPC maintains individual state including mood, interaction history, and behavioral metadata that influences LLM responses.

### Quest Progression

Quests are tracked through stage-based progression with completion and failure states. The main quest follows a linear progression through clue discovery and investigation phases.

## File Structure and Organization

```
main.py              # Entry point and main game loop
engine.py            # Core game logic and state management
llm_interface.py     # LLM integration and memory management
prompt_builder.py    # Context snapshot generation
validator.py         # Output validation and rule enforcement
game.py              # Game configuration and world definition
utils.py             # Utility functions
requirements.txt     # Python dependencies
```

## Dependencies and External APIs

**Core Dependencies**:

- `langchain-openai`: LLM integration
- `langchain-core`: Prompt templates and memory
- `langchain-community`: Community LLM implementations
- `python-dotenv`: Environment variable management

**External APIs**:

- OpenRouter API for primary LLM access
- OpenAI API for summarization LLM
- Environment-based API key management

## Data Persistence

Game state is automatically serialized to JSON format for persistence. The save system maintains complete game state including all flags, NPC states, quest progress, and memory context.
