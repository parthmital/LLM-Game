export type MessageType = "player" | "npc" | "narration" | "system";

export interface DialogueMessage {
	id: string;
	type: MessageType;
	speaker?: string;
	content: string;
	timestamp: number;
	trustChange?: number;
	memoryRef?: string;
}

export interface NPC {
	id: string;
	name: string;
	title?: string;
	description?: string;
	personality?: string;
	portraitUrl?: string;
	trust: number;
	maxTrust: number;
	trustThresholds: TrustThreshold[];
	emotionalState: EmotionalState;
	hiddenSecrets: number;
	revealedSecrets: number;
	allegiances: string[];
	relationshipTier: RelationshipTier;
	suspicion: number;
	emotionalLabel: string;
	trustPercent: number;
	locationId?: string;
}

export interface TrustThreshold {
	value: number;
	label: string;
	unlocked: boolean;
}

export type EmotionalState =
	| "neutral"
	| "suspicious"
	| "fearful"
	| "angry"
	| "melancholic"
	| "guarded"
	| "trusting"
	| "desperate"
	| "hostile"
	| "playful";

export type RelationshipTier =
	"stranger" | "acquaintance" | "confidant" | "ally" | "rival" | "enemy";

export interface JournalEntry {
	id: string;
	timestamp: number;
	content: string;
	npcId?: string;
	tags: string[];
	expanded?: boolean;
	category?: "case" | "evidence" | "note" | "thought";
}

export interface Clue {
	id: string;
	title: string;
	description: string;
	linkedClues: string[];
	npcId?: string;
	tension: number;
	discovered: boolean;
}
