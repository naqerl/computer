<script lang="ts">
	import '../app.css';
	import '@xterm/xterm/css/xterm.css';

	import { onMount } from 'svelte';
	import Bar from '$lib/components/Bar.svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import ShortcutBar from '$lib/components/ShortcutBar.svelte';
	import GitBar from '$lib/components/GitBar.svelte';
	import QuickOpen from '$lib/components/QuickOpen.svelte';
	import AuthScreen from '$lib/components/AuthScreen.svelte';
	import { Toaster } from 'svelte-sonner';
	import { activeTab, currentWorkspace, stateLoaded, initState, gitReviewOpen, isGitRepo, splitActive, splitCurrentTab, closeGroup } from '$lib/stores';
	import { systemEvents } from '$lib/stores/systemEvents.svelte';
	import { socketStore } from '$lib/stores/socket.svelte';
	import { setSession } from '$lib/session';
	import { getSession, getConfig } from '$lib/apis/auth';
	import { getGitStatus } from '$lib/apis/git';
	import { t } from '$lib/i18n';
	import { refreshChatState, bindGlobalChatListener } from '$lib/stores/chat';

	let { children } = $props();
	let showQuickOpen = $state(false);
	let viewportHeight = $state('100dvh');

	// Auth state
	type AuthState = 'checking' | 'needs_setup' | 'needs_login' | 'authenticated';
	let authState = $state<AuthState>('checking');
	let authMode = $state<'password' | 'pam'>('password');
	let signupEnabled = $state(false);

	onMount(async () => {
		// Check auth first
		await checkAuth();

		// Periodic session health check (every 30 min).
		// This triggers the backend's sliding session refresh and
		// proactively catches expired sessions before a 401 mid-action.
		const healthCheck = setInterval(() => {
			if (authState === 'authenticated') {
				getSession().then((auth) => {
					if (!auth.authenticated) clearSession();
				}).catch(() => {});
			}
		}, 30 * 60 * 1000);

		// iOS/Android: visualViewport gives accurate height when keyboard is open.
		// Debounce to avoid firing dozens of resizes during the keyboard animation
		// (~300ms). We only commit the final height after things settle, which
		// prevents TUI apps from receiving multiple SIGWINCH and re-rendering.
		const vv = window.visualViewport;
		let vpTimer: ReturnType<typeof setTimeout>;
		if (vv) {
			const update = () => {
				clearTimeout(vpTimer);
				vpTimer = setTimeout(() => {
					viewportHeight = `${vv.height}px`;
				}, 350);
			};
			vv.addEventListener('resize', update);
			return () => {
				clearTimeout(vpTimer);
				clearInterval(healthCheck);
				vv.removeEventListener('resize', update);
			};
		}

		return () => clearInterval(healthCheck);
	});

	let startupToken = $state('');

	async function checkAuth() {
		try {
			const params = new URLSearchParams(window.location.search);
			const token = params.get('token');
			if (token) {
				startupToken = token;
				// Remove token from URL but preserve workspace param
				const url = new URL(window.location.href);
				url.searchParams.delete('token');
				window.history.replaceState({}, '', url.toString());
			}

			const auth = await getSession();

			if (auth.authenticated) {
				setSession({
					user_id: auth.user_id!,
					username: auth.username!,
					display_name: auth.display_name,
					role: auth.role!,
					profile_image_url: auth.profile_image_url,
				});
				authState = 'authenticated';
				initState();
				refreshChatState();
			} else {
				const cfg = await getConfig();
				authMode = cfg.auth_mode || 'password';
				signupEnabled = cfg.signup_enabled || false;
				authState = cfg.needs_setup ? 'needs_setup' : 'needs_login';
			}
		} catch {
			authState = 'authenticated';
			initState();
		}
	}

	async function handleAuth() {
		try {
			const auth = await getSession();
			if (auth.authenticated) {
				setSession({
					user_id: auth.user_id!,
					username: auth.username!,
					display_name: auth.display_name,
					role: auth.role!,
					profile_image_url: auth.profile_image_url,
				});
				authState = 'authenticated';
				initState();
				refreshChatState();
				return;
			}
		} catch {}
		authState = 'needs_login';
	}

	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
			e.preventDefault();
			showQuickOpen = !showQuickOpen;
		}
		// Cmd/Ctrl+\ to toggle split view
		if ((e.metaKey || e.ctrlKey) && e.key === '\\') {
			e.preventDefault();
			if ($splitActive && $currentWorkspace) {
				// Close the non-active group
				const otherGroup = $currentWorkspace.groups.find((g) => g.id !== $currentWorkspace!.activeGroupId);
				if (otherGroup) closeGroup(otherGroup.id);
			} else {
				splitCurrentTab();
			}
		}
	}

	// Connect system events when workspace is active
	$effect(() => {
		const ws = $currentWorkspace;
		if (ws) {
			systemEvents.connect(ws.fileBrowserCwd || ws.path);
			socketStore.connect();
			bindGlobalChatListener();
		} else {
			systemEvents.disconnect();
			socketStore.disconnect();
		}
	});

	// Detect if workspace is a git repo
	$effect(() => {
		const ws = $currentWorkspace;
		if (!ws) {
			isGitRepo.set(false);
			gitReviewOpen.set(false);
			return;
		}
		const wsPath = ws.path;
		let cancelled = false;

		async function check() {
			try {
				const status = await getGitStatus(wsPath) as { is_repo?: boolean };
				if (!cancelled) isGitRepo.set(Boolean(status?.is_repo));
			} catch {
				if (!cancelled) isGitRepo.set(false);
			}
		}

		check();
		const interval = setInterval(check, 5000);
		return () => { cancelled = true; clearInterval(interval); };
	});
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
	<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300..700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
	<title>{$currentWorkspace ? `${$currentWorkspace.name} / cptr` : 'cptr'}</title>
	<meta name="description" content={$t('app.tagline')} />
