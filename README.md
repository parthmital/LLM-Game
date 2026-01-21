# Tavern Rats: The Reliquary Heist (LLM Edition)

An interactive text adventure game powered by Large Language Models (LLMs) where you play as a tavern regular caught up in a mystery surrounding the theft of a sacred relic.

## 🎮 Game Overview

Set in the medieval-noir town of Brinehook, you must investigate the disappearance of the Reliquary of Saint Kestrel. Navigate through a web of intrigue, smugglers, and town politics to recover the artifact and uncover the truth.

### Key Features

- **Dynamic NPC Interactions**: 8 unique NPCs with individual moods, locations, and secrets
- **Branching Narrative**: Your choices affect guard alert levels, reputation, and story outcomes
- **Exploration**: 17 interconnected locations across town, sewers, and forest
- **Memory System**: LLM-powered conversation summarization for coherent long-term gameplay
- **Validation System**: Ensures game state consistency and prevents invalid actions

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key (for LLM functionality)

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd "NPC LLM Game"
   ```

2. **Create virtual environment**

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Unix/macOS
   source .venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root:

   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

5. **Run the game**
   ```bash
   python main.py
   ```

## 📁 Project Structure

```
├── main.py              # Game entry point and main loop
├── game.py              # Game configuration, world state, and story
├── engine.py            # Core game logic and state management
├── llm_interface.py     # LLM integration and memory management
├── prompt_builder.py    # Game state snapshot generation
├── validator.py         # Output validation and game rules
├── utils.py             # Utility functions
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create this)
└── save.json           # Game save file (auto-generated)
```

## 🎯 Gameplay

### Starting the Game

You begin in the tavern common room with:

- Health: 100
- Gold: 3
- Empty inventory
- Main quest: Find who stole the Reliquary of Saint Kestrel

### Commands

The game accepts natural language input. Try commands like:

- `"look around"` - Examine your current location
- `"talk to bartender"` - Interact with NPCs
- `"go to town square"` - Move to adjacent locations
- `"check inventory"` - View your items
- `"ask about reliquary"` - Gather information

### Game Mechanics

**Movement**: Navigate through 17 interconnected locations following the world map adjacency rules.

**NPC System**: Each NPC has:

- Location and mood tracking
- Unique knowledge and behaviors
- Dynamic responses based on your reputation and actions

**Flag System**: Tracks game progress including:

- `guard_alert` (0-5): Town guard attention level
- `rat_reputation` (-3 to 3): Your street credibility
- Story progression flags and clue discovery

**Win/Lose Conditions**:

- **Win**: Recover the reliquary and escape to a safe public location
- **Lose**: Health reaches 0 OR guard_alert reaches 5 with no leverage

## 🧠 Technical Architecture

### LLM Integration

The game uses LangChain for LLM integration with:

- **Primary LLM**: OpenRouter's GPT-OSS-120B for game responses
- **Summarizer LLM**: GPT-3.5-Turbo for conversation memory management
- **ConversationSummaryMemory**: Maintains coherent long-term context

### State Management

- **Immutable State Design**: Uses deep copying to prevent unintended mutations
- **JSON-based Saves**: Automatic state serialization to `save.json`
- **Validation Layer**: Ensures LLM outputs follow game rules and constraints

### Core Components

1. **Engine (`engine.py`)**: Processes turns, applies state changes, manages game flow
2. **LLM Interface (`llm_interface.py`)**: Handles API calls and memory management
3. **Validator (`validator.py`)**: Enforces game rules and prevents invalid states
4. **Prompt Builder (`prompt_builder.py`)**: Creates context snapshots for LLM

## 🗺️ World Map

The game world consists of 17 locations:

**Town Areas**:

- Tavern (common room, backroom)
- Town Square
- Market
- Apothecary
- Guardhouse
- Chapel (steps, sanctuary, archive)

**Underground**:

- Alleyway
- Sewer entrance
- Sewer tunnels
- Docks warehouse basement

**Docks & Forest**:

- Docks road
- Docks
- Docks warehouse
- Forest edge
- Forest path
- Waystone clearing
- Old reliquary ruins

## 👥 NPC Characters

1. **Mara (Bartender)**: Knows rumors, hates trouble
2. **Grimbold (Bouncer)**: Loyal but not very bright
3. **Sable (Traveler)**: Courier with information for sale
4. **Voss (Hooded Figure)**: Fixer offering risky shortcuts
5. **Captain Reyne (Guard Captain)**: Can deputize or arrest you
6. **Elin (Scribe)**: Archivist who can decode sigils
7. **Nim (Apothecary)**: Knows about poisons and smugglers
8. **Krail (Smuggler Boss)**: Controls dockside operations

## 🔧 Configuration

### Game Settings

Modify `GAME_CONFIG` in `game.py` to customize:

- Story premise and tone
- Starting player stats
- NPC behaviors and locations
- World map structure
- System prompts and LLM parameters

### LLM Settings

Adjust LLM parameters in `llm_interface.py`:

- Model selection and temperature
- API endpoints and keys
- Memory configuration
- Response formatting

## 🐛 Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure your OpenAI API key is correctly set in `.env`
2. **Memory Issues**: The game automatically summarizes conversations to manage context length
3. **Invalid States**: The validator prevents game-breaking actions
4. **Save Corruption**: Delete `save.json` to restart with default state

### Debug Mode

Uncomment the traceback line in `main.py` to see full error details:

```python
traceback.print_exc()  # Remove comment for debugging
```

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Use type hints where applicable
- Document new features and functions
- Test game state changes thoroughly

## 📄 License

This project is open source. Please refer to the LICENSE file for details.

## 🙏 Acknowledgments

- Built with LangChain for LLM integration
- Powered by OpenAI and OpenRouter APIs
- Inspired by classic text adventure games
- Medieval-noir setting and original story content

---

**Enjoy your adventure in Brinehook! Remember: trust no one, watch your back, and may Saint Kestrel's luck be with you.**
