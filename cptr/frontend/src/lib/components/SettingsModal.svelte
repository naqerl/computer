<script lang="ts">
	import Icon from './Icon.svelte';
	import Modal from './Modal.svelte';
	import General from './Settings/General.svelte';
	import Account from './Settings/Account.svelte';
	import Keyboard from './Settings/Keyboard.svelte';
	import About from './Settings/About.svelte';
	import { t } from '$lib/i18n';

	interface Props {
		onclose: () => void;
		initialTab?: 'general' | 'keyboard' | 'account' | 'about';
	}

	let { onclose, initialTab = 'general' }: Props = $props();

	let activeTab = $state<'general' | 'keyboard' | 'account' | 'about'>(initialTab);
</script>

<Modal
	{onclose}
	class="w-full max-w-3xl mx-4 md:mx-0 flex flex-col md:flex-row max-h-[85vh] md:h-[560px]"
>
	<nav
		class="shrink-0 min-w-0 overflow-x-auto md:overflow-x-visible scrollbar-hidden border-b md:border-b-0 md:border-r border-gray-200 dark:border-white/6 md:w-[180px]"
	>
		<div class="flex w-max min-w-full md:w-auto md:min-w-0 md:flex-col p-1 gap-px">
			<button
				class="flex items-center gap-1.5 h-7 px-2 md:w-full shrink-0 rounded-lg text-xs text-gray-400 dark:text-gray-600 hover:text-gray-700 dark:hover:text-gray-300 transition-colors duration-75 md:mb-1"
				onclick={onclose}
			>
				<Icon name="chevron-left" size={12} />
				<span>{$t('settings.back')}</span>
			</button>
			{#each [{ id: 'general', label: $t('settings.general'), icon: 'settings' }, { id: 'keyboard', label: 'Keyboard', icon: 'terminal' }, { id: 'account', label: $t('settings.account'), icon: 'user' }, { id: 'about', label: $t('settings.about'), icon: 'info' }] as tab}
				<button
					class="flex items-center gap-1.5 h-7 px-2 md:w-full shrink-0 rounded-lg text-xs text-left transition-colors duration-75
						{activeTab === tab.id
						? 'font-medium text-gray-900 dark:text-white bg-gray-100 dark:bg-white/6'
						: 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}"
					onclick={() => (activeTab = tab.id as typeof activeTab)}
				>
					<Icon name={tab.icon} size={14} />
					{tab.label}
				</button>
			{/each}
		</div>
	</nav>

	<div class="flex-1 overflow-y-auto min-h-0 p-4 md:px-5">
		{#if activeTab === 'general'}
			<General />
		{:else if activeTab === 'keyboard'}
			<Keyboard />
		{:else if activeTab === 'account'}
			<Account />
		{:else if activeTab === 'about'}
			<About />
		{/if}
	</div>
</Modal>
