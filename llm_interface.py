
from dotenv import load_dotenv
load_dotenv()
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import ConversationSummaryMemory
from langchain_community.llms import OpenAI


# LLMInterface with summarization memory
class LLMInterface:
    def __init__(self, system_prompt):
        # LLM for game interaction
        self.llm = ChatOpenAI(
            model="openai/gpt-oss-120b:free",
            temperature=0.7,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "http://localhost",
                "X-Title": "Tavern Rats LLM Game"
            }
        )

        # LLM for summarization (can be the same or a smaller model)
        self.summarizer_llm = OpenAI(
            api_key=None,  # Uses env var if set
            model_name="gpt-3.5-turbo",  # Or your preferred summarizer
            temperature=0.3,
            max_tokens=256,
        )

        self.memory = ConversationSummaryMemory(
            llm=self.summarizer_llm,
            memory_key="history",
            input_key="input"
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("system", "{game_state}"),
            ("human", "{player_input}")
        ])

    def call(self, game_state: str, player_input: str, state=None) -> dict:
        # Save turn to memory and update summary
        if state is not None:
            # Add the new turn to memory
            self.memory.save_context({"input": player_input}, {"output": state.get("last_llm_text", "")})
            # Get the summarized memory
            summary = self.memory.buffer
            state["long_term_memory"] = summary
            # Optionally, keep a short window of recent turns
            state["memory"] = state.get("memory", [])[-10:]

        response = self.llm.invoke(
            self.prompt.format_messages(
                game_state=game_state,
                player_input=player_input
            )
        )

        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON from LLM:\n{response.content}") from e
