<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import {
		workspaceList,
		currentWorkspace,
		removeWorkspace,
		sidebarOpen,
	} from '$lib/stores';
	import Sortable from 'sortablejs';
	import Icon from './Icon.svelte';
	import DirectoryPicker from './DirectoryPicker.svelte';
	import DropdownMenu from './DropdownMenu.svelte';
	import SettingsModal from './SettingsModal.svelte';
	import AdminPanel from './AdminPanel.svelte';
	import { tooltip } from '$lib/tooltip';
	import { session, clearSession } from '$lib/session';
	import { getWelcome } from '$lib/apis/state';
	import { t } from '$lib/i18n';

	import { onMount, onDestroy } from 'svelte';

	let showPicker = $state(false);
	let showMenu = $state(false);
	let showSettings = $state(false);
	let settingsTab = $state<'general' | 'account' | 'about'>('general');
	let showAdmin = $state(false);
	let wsMenuPath = $state<string | null>(null);
	let wsMenuAnchor = $state<HTMLElement | null>(null);
	let appVersion = $state('');
	let menuButtonEl: HTMLButtonElement | undefined = $state();
	let wsListEl: HTMLDivElement | undefined = $state();

	// Current workspace path from URL
	const currentPath = $derived($page.url.searchParams.get('workspace'));

	function handleWorkspaceClick(e: MouseEvent, path: string) {
		// Let Cmd/Ctrl+click open in new tab naturally (it's an <a>)
		if (e.metaKey || e.ctrlKey) return;
		e.preventDefault();
		goto(`/?workspace=${encodeURIComponent(path)}`);
		if (typeof window !== 'undefined' && window.innerWidth < 768) {
			sidebarOpen.set(false);
		}
	}

	function openWsMenu(e: MouseEvent, path: string) {
		e.stopPropagation();
		e.preventDefault();
		wsMenuAnchor = e.currentTarget as HTMLElement;
		wsMenuPath = path;
	}

	function closeWsMenu() {
		wsMenuPath = null;
		wsMenuAnchor = null;
	}

	function closeSidebar() {
		sidebarOpen.set(false);
	}

	function openSettings() {
		showMenu = false;
		showSettings = true;
	}

	function logout() {
		clearSession();
	}

	async function handleRemoveWorkspace(path: string) {
		closeWsMenu();
		await removeWorkspace(path);
		// If we removed the workspace we're currently viewing, go home
		if (currentPath === path) {
			goto('/');
		}
	}

	onMount(() => {
		getWelcome()
			.then(d => { appVersion = d.version || ''; })
			.catch(() => {});
	});
</script>

