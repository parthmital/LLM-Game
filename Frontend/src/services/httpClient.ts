import { API_BASE_URL } from "@/config/constants";
import type {
	ActionResponse,
	GameMetadataResponse,
	GameStateResponse,
	HealthResponse,
	LocationInfo,
	NPCInfo,
	NPCListResponse,
	SaveInfo,
	SessionInfo,
} from "@/contracts/api";

export class APIError extends Error {
	constructor(
		public status: number,
		message: string,
	) {
		super(message);
		this.name = "APIError";
	}
}

export class APIClient {
	constructor(private baseUrl = API_BASE_URL) {}

	private async request<T>(
		method: string,
		path: string,
		body?: unknown,
	): Promise<T> {
		const response = await fetch(`${this.baseUrl}${path}`, {
			method,
			headers: { "Content-Type": "application/json" },
			body: body === undefined ? undefined : JSON.stringify(body),
		});
		const responseData = await response.json().catch(() => ({}));

		if (!response.ok) {
			throw new APIError(
				response.status,
				getErrorMessage(response, responseData),
			);
		}

		return responseData as T;
	}

	async createSession(config: {
		name: string;
		gender: string;
		age: number;
		occupation: string;
		reset?: boolean;
	}): Promise<SessionInfo> {
		return this.request<SessionInfo>("POST", "/session", {
			name: config.name,
			gender: config.gender,
			age: config.age,
			occupation: config.occupation,
			reset: config.reset ?? false,
		});
	}

	async destroySession(sessionId: string): Promise<void> {
		await this.request("DELETE", `/session/${sessionId}`);
	}

	async getGameState(sessionId: string): Promise<GameStateResponse> {
		return this.request<GameStateResponse>("GET", `/state/${sessionId}`);
	}

	async movePlayer(
		sessionId: string,
		locationId: string,
	): Promise<GameStateResponse> {
		return this.request<GameStateResponse>("POST", `/move/${sessionId}`, {
			location_id: locationId,
		});
	}

	async linkClues(
		sessionId: string,
		id1: string,
		id2: string,
	): Promise<GameStateResponse> {
		return this.request<GameStateResponse>("POST", `/clue/link/${sessionId}`, {
			id1,
			id2,
		});
	}

	async sendAction(
		sessionId: string,
		content: string,
		npcId?: string,
	): Promise<ActionResponse> {
		return this.request<ActionResponse>("POST", `/action/${sessionId}`, {
			content,
			npc_id: npcId,
		});
	}

	async listNPCs(
		sessionId: string,
		locationOnly = true,
	): Promise<NPCListResponse> {
		const query = locationOnly ? "?location_only=true" : "";
		return this.request<NPCListResponse>("GET", `/npcs/${sessionId}${query}`);
	}

	async switchNPC(
		sessionId: string,
		npcId: string,
	): Promise<{ status: string; npc: NPCInfo }> {
		return this.request("POST", `/npc/${sessionId}/${npcId}`);
	}

	async getLocation(sessionId: string): Promise<LocationInfo> {
		return this.request<LocationInfo>("GET", `/location/${sessionId}`);
	}

	async listLocations(sessionId: string): Promise<LocationInfo[]> {
		return this.request<LocationInfo[]>("GET", `/locations/${sessionId}`);
	}

	async healthCheck(): Promise<HealthResponse> {
		return this.request<HealthResponse>("GET", "/health");
	}

	async listSessions(): Promise<SaveInfo[]> {
		return this.request<SaveInfo[]>("GET", "/sessions");
	}

	async saveSession(sessionId: string): Promise<void> {
		await this.request("POST", `/save/${sessionId}`);
	}

	async loadSession(sessionId: string): Promise<SessionInfo> {
		return this.request<SessionInfo>("POST", `/load/${sessionId}`);
	}

	async getMetadata(): Promise<GameMetadataResponse> {
		return this.request<GameMetadataResponse>("GET", "/metadata");
	}

	async pickupObject(
		sessionId: string,
		objectId: string,
	): Promise<GameStateResponse> {
		return this.request<GameStateResponse>(
			"POST",
			`/pickup/${sessionId}/${objectId}`,
		);
	}

	async dropObject(
		sessionId: string,
		objectId: string,
	): Promise<GameStateResponse> {
		return this.request<GameStateResponse>(
			"POST",
			`/drop/${sessionId}/${objectId}`,
		);
	}

	async pollReady(): Promise<boolean> {
		try {
			const response = await fetch("/health");
			if (!response.ok) return false;
			const data = await response.json();
			return data.ready === true;
		} catch {
			return false;
		}
	}
}

function getErrorMessage(
	response: Response,
	data: Record<string, unknown>,
): string {
	if (Array.isArray(data.detail)) {
		return data.detail
			.map((err: { loc?: (string | number)[]; msg: string }) => {
				const field = err.loc ? err.loc[err.loc.length - 1] : "field";
				return `${field}: ${err.msg}`;
			})
			.join(". ");
	}

	if (data.detail) {
		return String(data.detail);
	}

	if (data.error) {
		return String(data.error);
	}

	return response.statusText;
}

export const apiClient = new APIClient();
