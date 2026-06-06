/**
 * Chat state: tracks whether chat is available (at least one connection configured).
 */
import { writable, get } from 'svelte/store';
import { fetchJSON } from '$lib/apis';
import { socketStore } from '$lib/stores/socket.svelte';

export const chatEnabled = writable<boolean>(false);

/** Set of tab IDs whose chat is currently streaming (assistant message not done). */
export const streamingChatTabs = writable<Set<string>>(new Set());

/**
 * Maps chatId -> tabId so we can clear streamingChatTabs from a global
 * socket listener even when the ChatPanel component is unmounted.
 */
const chatToTab = new Map<string, string>();

export function registerStreamingChat(chatId: string, tabId: string) {
	chatToTab.set(chatId, tabId);
}

export function unregisterStreamingChat(chatId: string) {
	chatToTab.delete(chatId);
}

/**
 * Bind a global socket listener that clears streamingChatTabs when a
 * chat's "done" event arrives -- even if the ChatPanel is not mounted.
 * Called once from the app layout.
 */
let globalListenerBound = false;

export function bindGlobalChatListener() {
	if (globalListenerBound) return;

	const tryBind = () => {
		const socket = socketStore.getSocket();
		if (!socket) { setTimeout(tryBind, 200); return; }

		socket.on('events:chat', (data: { chat_id: string; done?: boolean }) => {
			if (!data.done) return;
			const tabId = chatToTab.get(data.chat_id);
			if (tabId) {
				streamingChatTabs.update((s) => {
					const next = new Set(s);
					next.delete(tabId);
					return next;
				});
			}
		});

		globalListenerBound = true;
	};
	tryBind();
}

export interface ChatModel {
	id: string;
	name: string;
	provider: string;
	connection_id: string;
}

export const chatModels = writable<ChatModel[]>([]);
export const defaultModel = writable<string | null>(null);

export async function refreshChatState() {
	try {
		const data = await fetchJSON<{ models: ChatModel[]; default: string | null }>('/api/chats/models');
		chatModels.set(data.models);
		defaultModel.set(data.default);
		chatEnabled.set(data.models.length > 0);
	} catch {
		chatEnabled.set(false);
		chatModels.set([]);
	}
}
