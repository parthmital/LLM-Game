import { WS_CONFIG } from "@/config/constants";
import type { WSOutMessage } from "@/contracts/api";

export type WSCallback = (msg: WSOutMessage) => void;

class WebSocketService {
	private ws: WebSocket | null = null;
	private listeners: Map<string, WSCallback[]> = new Map();
	private reconnectAttempts = 0;
	private maxReconnects = WS_CONFIG.RECONNECT_MAX_ATTEMPTS;
	private sessionId: string | null = null;
	private pingInterval: ReturnType<typeof setInterval> | null = null;

	connect(sessionId: string, resetReconnects = true) {
		if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
			this.disconnect();
		}

		this.sessionId = sessionId;
		if (resetReconnects) {
			this.reconnectAttempts = 0;
		}

		const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
		const host = window.location.host;
		this.ws = new WebSocket(`${protocol}//${host}/ws/game/${sessionId}`);

		this.ws.onopen = () => {
			this.reconnectAttempts = 0;
			this.emitLocal("connection", {
				type: "connection",
				payload: { status: "connected" },
				timestamp: Date.now(),
			});

			this.pingInterval = setInterval(() => {
				this.send("ping", {});
			}, WS_CONFIG.HEARTBEAT_INTERVAL_MS);
		};

		this.ws.onmessage = (event) => {
			try {
				const msg: WSOutMessage = JSON.parse(event.data);
				this.emitLocal(msg.type, msg);
				this.emitLocal("*", msg);
			} catch {
				this.emitLocal("error", {
					type: "error",
					payload: { message: "Invalid WebSocket message" },
					timestamp: Date.now(),
				});
			}
		};

		this.ws.onclose = (event) => {
			this.clearPing();
			this.emitLocal("connection", {
				type: "connection",
				payload: { status: "disconnected", code: event.code },
				timestamp: Date.now(),
			});
			if (event.code !== 1000 && event.code !== 4004) {
				this.handleReconnect();
			}
		};

		this.ws.onerror = () => {
			this.emitLocal("error", {
				type: "error",
				payload: { message: "WebSocket error" },
				timestamp: Date.now(),
			});
		};
	}

	disconnect() {
		this.clearPing();
		if (this.ws) {
			this.ws.close(1000, "Client disconnect");
			this.ws = null;
		}
		this.sessionId = null;
	}

	send(type: string, payload: unknown) {
		if (this.ws?.readyState === WebSocket.OPEN) {
			this.ws.send(JSON.stringify({ type, payload }));
		}
	}

	on(type: string, callback: WSCallback) {
		const existing = this.listeners.get(type) ?? [];
		this.listeners.set(type, [...existing, callback]);
	}

	off(type: string, callback: WSCallback) {
		const existing = this.listeners.get(type) ?? [];
		this.listeners.set(
			type,
			existing.filter((cb) => cb !== callback),
		);
	}

	clearListeners() {
		this.listeners.clear();
	}

	get isConnected(): boolean {
		return this.ws?.readyState === WebSocket.OPEN;
	}

	private emitLocal(type: string, msg: WSOutMessage) {
		const handlers = this.listeners.get(type) ?? [];
		handlers.forEach((callback) => callback(msg));
	}

	private clearPing() {
		if (this.pingInterval) {
			clearInterval(this.pingInterval);
			this.pingInterval = null;
		}
	}

	private handleReconnect() {
		if (this.reconnectAttempts < this.maxReconnects && this.sessionId) {
			this.reconnectAttempts++;
			const delay = Math.min(
				WS_CONFIG.RECONNECT_BASE_DELAY_MS * Math.pow(2, this.reconnectAttempts),
				WS_CONFIG.RECONNECT_MAX_DELAY_MS,
			);
			setTimeout(() => {
				if (this.sessionId) this.connect(this.sessionId, false);
			}, delay);
		}
	}
}

export const wsService = new WebSocketService();
