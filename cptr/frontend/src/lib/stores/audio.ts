/**
 * Audio state: voice memos feature flag, transcription toggle, recording quality, and modal visibility.
 */
import { writable } from 'svelte/store';
import { fetchJSON } from '$lib/apis';

export type RecordingQuality = 'high' | 'medium' | 'low';

export const QUALITY_BITRATES: Record<RecordingQuality, number> = {
	high: 128000,
	medium: 64000,
	low: 32000
};

export const voiceMemosEnabled = writable<boolean>(false);
export const transcribeEnabled = writable<boolean>(true);
export const recordingQuality = writable<RecordingQuality>('high');
export const showVoiceMemo = writable<boolean>(false);
export const ttsEnabled = writable<boolean>(false);
export const ttsConfigured = writable<boolean>(false);
export const ttsVoice = writable<string>('alloy');
export const ttsFormat = writable<string>('mp3');
export const voiceModeEnabled = writable<boolean>(false);
export const ttsPlaybackEnabled = writable<boolean>(
	typeof localStorage !== 'undefined' ? localStorage.getItem('ttsPlaybackEnabled') === 'true' : false
);

ttsPlaybackEnabled.subscribe((v) => {
	if (typeof localStorage !== 'undefined') localStorage.setItem('ttsPlaybackEnabled', String(v));
});

export async function refreshAudioState() {
	try {
		const data = await fetchJSON<{
			voice_memos_enabled: boolean;
			transcribe_enabled: boolean;
			recording_quality: string;
			tts_enabled: boolean;
			tts_configured: boolean;
			tts_voice: string;
			tts_format: string;
		}>('/api/audio/state');
		voiceMemosEnabled.set(data.voice_memos_enabled === true);
		transcribeEnabled.set(data.transcribe_enabled !== false);
		const q = data.recording_quality;
		if (q === 'medium' || q === 'low') recordingQuality.set(q);
		else recordingQuality.set('high');
		ttsEnabled.set(data.tts_enabled === true);
		ttsConfigured.set(data.tts_configured === true);
		ttsVoice.set(data.tts_voice || 'alloy');
		ttsFormat.set(data.tts_format || 'mp3');
	} catch {
		voiceMemosEnabled.set(false);
		ttsEnabled.set(false);
		ttsConfigured.set(false);
	}
}
