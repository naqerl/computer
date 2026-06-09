<script lang="ts">
	import { onMount } from 'svelte';
	import { toolApprovalMode, planMode, type ToolApprovalMode } from '$lib/stores';
	import { tooltip } from '$lib/tooltip';
	import Icon from '../Icon.svelte';
	import ToggleSwitch from '../ToggleSwitch.svelte';

	interface Props {
		onfiles: (files: FileList) => void;
		oncapture?: (file: File) => void;
	}
	let { onfiles, oncapture }: Props = $props();

	let open = $state(false);
	let tab = $state<'' | 'tools'>('');
	let btnEl: HTMLButtonElement | undefined = $state();
	let menuEl: HTMLDivElement | undefined = $state();
	let inputEl: HTMLInputElement | undefined = $state();
	let cameraInputEl: HTMLInputElement | undefined = $state();
	let pos = $state<{ x: number; bottom: number }>({ x: -9999, bottom: -9999 });
	let ready = $state(false);

	const modes: { value: ToolApprovalMode; label: string; desc: string }[] = [
		{ value: 'ask', label: 'Ask for approval', desc: 'Confirm each tool call before it runs' },
		{ value: 'auto', label: 'Auto-approve', desc: 'Approve safe actions, ask for risky ones' },
		{ value: 'full', label: 'Full access', desc: 'All tool calls run without confirmation' }
	];

	const currentModeLabel = $derived(
		modes.find((m) => m.value === $toolApprovalMode)?.label ?? 'Tool permissions'
	);

	function toggle() {
		open = !open;
		if (open) {
			tab = '';
			requestAnimationFrame(updatePosition);
		}
	}

	function updatePosition() {
		if (!btnEl || !menuEl) return;
		const rect = btnEl.getBoundingClientRect();
		const mw = menuEl.offsetWidth;
		const vh = window.innerHeight;
		let x = rect.left;
		if (x + mw > window.innerWidth - 8) x = window.innerWidth - mw - 8;
		if (x < 8) x = 8;
		pos = { x, bottom: vh - rect.top + 4 };
		ready = true;
	}

	function selectMode(mode: ToolApprovalMode) {
		toolApprovalMode.set(mode);
	}

	function triggerUpload() {
		open = false;
		inputEl?.click();
	}

	function handleFileChange() {
		if (inputEl?.files && inputEl.files.length > 0) {
			onfiles(inputEl.files);
			inputEl.value = '';
		}
	}

	function handleCameraChange() {
		if (cameraInputEl?.files && cameraInputEl.files.length > 0) {
			// Camera input returns image files — pass them through oncapture or onfiles
			for (const file of Array.from(cameraInputEl.files)) {
				if (oncapture) oncapture(file);
			}
			cameraInputEl.value = '';
		}
	}

	function isMobileDevice(): boolean {
		if (typeof navigator === 'undefined') return false;
		const ua = navigator.userAgent || (navigator as any).vendor || (window as any).opera || '';
		return /android|iphone|ipad|ipod|windows phone/i.test(ua);
	}

	async function captureHandler() {
		open = false;
		if (isMobileDevice()) {
			// On mobile, open the camera
			cameraInputEl?.click();
			return;
		}
		// Desktop: use screen capture API
		try {
			const mediaStream = await navigator.mediaDevices.getDisplayMedia({
				video: { cursor: 'never' } as any,
				audio: false
			});
			const video = document.createElement('video');
			video.srcObject = mediaStream;
			await video.play();

			const canvas = document.createElement('canvas');
			canvas.width = video.videoWidth;
			canvas.height = video.videoHeight;
			const ctx = canvas.getContext('2d');
			if (ctx) ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

			mediaStream.getTracks().forEach((t) => t.stop());
			window.focus();

			const blob = await new Promise<Blob | null>((res) => canvas.toBlob(res, 'image/png'));
			if (blob) {
				const file = new File([blob], `screen-capture-${Date.now()}.png`, { type: 'image/png' });
				if (oncapture) oncapture(file);
			}
			video.srcObject = null;
		} catch (err) {
			console.error('Error capturing screen:', err);
		}
	}

	function close() {
		open = false;
		ready = false;
		tab = '';
	}

	$effect(() => {
		if (!open) {
			ready = false;
			tab = '';
		}
	});
</script>

<input
	bind:this={inputEl}
	type="file"
	multiple
	accept="image/*,.pdf,.txt,.md,.csv,.json,.xml,.yaml,.yml,.html,.css,.js,.ts,.py,.go,.rs,.java,.c,.cpp,.h,.rb,.sh"
	class="hidden"
	onchange={handleFileChange}
/>

<!-- Hidden camera input for mobile capture -->
<input
	bind:this={cameraInputEl}
	type="file"
	accept="image/*"
	capture="environment"
	class="hidden"
	onchange={handleCameraChange}
/>

<button
	bind:this={btnEl}
	type="button"
	class="flex items-center justify-center w-6 h-6 rounded-full text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors duration-100 cursor-pointer"
	onclick={toggle}
	aria-expanded={open}
	aria-haspopup="menu"
