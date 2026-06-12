/**
 * Audio state: voice memos feature flag, transcription toggle, and modal visibility.
 */
import { writable } from 'svelte/store';
import { fetchJSON } from '$lib/apis';

export const voiceMemosEnabled = writable<boolean>(false);
export const transcribeEnabled = writable<boolean>(true);
export const showVoiceMemo = writable<boolean>(false);

export async function refreshAudioState() {
	try {
		const data = await fetchJSON<{ config: Record<string, unknown> }>(
			'/api/admin/config/audio'
		);
		voiceMemosEnabled.set(data.config?.['audio.voice_memos_enabled'] === true);
		transcribeEnabled.set(data.config?.['audio.transcribe_enabled'] !== false);
	} catch {
		voiceMemosEnabled.set(false);
	}
}
