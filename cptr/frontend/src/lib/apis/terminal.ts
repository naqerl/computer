/**
 * Terminal API: create, list, delete sessions.
 */
import { fetchHandler, fetchJSON, jsonBody } from '$lib/apis';

export interface TerminalSession {
	session_id: string;
}

export const listSessions = () =>
	fetchJSON<TerminalSession[]>('/api/terminal');

export const createSession = (cwd: string) =>
	fetchJSON<TerminalSession>('/api/terminal', jsonBody({ cwd }));

export const deleteSession = (sessionId: string) =>
	fetchHandler(`/api/terminal/${sessionId}`, { method: 'DELETE' }).catch(() => {});