>
	<svg
		class="size-3.5 transition-transform duration-150"
		class:rotate-45={open}
		viewBox="0 0 24 24"
		fill="none"
		stroke="currentColor"
		stroke-width="2"
		stroke-linecap="round"
		stroke-linejoin="round"
	>
		<line x1="12" y1="5" x2="12" y2="19" />
		<line x1="5" y1="12" x2="19" y2="12" />
	</svg>
</button>

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="fixed inset-0 z-[100]" onclick={close}></div>

	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		bind:this={menuEl}
		class="fixed z-[101] w-56 rounded-xl bg-white dark:bg-[#1a1a1a] border border-gray-150 dark:border-white/6 shadow-xl p-0.5 overflow-hidden"
		style="left: {pos.x}px; bottom: {pos.bottom}px; opacity: {ready ? 1 : 0}; pointer-events: {ready
			? 'auto'
			: 'none'};"
		onclick={(e) => e.stopPropagation()}
	>
		{#if tab === ''}
			<!-- Main menu -->
			<div class="plus-menu-slide-in-left">
				<button
					class="flex items-center gap-2 w-full h-7 px-2 rounded-xl text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-white transition-colors duration-75"
					onclick={triggerUpload}
				>
					<svg
						class="size-3.5 shrink-0"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.5"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path
							d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"
						/>
					</svg>
					<span class="flex-1 text-left truncate">Attach files</span>
				</button>

				<button
					class="flex items-center gap-2 w-full h-7 px-2 rounded-xl text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-white transition-colors duration-75"
					onclick={captureHandler}
				>
					<svg
						class="size-3.5 shrink-0"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.5"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
						<circle cx="12" cy="13" r="4" />
					</svg>
					<span class="flex-1 text-left truncate">Capture</span>
				</button>

				<div class="h-px bg-gray-100/50 dark:bg-white/3 mx-1 my-0.5"></div>

				<!-- Plan mode toggle -->
				<button
					class="flex items-center gap-2 w-full h-7 px-2 rounded-xl text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-white transition-colors duration-75"
					onclick={() => planMode.update((v) => !v)}
				>
					<svg
						class="size-3.5 shrink-0"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.5"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
						<polyline points="14 2 14 8 20 8" />
						<line x1="9" y1="13" x2="15" y2="13" />
						<line x1="9" y1="17" x2="15" y2="17" />
					</svg>
					<span class="flex-1 text-left truncate">Plan mode</span>
					<ToggleSwitch value={$planMode} onchange={(v) => planMode.set(v)} />
				</button>

				<div class="h-px bg-gray-100/50 dark:bg-white/3 mx-1 my-0.5"></div>

				<button
					class="flex items-center gap-2 w-full h-7 px-2 rounded-xl text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-white transition-colors duration-75"
					onclick={() => (tab = 'tools')}
				>
					<Icon name="shield" size={14} />
					<span class="flex-1 text-left truncate">Tool permissions</span>
					<span class="text-[10px] text-gray-400 dark:text-gray-500 truncate max-w-16"
						>{currentModeLabel}</span
					>
					<Icon name="chevron-right" size={12} class="shrink-0 text-gray-400 dark:text-gray-500" />
				</button>
			</div>
		{:else if tab === 'tools'}
			<!-- Tool permissions submenu -->
			<div class="plus-menu-slide-in-right">
				<button
					class="flex items-center gap-2 w-full h-7 px-2 rounded-xl text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-white transition-colors duration-75"
					onclick={() => (tab = '')}
				>
					<Icon name="chevron-left" size={12} />
					<span class="flex-1 text-left font-medium">Tool permissions</span>
				</button>

				<div class="h-px bg-gray-100/50 dark:bg-white/3 mx-1 my-0.5"></div>

				{#each modes as mode}
					<button
						class="flex items-center gap-2 w-full h-7 px-2 rounded-xl text-xs transition-colors duration-75
							{$toolApprovalMode === mode.value
							? 'text-gray-900 dark:text-white bg-gray-50 dark:bg-white/5'
							: 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-white'}"
						onclick={() => selectMode(mode.value)}
						use:tooltip={{ content: mode.desc, placement: 'right' }}
					>
						<span class="flex-1 text-left truncate">{mode.label}</span>
						{#if $toolApprovalMode === mode.value}
							<svg
								class="w-3 h-3 shrink-0 text-gray-400 dark:text-gray-500"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2.5"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<polyline points="20 6 9 17 4 12" />
							</svg>
						{/if}
					</button>
				{/each}
			</div>
		{/if}
	</div>
{/if}

<style>
	@reference "../../../app.css";

	.plus-menu-slide-in-left {
		animation: slideFromLeft 0.15s ease-out;
	}

	.plus-menu-slide-in-right {
		animation: slideFromRight 0.15s ease-out;
	}

	@keyframes slideFromLeft {
		from {
			opacity: 0;
			transform: translateX(-12px);
		}
		to {
			opacity: 1;
			transform: translateX(0);
		}
	}

	@keyframes slideFromRight {
		from {
			opacity: 0;
			transform: translateX(12px);
		}
		to {
			opacity: 1;
			transform: translateX(0);
		}
	}
</style>
