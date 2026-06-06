<script lang="ts">
	import { onMount } from 'svelte';
	import { toolApprovalMode, type ToolApprovalMode } from '$lib/stores';

	interface Props {
		onfiles: (files: FileList) => void;
	}
	let { onfiles }: Props = $props();

	let open = $state(false);
	let btnEl: HTMLButtonElement | undefined = $state();
	let menuEl: HTMLDivElement | undefined = $state();
	let inputEl: HTMLInputElement | undefined = $state();
	let pos = $state<{ x: number; bottom: number }>({ x: -9999, bottom: -9999 });
	let ready = $state(false);

	const modes: { value: ToolApprovalMode; label: string }[] = [
		{ value: 'ask', label: 'Ask for approval' },
		{ value: 'auto', label: 'Approve for me' },
		{ value: 'full', label: 'Full access' },
	];

	function toggle() {
		open = !open;
		if (open) requestAnimationFrame(updatePosition);
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

	function close() {
		open = false;
		ready = false;
	}

	$effect(() => {
		if (!open) ready = false;
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

<button
	bind:this={btnEl}
	type="button"
	class="flex items-center justify-center w-6 h-6 rounded-full text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors duration-100 cursor-pointer"
	onclick={toggle}
	aria-expanded={open}
	aria-haspopup="menu"
>
	<svg class="size-3.5 transition-transform duration-150" class:rotate-45={open} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
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
		class="fixed z-[101] min-w-36 rounded-xl bg-white dark:bg-[#1a1a1a] border border-gray-150 dark:border-white/6 shadow-xl p-0.5"
		style="left: {pos.x}px; bottom: {pos.bottom}px; opacity: {ready ? 1 : 0}; pointer-events: {ready ? 'auto' : 'none'};"
		onclick={(e) => e.stopPropagation()}
	>
	<button
			class="flex items-center gap-2 w-full h-7 px-2 rounded-xl text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-white transition-colors duration-75"
			onclick={triggerUpload}
		>
			<svg class="size-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
				<path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
			</svg>
			<span class="flex-1 text-left truncate">Attach files</span>
		</button>

		<div class="h-px bg-gray-100 dark:bg-white/4 mx-1 my-0.5"></div>

		{#each modes as mode}
			<button
				class="flex items-center gap-2 w-full h-7 px-2 rounded-xl text-xs transition-colors duration-75
					{$toolApprovalMode === mode.value
						? 'text-gray-900 dark:text-white bg-gray-50 dark:bg-white/5'
						: 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-white'}"
				onclick={() => selectMode(mode.value)}
			>
				<span class="flex-1 text-left truncate">{mode.label}</span>
				{#if $toolApprovalMode === mode.value}
					<svg class="w-3 h-3 shrink-0 text-gray-400 dark:text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
						<polyline points="20 6 9 17 4 12" />
					</svg>
				{/if}
			</button>
		{/each}
	</div>
{/if}
