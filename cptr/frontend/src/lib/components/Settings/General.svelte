<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Icon from '../Icon.svelte';
	import { theme, streamingBehavior } from '$lib/stores';
	import type { Theme, StreamingBehavior } from '$lib/stores';
	import { t, locale, changeLocale, supportedLocales } from '$lib/i18n';

	function setTheme(v: Theme) { theme.set(v); }
</script>

<div class="flex flex-col min-h-full">
<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{$t('general.title')}</h2>

<h3 class="text-xs text-gray-400 dark:text-gray-600 mb-2">{$t('general.theme')}</h3>
<div class="flex gap-1">
	{#each [
		{ value: 'light' as Theme, label: $t('general.light'), icon: 'sun-light' },
		{ value: 'dark' as Theme, label: $t('general.dark'), icon: 'half-moon' },
		{ value: 'system' as Theme, label: $t('general.system'), icon: 'monitor' },
	] as opt}
		<button
			class="flex items-center gap-1.5 h-7 px-2.5 rounded-lg text-xs transition-colors duration-100
				{$theme === opt.value ? 'bg-gray-200/50 dark:bg-white/8 text-gray-900 dark:text-white font-medium' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}"
			onclick={() => setTheme(opt.value)}
		>
			<Icon name={opt.icon} size={13} />
			{opt.label}
		</button>
	{/each}
</div>

<h3 class="text-xs text-gray-400 dark:text-gray-600 mb-2 mt-5">{$t('general.language')}</h3>
<select
	class="w-full max-w-[200px] bg-transparent text-[13px] text-gray-700 dark:text-gray-300 outline-none py-1 cursor-pointer"
	value={$locale}
	onchange={(e) => changeLocale((e.currentTarget as HTMLSelectElement).value)}
>
	{#each supportedLocales as loc}
		<option value={loc.code}>{loc.label}</option>
	{/each}
</select>

<h3 class="text-xs text-gray-400 dark:text-gray-600 mb-2 mt-5">Message queue</h3>
<div class="flex gap-1">
	{#each [
		{ value: 'queue' as StreamingBehavior, label: 'Queue' },
		{ value: 'interrupt' as StreamingBehavior, label: 'Interrupt' },
	] as opt}
		<button
			class="flex items-center gap-1.5 h-7 px-2.5 rounded-lg text-xs transition-colors duration-100
				{$streamingBehavior === opt.value ? 'bg-gray-200/50 dark:bg-white/8 text-gray-900 dark:text-white font-medium' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}"
			onclick={() => streamingBehavior.set(opt.value)}
		>
			{opt.label}
		</button>
	{/each}
</div>
<p class="text-[11px] text-gray-400 dark:text-gray-600 mt-1">
	{$streamingBehavior === 'queue'
		? 'Messages sent during generation are queued and sent after completion.'
		: 'Sending a message cancels the current generation.'}
</p>


<div class="mt-auto pt-6 flex justify-end">
	<button
		class="text-[13px] text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors duration-100"
		onclick={() => toast.success($t('settings.saved'))}
	>{$t('settings.save')}</button>
</div>
</div>

