export interface SessionInfo {
	session_id: string;
	player_name: string;
	turn: number;
	active_npc_id: string | null;
	current_location_id: string;
	created_at: number;
}

export interface TrustThreshold {
	value: number;
	label: string;
	unlocked: boolean;
}

export interface NPCInfo {
	id: string;
	name: string;
	description: string;
	personality: string;
	location_id: string;
	alive: boolean;
	trust: number;
	title?: string;
	max_trust: number;
	trust_thresholds: TrustThreshold[];
	emotional_state: string;
	emotional_label: string;
	relationship_tier: string;
	suspicion: number;
	trust_percent: number;
}

export interface ObjectInfo {
	id: string;
	name: string;
	description: string;
	location_id: string | null;
	properties: Record<string, unknown>;
}

export interface LocationInfo {
	id: string;
	name: string;
	description: string;
	connected_to: string[];
	npcs_present: NPCInfo[];
	objects_here: ObjectInfo[];
	state: Record<string, unknown>;
}

export interface PlayerInfo {
	current_location_id: string;
	inventory: ObjectInfo[];
	flags: Record<string, unknown>;
	moral_alignment: number;
	currency: number;
}

export interface GameStateResponse {
	session_id: string;
	turn: number;
	active_npc_id: string | null;
	active_npc: NPCInfo | null;
	location: LocationInfo | null;
	player: PlayerInfo | null;
	relationships: Record<string, Record<string, number>>;
	journal: Array<{
		id: string;
		turn: number;
		content: string;
		timestamp: number;
		tags?: string[];
	}>;
	clues: Array<{
		id: string;
		title: string;
		description: string;
		linked_clues: string[];
		npc_id?: string;
		tension: number;
		discovered: boolean;
	}>;
	dialogue_history?: Array<{
		id: string;
		type: string;
		speaker?: string;
		content: string;
		timestamp: number;
		trustChange?: number;
		narration?: string;
	}>;
}

export interface ActionResponse {
	npc_dialogue: string;
	narration: string;
	npc_id: string;
	npc_name: string;
	turn: number;
	trust_change: number;
	validation_errors: string[];
	elapsed_ms: number;
	events: Array<{ type: string; payload: Record<string, unknown> }>;
	npc?: NPCInfo;
	error?: boolean;
}

export interface NPCListResponse {
	npcs: NPCInfo[];
	active_npc_id: string | null;
}

export interface HealthResponse {
	status: string;
	version: string;
	llm_reachable: boolean;
	active_sessions: number;
	ready: boolean;
}

export interface SaveInfo {
	session_id: string;
	player_name: string;
	location_name: string;
	turn: number;
	created_at: number;
	is_auto: boolean;
}

export interface GameMetadataResponse {
	title: string;
	description: string;
	initial_narrator_message?: string;
	character_options?: {
		genders: string[];
		occupations: Array<{ id: string; name: string; desc: string }>;
	};
}

export interface WSOutMessage {
	type: string;
	payload: Record<string, unknown>;
	timestamp: number;
}
