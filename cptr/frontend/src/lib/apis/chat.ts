/**
 * Chat API: send messages, approve/reject tools, cancel tasks, fetch chats.
 */
import { fetchJSON, jsonBody } from '$lib/apis';

export interface ChatMessageRow {
	id: string;
	parent_id: string | null;
	role: 'user' | 'assistant';
	content: string;
	model: string | null;
	done: boolean;
	output: any[] | null;
	usage: Record<string, number> | null;
	meta: Record<string, any> | null;
	created_at: number;
}

export interface ChatInfo {
	id: string;
	title: string;
	summary: string | null;
	folder: string;
	meta: Record<string, any> | null;
	current_message_id: string | null;
	created_at: number;
	updated_at: number;
}

export interface ChatDetail {
	chat: ChatInfo;
	messages: ChatMessageRow[];
}

export interface SendMessageResult {
	chat_id: string;
	message_id: string;
}

// ── Queries ─────────────────────────────────────────────────

export const getChats = (workspace: string) =>
	fetchJSON<{ chats: ChatInfo[] }>(`/api/chats?workspace=${encodeURIComponent(workspace)}`);

export const getChat = (chatId: string) =>
	fetchJSON<ChatDetail>(`/api/chats/${chatId}`);

export const deleteChat = (chatId: string) =>
	fetchJSON<{ ok: boolean }>(`/api/chats/${chatId}`, { method: 'DELETE' });

// ── Mutations ───────────────────────────────────────────────

export const sendMessage = (
	content: string,
	modelId: string,
	workspace: string,
	chatId?: string,
	parentId?: string | null,
	params: { tool_approval_mode?: string } = {},
	regenerationPrompt?: string
) =>
	fetchJSON<SendMessageResult>(
		'/api/chats',
		jsonBody({
			content,
			model_id: modelId,
			workspace,
			chat_id: chatId,
			parent_id: parentId ?? null,
			regeneration_prompt: regenerationPrompt,
			params
		})
	);

export const approveToolCall = (
	chatId: string,
	messageId: string,
	callId: string,
	approved = true
) =>
	fetchJSON(
		`/api/chats/${chatId}/messages/${messageId}/approve`,
		jsonBody({ call_id: callId, approved })
	);

export const cancelTask = (chatId: string, messageId: string) =>
	fetchJSON(`/api/chats/${chatId}/messages/${messageId}/cancel`, { method: 'POST' });

export const updateCurrentMessage = (chatId: string, messageId: string) =>
	fetchJSON<{ ok: boolean }>(
		`/api/chats/${chatId}/current`,
		jsonBody({ message_id: messageId })
	);

export const updateMessage = (
	chatId: string,
	messageId: string,
	updates: { content?: string; output?: any[] }
) =>
	fetchJSON<{ ok: boolean }>(`/api/chats/${chatId}/messages/${messageId}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(updates)
	});

export const createMessage = (
	chatId: string,
	parentId: string | null,
	role: string,
	content: string,
	output?: any[]
) =>
	fetchJSON<{ ok: boolean; message_id: string }>(
		`/api/chats/${chatId}/messages`,
		jsonBody({ parent_id: parentId, role, content, output })
	);