{#if $sidebarOpen}
	<button class="fixed inset-0 bg-black/50 z-40 cursor-default md:hidden" onclick={closeSidebar} aria-label={$t('sidebar.closeSidebar')}></button>

	<aside class="sidebar">
		<!-- Logo header with collapse button -->
		<div class="flex items-center justify-between h-9 pl-3.5 pr-1.5 shrink-0 border-b border-gray-200 dark:border-white/6">
			<a
			href="/"
			class="flex items-center gap-1.5 text-xs font-semibold tracking-tight text-gray-900 dark:text-white"
			onclick={(e) => { e.preventDefault(); goto('/'); if (typeof window !== 'undefined' && window.innerWidth < 768) sidebarOpen.set(false); }}
		><img src="/favicon.png" alt="cptr logo" class="w-4 h-4" />cptr</a>
			<button
				class="flex items-center justify-center w-7 h-7 rounded-lg text-gray-300 hover:text-gray-500 dark:text-gray-600 dark:hover:text-gray-400 transition-colors duration-100"
				onclick={() => sidebarOpen.set(false)}
				aria-label={$t('sidebar.collapse')}
				use:tooltip={$t('sidebar.collapse')}
			>
				<Icon name="sidebar-expand" size={14} />
			</button>
		</div>

		<!-- Workspace section header -->
		<div class="flex items-center justify-between h-8 pl-3.5 pr-1.5 shrink-0">
			<span class="text-xs text-gray-400 dark:text-gray-500">{$t('sidebar.workspaces')}</span>
			<button
				class="flex items-center justify-center w-7 h-7 rounded-lg text-gray-300 hover:text-gray-500 dark:text-gray-600 dark:hover:text-gray-400 transition-colors duration-100"
				onclick={() => showPicker = true}
				aria-label={$t('sidebar.addWorkspace')}
				use:tooltip={$t('sidebar.addWorkspace')}
			>
				<Icon name="plus" size={14} />
			</button>
		</div>

		<!-- Workspace list -->
		<div bind:this={wsListEl} class="flex-1 overflow-y-auto px-1.5">
			{#each $workspaceList as ws (ws.path)}
				<a
					href="/?workspace={encodeURIComponent(ws.path)}"
					class="group flex items-center gap-1.5 w-full h-7 px-2 rounded-lg text-xs font-medium transition-colors duration-100 no-underline
						{ws.path === currentPath
							? 'bg-gray-200 text-gray-900 dark:bg-white/8 dark:text-white'
							: 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}"
					onclick={(e) => handleWorkspaceClick(e, ws.path)}
				>
					<Icon name="folder" size={14} />
					<span class="flex-1 text-left overflow-hidden text-ellipsis whitespace-nowrap">{ws.name}</span>
					<span
						class="flex items-center justify-center w-5 h-5 rounded shrink-0 text-gray-400 opacity-0 group-hover:opacity-100 hover:bg-gray-300 dark:hover:bg-white/10 transition-all duration-75"
						role="button"
						tabindex="-1"
						onclick={(e) => openWsMenu(e, ws.path)}
						aria-label={$t('sidebar.workspaceOptions')}
					>
						<Icon name="three-dots" size={11} />
					</span>
				</a>
			{/each}

			{#if $workspaceList.length === 0}
				<div class="flex flex-col items-center justify-center py-12">
					<p class="text-xs text-gray-400 dark:text-gray-600">{$t('sidebar.noWorkspaces')}</p>
				</div>
			{/if}
		</div>

		<!-- Settings - pinned bottom -->
		<div class="relative px-1.5 pb-1.5 shrink-0">

			<button
				bind:this={menuButtonEl}
				class="flex items-center gap-2 w-full h-8 px-2 rounded-lg text-xs font-medium text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors duration-100"
				onclick={() => showMenu = !showMenu}
			>
				<img
					src={$session?.profile_image_url || '/user.png'}
					alt="Avatar"
					class="w-5 h-5 rounded-full object-cover shrink-0"
				/>
				<span class="truncate">{$session?.display_name || $session?.username || $t('sidebar.settings')}</span>
				{#if appVersion}
					<span class="ml-auto text-[10px] text-gray-400 dark:text-gray-600 font-mono">v{appVersion}</span>
				{/if}
			</button>
		</div>
	</aside>
{/if}

{#if showMenu && menuButtonEl}
	<DropdownMenu
		anchor={menuButtonEl}
		matchWidth
		items={[
			...$session ? [{ label: $session.display_name || $session.username, image: $session.profile_image_url || '/user.png', onclick: () => { settingsTab = 'account'; showSettings = true; } }] : [],
			...$session ? [{ divider: true, label: '', onclick: () => {} }] : [],
			{ label: $t('sidebar.settings'), icon: 'settings', onclick: openSettings },
			...$session?.role === 'admin' ? [{ label: $t('sidebar.admin'), icon: 'shield', onclick: () => { showMenu = false; showAdmin = true; } }] : [],
			{ divider: true, label: '', onclick: () => {} },
			{ label: $t('sidebar.logOut'), icon: 'log-out', onclick: logout },
		]}
		onclose={() => showMenu = false}
	/>
{/if}

{#if showPicker}
	<DirectoryPicker onclose={() => showPicker = false} />
{/if}

{#if wsMenuPath && wsMenuAnchor}
	<DropdownMenu
		anchor={wsMenuAnchor}
		items={[
			{ label: $t('sidebar.remove'), icon: 'xmark', onclick: () => handleRemoveWorkspace(wsMenuPath!) },
		]}
		onclose={closeWsMenu}
	/>
{/if}

{#if showSettings}
	<SettingsModal initialTab={settingsTab} onclose={() => { showSettings = false; settingsTab = 'general'; }} />
{/if}

{#if showAdmin}
	<AdminPanel onclose={() => showAdmin = false} />
{/if}

<style>
	@reference "../../app.css";

	.sidebar {
		position: fixed;
		left: 0;
		top: 0;
		bottom: 0;
		width: 220px;
		z-index: 50;
		display: flex;
		flex-direction: column;
		background: white;
		border-right: 1px solid var(--color-gray-200);
	}

	:global(.dark) .sidebar {
		background: #000;
		border-right-color: rgba(255, 255, 255, 0.06);
	}

	@media (min-width: 768px) {
		.sidebar {
			position: relative;
			z-index: auto;
		}
	}
</style>