</svelte:head>

<svelte:window onkeydown={handleKeydown} />

{#if authState === 'checking'}
	<!-- Loading spinner while checking auth -->
	<div class="flex items-center justify-center h-dvh bg-white dark:bg-black">
		<div class="w-5 h-5 border-2 border-gray-300 border-t-gray-600 dark:border-gray-700 dark:border-t-gray-400 rounded-full animate-spin"></div>
	</div>
{:else if authState === 'needs_setup' || authState === 'needs_login'}
	<!-- Auth screen -->
	<AuthScreen
		mode={authMode}
		needsSetup={authState === 'needs_setup'}
		{signupEnabled}
		token={startupToken}
		onauth={handleAuth}
	/>
{:else if $stateLoaded}
	<div class="flex overflow-hidden font-sans antialiased text-gray-900 bg-white dark:text-gray-100 dark:bg-black" style="height: {viewportHeight};">
		<Sidebar />

		<div class="flex flex-col flex-1 min-w-0">
			{#if !$currentWorkspace}
				<Bar />
			{/if}
			<main class="relative flex-1 min-h-0 overflow-hidden">
				{@render children()}
			</main>

			{#if $currentWorkspace && $isGitRepo && !$gitReviewOpen}
				<GitBar />
			{/if}

			{#if $activeTab?.type === 'terminal'}
				<ShortcutBar />
			{/if}
		</div>
	</div>

	{#if showQuickOpen}
		<QuickOpen onclose={() => showQuickOpen = false} />
	{/if}
{:else}
	<div class="flex items-center justify-center h-dvh bg-white dark:bg-black">
		<div class="w-5 h-5 border-2 border-gray-300 border-t-gray-600 dark:border-gray-700 dark:border-t-gray-400 rounded-full animate-spin"></div>
	</div>
{/if}

<Toaster
	position="bottom-center"
	toastOptions={{
		style: 'font-size: 12px; font-family: var(--font-sans); background: #111; color: #e0e0e0; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;'
	}}
/>
