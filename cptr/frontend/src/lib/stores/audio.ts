/**
 * Audio state: voice notes feature flag, transcription toggle, and modal visibility.
 */
import { writable } from 'svelte/store';
import { fetchJSON } from '$lib/apis';

export const voiceNotesEnabled = writable<boolean>(false);
export const transcribeEnabled = writable<boolean>(true);
export const showVoiceNote = writable<boolean>(false);

export async function refreshAudioState() {
	try {
		const data = await fetchJSON<{ config: Record<string, unknown> }>(
			'/api/admin/config/audio'
		);
		voiceNotesEnabled.set(data.config?.['audio.voice_notes_enabled'] === true);
		transcribeEnabled.set(data.config?.['audio.transcribe_enabled'] !== false);
	} catch {
		voiceNotesEnabled.set(false);
	}
}
