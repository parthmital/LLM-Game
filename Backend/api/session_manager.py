"""Session lifecycle and orchestration for isolated game instances."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import config
from core.event_store import EventStore
from core.reducer import rebuild_state
from core.snapshot import load_snapshot, save_snapshot
from game.world_loader import load_world_seed
from graph.definition import TurnState, build_graph
from llm.groq_client import GroqClient
from memory.embedder import Embedder
from memory.faiss_index import FAISSMemory
from memory.short_term import ShortTermMemory
from schemas.events import Event, EventType

log = logging.getLogger(__name__)


class GameSession:
    """All mutable runtime state for a single game session."""

    __slots__ = (
        "session_id",
        "created_at",
        "world",
        "graph",
        "store",
        "faiss_mem",
        "short_term",
        "active_npc_id",
        "data_dir",
        "_lock",
        "ws_connections",
        "dialogue_history",
    )

    def __init__(
        self,
        session_id: str,
        world: Any,
        graph: Any,
        store: EventStore,
        faiss_mem: FAISSMemory,
        short_term: ShortTermMemory,
        active_npc_id: Optional[str],
        data_dir: Path,
    ):
        self.session_id = session_id
        self.created_at = time.time()
        self.world = world
        self.graph = graph
        self.store = store
        self.faiss_mem = faiss_mem
        self.short_term = short_term
        self.active_npc_id = active_npc_id
        self.data_dir = data_dir
        self._lock = asyncio.Lock()
        self.ws_connections: Set[Any] = set()
        self.dialogue_history: list = []

    def close(self) -> None:
        """Persist and release session resources."""
        try:
            self.faiss_mem.save()
            self.store.close()
        except Exception as exc:
            log.error("Error closing session %s: %s", self.session_id, exc)


class SessionManager:
    """Creates, stores, retrieves, and destroys game sessions."""

    def __init__(self):
        self._sessions: Dict[str, GameSession] = {}
        self._embedder: Optional[Embedder] = None
        self._client: Optional[GroqClient] = None
        self._seed = None
        self._initialised = False
        self._init_lock = asyncio.Lock()

    async def _ensure_init(self) -> None:
        if self._initialised:
            return
        async with self._init_lock:
            if self._initialised:
                return

            log.info("Initialising shared game resources...")
            loop = asyncio.get_running_loop()
            self._seed = await loop.run_in_executor(
                None, load_world_seed, config.WORLD_SEED_PATH
            )
            self._embedder = await loop.run_in_executor(
                None,
                lambda: Embedder(
                    config.EMBEDDING_MODEL,
                    config.EMBED_CACHE_PATH,
                    config.EMBEDDING_DIM,
                ),
            )
            self._client = GroqClient(
                model=config.MODEL_NAME,
                api_key=config.GROQ_API_KEY,
                timeout=config.REQUEST_TIMEOUT,
            )
            if self._embedder:
                await loop.run_in_executor(
                    None, self._embedder.embed, config.EMBEDDING_WARMUP_TEXT
                )
                log.info("Embedding model warmed up.")

            self._initialised = True
            log.info("Shared resources ready.")

    async def create_session(
        self,
        name: str,
        gender: str,
        age: int,
        occupation: str,
        reset: bool = False,
    ) -> GameSession:
        await self._ensure_init()

        if len(self._sessions) >= config.MAX_CONCURRENT_SESSIONS:
            raise RuntimeError(
                f"Maximum concurrent sessions ({config.MAX_CONCURRENT_SESSIONS}) reached"
            )

        session_id = str(uuid.uuid4())
        data_dir = config.DATA_DIR / "sessions" / session_id
        data_dir.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_running_loop()

        def _create():
            store = EventStore(data_dir / config.EVENTS_DB_FILENAME)
            world = self._seed.model_copy(deep=True)

            world.player.name = name
            world.player.gender = gender
            world.player.age = age
            world.player.occupation = occupation
            world.player.moral_alignment = config.INITIAL_MORAL_ALIGNMENT

            store.append(Event(turn=0, event_type=EventType.SESSION_START, payload={}))

            faiss_mem = FAISSMemory(
                data_dir / config.FAISS_INDEX_FILENAME,
                data_dir / config.FAISS_META_FILENAME,
                config.EMBEDDING_DIM,
            )
            short_term = ShortTermMemory(config.MAX_SHORT_TERM_TURNS)

            graph = build_graph(
                store,
                self._embedder,
                faiss_mem,
                short_term,
                self._client,
                snapshot_path=data_dir / config.SNAPSHOT_AUTO_FILENAME,
            )

            world.active_npc_id = None

            return GameSession(
                session_id=session_id,
                world=world,
                graph=graph,
                store=store,
                faiss_mem=faiss_mem,
                short_term=short_term,
                active_npc_id=None,
                data_dir=data_dir,
            )

        session = await loop.run_in_executor(None, _create)
        self._sessions[session_id] = session

        if (
            self._seed
            and hasattr(self._seed, "metadata")
            and self._seed.metadata.initial_narrator_message
        ):
            session.dialogue_history.append(
                {
                    "id": f"init_{int(time.time() * 1000)}",
                    "type": "narration",
                    "speaker": "Narrator",
                    "content": self._seed.metadata.initial_narrator_message,
                    "timestamp": time.time() * 1000,
                }
            )

        await self.save_session(session_id, is_auto=True)

        log.info(
            "Session created: %s (Player: %s, NPC: %s)",
            session_id,
            name,
            session.active_npc_id,
        )
        return session

    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions saved on disk."""
        sessions_dir = config.DATA_DIR / "sessions"
        if not sessions_dir.exists():
            return []

        results = []
        for session_dir in sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue

            for save_type in ["manual", "auto"]:
                snapshot_name = (
                    config.SNAPSHOT_FILENAME
                    if save_type == "manual"
                    else config.SNAPSHOT_AUTO_FILENAME
                )
                snapshot_path = session_dir / snapshot_name
                if not snapshot_path.exists():
                    continue

                try:
                    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
                    world = data["world_state"]
                    loc_id = world["player"]["current_location_id"]
                    loc_name = world["locations"].get(loc_id, {}).get("name", loc_id)

                    results.append(
                        {
                            "session_id": f"{session_dir.name}:{save_type}",
                            "player_name": world["player"]["name"],
                            "location_name": loc_name,
                            "turn": world["turn"],
                            "created_at": snapshot_path.stat().st_mtime,
                            "is_auto": save_type == "auto",
                        }
                    )
                except Exception:
                    log.warning("Skipping corrupt snapshot: %s", snapshot_path)

        return sorted(results, key=lambda item: item["created_at"], reverse=True)

    async def load_session(self, session_id: str) -> Optional[GameSession]:
        """Load a session save from disk."""
        save_type = "manual"
        original_id = session_id
        if ":" in session_id:
            original_id, save_type = session_id.split(":", 1)

        if original_id in self._sessions:
            self._sessions.pop(original_id).close()

        await self._ensure_init()
        data_dir = config.DATA_DIR / "sessions" / original_id
        if not data_dir.exists():
            return None

        snapshot_name = (
            config.SNAPSHOT_FILENAME
            if save_type == "manual"
            else config.SNAPSHOT_AUTO_FILENAME
        )
        dialogue_name = (
            config.DIALOGUE_FILENAME
            if save_type == "manual"
            else config.DIALOGUE_AUTO_FILENAME
        )
        snapshot_path = data_dir / snapshot_name
        dialogue_path = data_dir / dialogue_name

        loop = asyncio.get_running_loop()

        def _load():
            store = EventStore(data_dir / config.EVENTS_DB_FILENAME)
            snap = load_snapshot(snapshot_path)
            if snap:
                world, _last_id = snap
            else:
                world = self._seed.model_copy(deep=True)
                world = rebuild_state(world, store.load_all())

            faiss_mem = FAISSMemory(
                data_dir / config.FAISS_INDEX_FILENAME,
                data_dir / config.FAISS_META_FILENAME,
                config.EMBEDDING_DIM,
            )
            short_term = ShortTermMemory(config.MAX_SHORT_TERM_TURNS)

            graph = build_graph(
                store,
                self._embedder,
                faiss_mem,
                short_term,
                self._client,
                snapshot_path=data_dir / config.SNAPSHOT_AUTO_FILENAME,
            )

            npc_id = world.active_npc_id or next(iter(world.npcs.keys()), None)

            dialogue_history = []
            if dialogue_path.exists():
                try:
                    dialogue_history = json.loads(
                        dialogue_path.read_text(encoding="utf-8")
                    )
                except Exception:
                    log.warning("Skipping corrupt dialogue history: %s", dialogue_path)

            session = GameSession(
                session_id=original_id,
                world=world,
                graph=graph,
                store=store,
                faiss_mem=faiss_mem,
                short_term=short_term,
                active_npc_id=npc_id,
                data_dir=data_dir,
            )
            session.dialogue_history = dialogue_history
            return session

        try:
            session = await loop.run_in_executor(None, _load)
            self._sessions[original_id] = session
            return session
        except Exception as exc:
            log.error("Failed to load session %s: %s", session_id, exc)
            return None

    def get_session(self, session_id: str) -> Optional[GameSession]:
        original_id = session_id.split(":", 1)[0]
        return self._sessions.get(original_id)

    def destroy_session(self, session_id: str) -> bool:
        original_id = session_id.split(":", 1)[0]
        session = self._sessions.pop(original_id, None)
        if session is None:
            return False
        session.close()
        log.info("Session destroyed: %s", original_id)
        return True

    async def save_session(self, session_id: str, is_auto: bool = False) -> bool:
        """Persist session state to disk."""
        session = self.get_session(session_id)
        if not session:
            return False

        loop = asyncio.get_running_loop()

        def _save():
            session.faiss_mem.save()
            last_id = session.store.get_last_id()

            snapshot_name = (
                config.SNAPSHOT_AUTO_FILENAME if is_auto else config.SNAPSHOT_FILENAME
            )
            save_snapshot(session.world, session.data_dir / snapshot_name, last_id)

            dialogue_name = (
                config.DIALOGUE_AUTO_FILENAME if is_auto else config.DIALOGUE_FILENAME
            )
            with open(session.data_dir / dialogue_name, "w", encoding="utf-8") as f:
                json.dump(session.dialogue_history, f, ensure_ascii=False)

        await loop.run_in_executor(None, _save)
        return True

    async def process_action(
        self, session: GameSession, player_input: str, npc_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a player action through the LangGraph pipeline."""
        async with session._lock:
            active_npc = npc_id or session.active_npc_id

            turn_state: TurnState = {
                "player_input": player_input,
                "active_npc_id": active_npc,
                "world": session.world,
                "query_vec": None,
                "retrieved_memories": [],
                "prompt": "",
                "raw_llm_output": "",
                "parsed_output": None,
                "valid_events": [],
                "validation_errors": [],
                "narration": "",
                "npc_dialogue": "",
                "turn_errors": [],
                "elapsed_ms": 0.0,
            }

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, session.graph.invoke, turn_state)

            session.world = result["world"]
            session.active_npc_id = result.get("active_npc_id", active_npc)
            session.world.active_npc_id = session.active_npc_id

            trust_change = 0
            events_out = []
            for event in result.get("valid_events", []):
                events_out.append(
                    {
                        "type": event.event_type.value,
                        "payload": event.payload,
                    }
                )
                if (
                    event.event_type == EventType.RELATIONSHIP_CHANGED
                    and event.payload.get("target_id") == "player"
                ):
                    trust_change += int(event.payload.get("delta", 0))

            parsed = result.get("parsed_output")
            speaker_id = active_npc
            if parsed and parsed.speaker_id:
                speaker_id = parsed.speaker_id

            npc_obj = session.world.npcs.get(speaker_id)
            if speaker_id == "narrator":
                npc_name = "Narrator"
            else:
                npc_name = npc_obj.name if npc_obj else speaker_id

            return {
                "npc_dialogue": result.get("npc_dialogue", ""),
                "narration": result.get("narration", ""),
                "npc_id": speaker_id,
                "npc_name": npc_name,
                "turn": session.world.turn,
                "trust_change": trust_change,
                "validation_errors": result.get("validation_errors", []),
                "elapsed_ms": result.get("elapsed_ms", 0.0),
                "events": events_out,
            }

    @property
    def active_session_count(self) -> int:
        return len(self._sessions)

    @property
    def is_ready(self) -> bool:
        return self._initialised

    def ping_llm(self) -> bool:
        if self._client:
            return self._client.ping()
        return False

    async def shutdown(self) -> None:
        """Close all sessions on server shutdown."""
        for session_id in list(self._sessions.keys()):
            self.destroy_session(session_id)
        if self._embedder:
            self._embedder.close()
        log.info("Session manager shut down.")
