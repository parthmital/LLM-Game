"""REST and WebSocket routes for the NPC Engine API."""

from __future__ import annotations

import json
import logging
import time
from typing import List, Optional

import config
from api.presenters import (
    build_game_state_response,
    build_location_info,
    build_npc_info,
)
from api.schemas import (
    ActionResponse,
    CreateSessionRequest,
    GameMetadataResponse,
    GameStateResponse,
    HealthResponse,
    LinkCluesRequest,
    LocationInfo,
    MoveRequest,
    NPCListResponse,
    PlayerActionRequest,
    SaveInfo,
    SessionInfo,
    WSOutMessage,
)
from api.session_manager import SessionManager
from core.reducer import apply_event
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from schemas.events import Event, EventType

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/game", tags=["game"])
ws_router = APIRouter(tags=["websocket"])

_sm: Optional[SessionManager] = None


def set_session_manager(sm: SessionManager) -> None:
    global _sm
    _sm = sm


def _get_sm() -> SessionManager:
    if _sm is None:
        raise HTTPException(500, "Server not initialised")
    return _sm


@router.get("/metadata", response_model=GameMetadataResponse)
async def get_metadata():
    """Retrieve top-level game metadata from the seed file."""
    try:
        if config.WORLD_SEED_PATH.exists():
            with open(config.WORLD_SEED_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                meta = data.get("metadata", {})
                return GameMetadataResponse(
                    title=meta.get("title", "LLM Game"),
                    description=meta.get("description", ""),
                    initial_narrator_message=meta.get("initial_narrator_message", ""),
                    character_options=meta.get("character_options", {}),
                )
    except Exception as exc:
        log.error("Failed to load metadata from %s: %s", config.WORLD_SEED_PATH, exc)
    return GameMetadataResponse()


@router.post("/session", response_model=SessionInfo)
async def create_session(req: CreateSessionRequest):
    """Create a new game session."""
    sm = _get_sm()
    try:
        session = await sm.create_session(
            name=req.name,
            gender=req.gender,
            age=req.age,
            occupation=req.occupation,
            reset=req.reset,
        )
    except RuntimeError as exc:
        raise HTTPException(429, str(exc)) from exc

    return SessionInfo(
        session_id=session.session_id,
        player_name=session.world.player.name,
        turn=session.world.turn,
        active_npc_id=session.active_npc_id,
        current_location_id=session.world.player.current_location_id,
        created_at=session.created_at,
    )


@router.get("/sessions", response_model=List[SaveInfo])
async def list_sessions():
    """List all saved game sessions."""
    sessions = await _get_sm().list_sessions()
    return [SaveInfo(**session) for session in sessions]


@router.post("/load/{session_id}", response_model=SessionInfo)
async def load_session(session_id: str):
    """Load a specific session."""
    session = await _get_sm().load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found or corrupt")
    return SessionInfo(
        session_id=session.session_id,
        player_name=session.world.player.name,
        turn=session.world.turn,
        active_npc_id=session.active_npc_id,
        current_location_id=session.world.player.current_location_id,
        created_at=session.created_at,
    )


@router.post("/save/{session_id}")
async def save_game(session_id: str):
    """Manually save game state."""
    if not await _get_sm().save_session(session_id, is_auto=False):
        raise HTTPException(404, "Session not found")
    return {"status": "saved"}


@router.delete("/session/{session_id}")
async def destroy_session(session_id: str):
    """End and clean up a session."""
    if not _get_sm().destroy_session(session_id):
        raise HTTPException(404, "Session not found")
    return {"status": "destroyed", "session_id": session_id}


@router.get("/state/{session_id}", response_model=GameStateResponse)
async def get_game_state(session_id: str):
    """Retrieve full game state for a session."""
    session = _get_sm().get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return build_game_state_response(session)


@router.post("/action/{session_id}", response_model=ActionResponse)
async def submit_action(session_id: str, req: PlayerActionRequest):
    """Submit a player action and return the NPC response."""
    sm = _get_sm()
    session = sm.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    content = req.content.strip()

    try:
        result = await sm.process_action(session, content, req.npc_id)
    except Exception as exc:
        log.error("Action error for session %s: %s", session_id, exc, exc_info=True)
        raise HTTPException(500, "Game engine error") from exc

    npc_obj = session.world.npcs.get(result["npc_id"])
    npc_name = npc_obj.name if npc_obj else result["npc_id"]
    narration_text = result.get("narration", "").strip()
    npc_dialogue_text = result["npc_dialogue"].strip()

    session.dialogue_history.append(
        {
            "id": str(int(time.time() * 1000)),
            "type": "player",
            "content": content,
            "timestamp": time.time() * 1000,
        }
    )

    if result["npc_id"] == "narrator":
        merged_narrative = _merge_narration(narration_text, npc_dialogue_text)
        if merged_narrative:
            session.dialogue_history.append(
                {
                    "id": str(int(time.time() * 1000) + 1),
                    "type": "narration",
                    "speaker": "Narrator",
                    "content": merged_narrative,
                    "timestamp": time.time() * 1000,
                }
            )
    else:
        if narration_text:
            session.dialogue_history.append(
                {
                    "id": str(int(time.time() * 1000) + 1),
                    "type": "narration",
                    "speaker": "Narrator",
                    "content": narration_text,
                    "timestamp": time.time() * 1000,
                }
            )

        if npc_dialogue_text:
            session.dialogue_history.append(
                {
                    "id": str(int(time.time() * 1000) + 2),
                    "type": "npc",
                    "speaker": npc_name,
                    "content": npc_dialogue_text,
                    "timestamp": time.time() * 1000 + 1,
                    "trustChange": result.get("trust_change"),
                }
            )

    ws_msg = WSOutMessage(
        type="npc_response",
        payload={
            "npc_dialogue": npc_dialogue_text,
            "narration": narration_text,
            "npc_id": result["npc_id"],
            "npc_name": npc_name,
            "turn": result["turn"],
            "trust_change": result["trust_change"],
            "events": result["events"],
        },
        timestamp=time.time(),
    )
    await _broadcast_to_session(session, ws_msg)
    await sm.save_session(session_id, is_auto=True)

    return ActionResponse(
        npc_dialogue=npc_dialogue_text,
        narration=narration_text,
        npc_id=result["npc_id"],
        npc_name=npc_name,
        turn=result["turn"],
        trust_change=result["trust_change"],
        validation_errors=result["validation_errors"],
        elapsed_ms=result["elapsed_ms"],
        events=result["events"],
    )


@router.get("/npcs/{session_id}", response_model=NPCListResponse)
async def list_npcs(session_id: str, location_only: bool = Query(True)):
    """List NPCs for the session."""
    session = _get_sm().get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    world = session.world
    npcs = []
    for npc in world.npcs.values():
        if location_only and npc.location_id != world.player.current_location_id:
            continue
        if npc.alive:
            npcs.append(build_npc_info(session, npc))

    return NPCListResponse(npcs=npcs, active_npc_id=session.active_npc_id)


@router.post("/npc/{session_id}/{npc_id}")
async def switch_npc(session_id: str, npc_id: str):
    """Switch the active NPC for a session."""
    session = _get_sm().get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    world = session.world
    if npc_id not in world.npcs:
        raise HTTPException(404, f"NPC '{npc_id}' not found")

    npc = world.npcs[npc_id]
    if npc.location_id != world.player.current_location_id:
        raise HTTPException(400, f"{npc.name} is not in this location")

    if not npc.alive:
        raise HTTPException(400, f"{npc.name} is no longer available")

    session.active_npc_id = npc_id
    npc_info = build_npc_info(session, npc)

    ws_msg = WSOutMessage(
        type="npc_switched",
        payload=npc_info.model_dump(),
        timestamp=time.time(),
    )
    await _broadcast_to_session(session, ws_msg)

    return {"status": "switched", "npc": npc_info.model_dump()}


@router.get("/location/{session_id}", response_model=LocationInfo)
async def get_location(session_id: str):
    """Get current location data."""
    session = _get_sm().get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    loc_info = build_location_info(session)
    if not loc_info:
        raise HTTPException(404, "Location not found")
    return loc_info


@router.get("/locations/{session_id}", response_model=List[LocationInfo])
async def list_locations(session_id: str):
    """List all locations in the world."""
    session = _get_sm().get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    return [
        loc_info
        for loc in session.world.locations.values()
        if (loc_info := build_location_info(session, loc.id)) is not None
    ]


@router.post("/move/{session_id}", response_model=GameStateResponse)
async def move_player(session_id: str, req: MoveRequest):
    """Directly move the player to a connected location."""
    sm = _get_sm()
    session = sm.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    current_loc_id = session.world.player.current_location_id
    current_loc = session.world.locations.get(current_loc_id)

    if not current_loc or req.location_id not in current_loc.connected_to:
        target_name = (
            session.world.locations[req.location_id].name
            if req.location_id in session.world.locations
            else req.location_id.replace("_", " ").title()
        )
        current_name = (
            current_loc.name
            if current_loc
            else current_loc_id.replace("_", " ").title()
        )
        raise HTTPException(400, f"Cannot travel to {target_name} from {current_name}")

    event = Event(
        turn=session.world.turn + 1,
        event_type=EventType.PLAYER_MOVED,
        payload={"to_location_id": req.location_id},
    )
    session.store.append(event)
    session.world = apply_event(session.world, event)
    session.world.turn = event.turn

    await sm.save_session(session_id, is_auto=True)
    return build_game_state_response(session)


@router.post("/clue/link/{session_id}", response_model=GameStateResponse)
async def link_clues(session_id: str, req: LinkCluesRequest):
    """Link two clues logically in the player's journal."""
    sm = _get_sm()
    session = sm.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    if req.id1 not in session.world.clues or req.id2 not in session.world.clues:
        raise HTTPException(400, "One or both clues not found")

    event = Event(
        turn=session.world.turn,
        event_type=EventType.CLUE_LINKED,
        payload={"id1": req.id1, "id2": req.id2},
    )
    session.store.append(event)
    session.world = apply_event(session.world, event)

    await sm.save_session(session_id, is_auto=True)
    return build_game_state_response(session)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    sm = _get_sm()
    llm_ok = False
    try:
        llm_ok = sm.ping_llm()
    except Exception:
        pass
    return HealthResponse(
        status="ok",
        llm_reachable=llm_ok,
        active_sessions=sm.active_session_count,
        ready=sm.is_ready,
    )


@router.post("/pickup/{session_id}/{object_id}", response_model=GameStateResponse)
async def pickup_object(session_id: str, object_id: str):
    """Pick up an object from the current location into inventory."""
    sm = _get_sm()
    session = sm.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    world = session.world
    if object_id not in world.objects:
        raise HTTPException(404, f"Object '{object_id}' not found")

    obj = world.objects[object_id]
    if obj.location_id != world.player.current_location_id:
        raise HTTPException(400, f"{obj.name} is not in this location")

    if object_id in world.player.inventory:
        raise HTTPException(400, f"You already have {obj.name}")

    event = Event(
        turn=world.turn,
        event_type=EventType.OBJECT_TAKEN,
        payload={"object_id": object_id, "taken_by": "player"},
    )
    session.store.append(event)
    session.world = apply_event(session.world, event)

    await sm.save_session(session_id, is_auto=True)
    return build_game_state_response(session)


@router.post("/drop/{session_id}/{object_id}", response_model=GameStateResponse)
async def drop_object(session_id: str, object_id: str):
    """Drop an object from inventory at current location."""
    sm = _get_sm()
    session = sm.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    world = session.world
    if object_id not in world.player.inventory:
        raise HTTPException(400, "Object not in inventory")

    event = Event(
        turn=world.turn,
        event_type=EventType.OBJECT_DROPPED,
        payload={
            "object_id": object_id,
            "dropped_by": "player",
            "location_id": world.player.current_location_id,
        },
    )
    session.store.append(event)
    session.world = apply_event(session.world, event)

    await sm.save_session(session_id, is_auto=True)
    return build_game_state_response(session)


def _merge_narration(narration: str, dialogue: str) -> str:
    if narration and dialogue:
        return f"{narration}\n\n{dialogue}"
    return narration or dialogue


async def _broadcast_to_session(session, msg: WSOutMessage):
    """Send a message to all WebSocket connections for a session."""
    dead = set()
    data = msg.model_dump_json()
    for ws in session.ws_connections:
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    session.ws_connections -= dead


@ws_router.websocket("/ws/game/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    Real-time WebSocket for gameplay events.

    Incoming messages:
      - {"type": "action", "payload": {"content": "..."}}
      - {"type": "ping"}
    """
    sm = _get_sm()
    session = sm.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    session.ws_connections.add(websocket)
    log.info("WS connected: session=%s", session_id)

    try:
        active_npc_obj = session.world.npcs.get(session.active_npc_id)
        init_msg = WSOutMessage(
            type="connected",
            payload={
                "session_id": session_id,
                "turn": session.world.turn,
                "active_npc_id": session.active_npc_id,
                "active_npc_name": active_npc_obj.name if active_npc_obj else "",
                "location": session.world.player.current_location_id,
            },
            timestamp=time.time(),
        )
        await websocket.send_text(init_msg.model_dump_json())
    except Exception as exc:
        log.error("WS init error: %s", exc)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    WSOutMessage(
                        type="error",
                        payload={"message": "Invalid JSON"},
                        timestamp=time.time(),
                    ).model_dump_json()
                )
                continue

            msg_type = msg.get("type", "")
            payload = msg.get("payload", {})

            if msg_type == "ping":
                await websocket.send_text(
                    WSOutMessage(
                        type="pong", payload={}, timestamp=time.time()
                    ).model_dump_json()
                )
                continue

            if msg_type != "action":
                continue

            content = payload.get("content", "").strip()
            if not content:
                continue

            try:
                result = await sm.process_action(session, content)
                npc_obj = session.world.npcs.get(result["npc_id"])
                npc_name = npc_obj.name if npc_obj else result["npc_id"]

                response_msg = WSOutMessage(
                    type="npc_response",
                    payload={
                        "npc_dialogue": result.get("npc_dialogue", "").strip(),
                        "narration": result.get("narration", "").strip(),
                        "npc_id": result["npc_id"],
                        "npc_name": npc_name,
                        "turn": result["turn"],
                        "trust_change": result["trust_change"],
                        "validation_errors": result["validation_errors"],
                        "elapsed_ms": result["elapsed_ms"],
                        "events": result["events"],
                    },
                    timestamp=time.time(),
                )
                await _broadcast_to_session(session, response_msg)
                await sm.save_session(session_id, is_auto=True)
            except Exception as exc:
                log.error("WS action error: %s", exc, exc_info=True)
                await websocket.send_text(
                    WSOutMessage(
                        type="error",
                        payload={"message": "Game engine error"},
                        timestamp=time.time(),
                    ).model_dump_json()
                )

    except WebSocketDisconnect:
        log.info("WS disconnected: session=%s", session_id)
    except Exception as exc:
        log.error("WS error: %s", exc, exc_info=True)
    finally:
        session.ws_connections.discard(websocket)
