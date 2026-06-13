<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Icon from '../Icon.svelte';
	import Modal from '../Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { onMount } from 'svelte';
	import {
		listToolServers,
		createToolServer,
		updateToolServer,
		deleteToolServer,
		verifyToolServer,
		type ToolServer
	} from '$lib/apis/admin';
	import { t } from '$lib/i18n';

	let servers = $state<ToolServer[]>([]);
	let loading = $state(true);

	// Modal state
	let showModal = $state(false);
	let editServer = $state<ToolServer | null>(null);

	// Form state
	let formId = $state('');
	let formType = $state<'openapi' | 'mcp'>('openapi');
	let formUrl = $state('');
	let formPath = $state('openapi.json');
	let formAuthType = $state('bearer');
	let formKey = $state('');
	let formName = $state('');
	let formDescription = $state('');
	let formHeaders = $state('');

	let saving = $state(false);
	let verifying = $state(false);

	// Verify result
	let verifyResult = $state<{ ok: boolean; tools?: any[]; message?: string } | null>(null);

	async function load() {
		try {
			servers = await listToolServers();
		} catch {
			toast.error($t('toolServers.loadError'));
		} finally {
			loading = false;
		}
	}

	function openCreate() {
		editServer = null;
		formId = '';
		formType = 'openapi';
		formUrl = '';
		formPath = 'openapi.json';
		formAuthType = 'bearer';
		formKey = '';
		formName = '';
		formDescription = '';
		formHeaders = '';

		verifyResult = null;
		showModal = true;
	}

	function openEdit(s: ToolServer) {
		editServer = s;
		formId = s.id;
		formType = s.type;
		formUrl = s.url;
		formPath = s.path;
		formAuthType = s.auth_type;
		formKey = '';
		formName = s.name;
		formDescription = s.description;
		formHeaders = s.headers ? JSON.stringify(s.headers, null, 2) : '';

		verifyResult = null;
		showModal = true;
	}

	async function handleSubmit() {
		if (!formId.trim() || !formUrl.trim()) {
			toast.error($t('toolServers.fieldsRequired'));
			return;
		}
		if (/[^a-z0-9_]/.test(formId.trim())) {
			toast.error($t('toolServers.idInvalid'));
			return;
		}
		let parsedHeaders: Record<string, string> | undefined;
		if (formHeaders.trim()) {
			try {
				parsedHeaders = JSON.parse(formHeaders);
				if (typeof parsedHeaders !== 'object' || Array.isArray(parsedHeaders)) throw 0;
			} catch {
				toast.error($t('toolServers.headersInvalid'));
				return;
			}
		}
		saving = true;
		try {
			const data: Record<string, unknown> = {
				id: formId.trim(),
				type: formType,
				url: formUrl.trim(),
				path: formPath,
				auth_type: formAuthType,
				name:
					formName.trim() ||
					(() => {
						try {
							return new URL(formUrl.trim()).hostname;
						} catch {
							return formType;
						}
					})(),
				description: formDescription.trim(),
				headers: parsedHeaders || null
			};
			if (editServer) {
				if (formKey.trim()) data.key = formKey.trim();
				await updateToolServer(editServer.id, data as any);
				toast.success($t('toolServers.updated'));
			} else {
				data.key = formKey.trim();
				await createToolServer(data as any);
				toast.success($t('toolServers.created'));
			}
			showModal = false;
			load();
		} catch {
			toast.error($t('toolServers.saveFailed'));
		} finally {
			saving = false;
		}
	}

	async function handleDelete() {
		if (!editServer) return;
		try {
			await deleteToolServer(editServer.id);
			toast.success($t('toolServers.deleted'));
			showModal = false;
			load();
		} catch {
			toast.error($t('toolServers.deleteFailed'));
		}
	}

	async function handleVerify() {
		if (!editServer) return;
		verifying = true;
		verifyResult = null;
		try {
			verifyResult = await verifyToolServer(editServer.id);
			if (verifyResult.ok) toast.success($t('toolServers.connected'));
			else toast.error(verifyResult.message || 'Connection failed');
		} catch (e: any) {
			verifyResult = { ok: false, message: e?.message || 'Connection failed' };
			toast.error(verifyResult.message!);
		} finally {
			verifying = false;
		}
	}

	async function toggleEnabled(e: Event, s: ToolServer) {
		e.stopPropagation();
		const newVal = !s.enabled;
		s.enabled = newVal;
		servers = [...servers];
		try {
			await updateToolServer(s.id, { enabled: newVal });
		} catch {
			s.enabled = !newVal;
			servers = [...servers];
			toast.error($t('toolServers.saveFailed'));
		}
	}

	onMount(load);
</script>

<div class="flex items-center justify-between mb-4">
	<h2 class="text-sm font-medium text-gray-900 dark:text-white">{$t('toolServers.title')}</h2>
	<button
		class="flex items-center justify-center w-6 h-6 rounded-lg text-gray-400 hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300 transition-colors duration-75"
		onclick={() => openCreate()}
	>
		<Icon name="plus" size={14} />
	</button>
</div>

{#if loading}
	<div class="flex justify-center py-8">
		<Spinner size={16} />
	</div>
{:else}
	<div>
		{#each servers as s}
			<button
				class="group flex items-center gap-2 w-full h-7 text-left"
				onclick={() => openEdit(s)}
			>
				<span
					class="text-[10px] font-mono shrink-0
					{s.type === 'mcp'
						? 'text-purple-500 dark:text-purple-400'
						: 'text-blue-500 dark:text-blue-400'}"
				>
					{s.type === 'mcp' ? 'MCP' : 'API'}
				</span>
				<span
					class="flex-1 text-[13px] truncate
					{s.enabled ? 'text-gray-700 dark:text-gray-300' : 'text-gray-400 dark:text-gray-600'}"
				>
					{s.name || s.url}
				</span>
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<span
					class="relative w-6 h-3.5 rounded-full shrink-0 cursor-pointer transition-colors duration-150
						{s.enabled ? 'bg-gray-900 dark:bg-white' : 'bg-gray-200 dark:bg-gray-700'}"
					role="switch"
					tabindex="-1"
					aria-checked={s.enabled}
					onclick={(e) => toggleEnabled(e, s)}
					onkeydown={(e) => {
						if (e.key === 'Enter' || e.key === ' ') {
							e.preventDefault();
							toggleEnabled(e, s);
						}
					}}
				>
					<span
						class="absolute top-0.5 w-2.5 h-2.5 rounded-full transition-all duration-150
						{s.enabled ? 'left-3 bg-white dark:bg-gray-900' : 'left-0.5 bg-white dark:bg-gray-500'}"
					></span>
				</span>
			</button>
		{/each}

		{#if servers.length === 0}
			<p class="text-[13px] text-gray-400 dark:text-gray-600 py-4">
				{$t('toolServers.empty')}
			</p>
		{/if}
	</div>
{/if}

{#if showModal}
	<Modal onclose={() => (showModal = false)} class="w-full max-w-md mx-4">
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="p-4"
			onkeydown={(e) => {
				if (e.key === 'Enter' && formUrl.trim()) handleSubmit();
			}}
		>
			<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-3">
				{editServer ? $t('toolServers.edit') : $t('toolServers.add')}
			</h2>

			<!-- ID + Type -->
			<div class="flex gap-3">
				<div class="flex-1">
					<label class="text-[10px] text-gray-400 dark:text-gray-600"
						>{$t('toolServers.id')}</label
					>
					<input
						type="text"
						placeholder="my_server"
						bind:value={formId}
						autofocus
						autocomplete="off"
						spellcheck="false"
						disabled={!!editServer}
						class="block w-full bg-transparent text-[13px] text-gray-700 dark:text-gray-300 placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-none py-0.5 font-mono disabled:opacity-50"
					/>
				</div>
				<div class="w-28 shrink-0">
					<label class="text-[10px] text-gray-400 dark:text-gray-600"
						>{$t('toolServers.type')}</label
					>
					<select
						bind:value={formType}
						class="block w-full bg-transparent text-[13px] text-gray-700 dark:text-gray-300 outline-none py-0.5 cursor-pointer"
					>
						<option value="openapi">OpenAPI</option>
						<option value="mcp">MCP</option>
					</select>
				</div>
			</div>

			<!-- Name -->
			<label class="text-[10px] text-gray-400 dark:text-gray-600 mt-2"
				>{$t('toolServers.name')}</label
			>
			<input
				type="text"
				placeholder="Optional display name"
				bind:value={formName}
				autocomplete="off"
				spellcheck="false"
				class="block w-full bg-transparent text-[13px] text-gray-700 dark:text-gray-300 placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-none py-0.5"
			/>

			<!-- URL -->
			<label class="text-[10px] text-gray-400 dark:text-gray-600 mt-2"
				>{$t('toolServers.url')}</label
			>
			<input
				type="text"
				placeholder={formType === 'mcp'
					? 'https://mcp.example.com/mcp'
					: 'https://api.example.com'}
				bind:value={formUrl}
				autocomplete="off"
				spellcheck="false"
				class="block w-full bg-transparent text-[13px] text-gray-700 dark:text-gray-300 placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-none py-0.5 font-mono"
			/>

			<!-- Spec path (OpenAPI only) -->
			{#if formType === 'openapi'}
				<label class="text-[10px] text-gray-400 dark:text-gray-600 mt-2"
					>{$t('toolServers.specPath')}</label
				>
				<input
					type="text"
					placeholder="openapi.json"
					bind:value={formPath}
					autocomplete="off"
					spellcheck="false"
					class="block w-full bg-transparent text-[13px] text-gray-700 dark:text-gray-300 placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-none py-0.5 font-mono"
				/>
			{/if}

			<!-- Auth -->
			<div class="flex gap-3 mt-2">
				<div class="w-28 shrink-0">
					<label class="text-[10px] text-gray-400 dark:text-gray-600"
						>{$t('toolServers.auth')}</label
					>
					<select
						bind:value={formAuthType}
						class="block w-full bg-transparent text-[13px] text-gray-700 dark:text-gray-300 outline-none py-0.5 cursor-pointer"
					>
						<option value="none">{$t('toolServers.authNone')}</option>
						<option value="bearer">{$t('toolServers.authBearer')}</option>
					</select>
				</div>
				{#if formAuthType === 'bearer'}
					<div class="flex-1">
						<label class="text-[10px] text-gray-400 dark:text-gray-600"
							>{$t('toolServers.apiKey')}</label
						>
						<input
							type="password"
							placeholder={editServer ? '••••••••  (leave blank to keep)' : 'sk-...'}
							bind:value={formKey}
							autocomplete="new-password"
							class="block w-full bg-transparent text-[13px] text-gray-700 dark:text-gray-300 placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-none py-0.5 font-mono"
						/>
					</div>
				{/if}
			</div>

			<!-- Description -->
			<label class="text-[10px] text-gray-400 dark:text-gray-600 mt-2"
				>{$t('toolServers.description')}</label
			>
			<input
				type="text"
				placeholder={$t('toolServers.descriptionPlaceholder')}
				bind:value={formDescription}
				autocomplete="off"
				spellcheck="false"
				class="block w-full bg-transparent text-[13px] text-gray-700 dark:text-gray-300 placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-none py-0.5"
			/>

			<!-- Headers -->
			<label class="text-[10px] text-gray-400 dark:text-gray-600 mt-2"
				>{$t('toolServers.headers')}</label
			>
			<p class="text-[10px] text-gray-300 dark:text-gray-700 mb-0.5">{$t('toolServers.headersHint')}</p>
			<textarea
				placeholder={'{"X-Custom-Header": "value"}'}
				bind:value={formHeaders}
				autocomplete="off"
				spellcheck="false"
				rows="2"
				class="block w-full bg-transparent text-[13px] text-gray-700 dark:text-gray-300 placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-none py-0.5 font-mono resize-none"
			></textarea>


			<!-- Verify result -->
			{#if verifyResult?.ok && verifyResult.tools}
				<div class="mt-2 text-[11px] text-gray-500 dark:text-gray-400">
					{verifyResult.tools.length}
					{$t('toolServers.toolsFound')}:
					<span class="text-gray-400 dark:text-gray-500"
						>{verifyResult.tools.map((t) => t.name).join(', ')}</span
					>
				</div>
			{/if}

			<!-- Actions -->
			<div class="flex items-center justify-between mt-3">
				<div class="flex items-center gap-3">
					{#if editServer}
						<button
							class="text-[13px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-100"
							onclick={handleDelete}>{$t('toolServers.delete')}</button
						>
						<button
							class="text-[13px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-100 disabled:opacity-30"
							disabled={verifying}
							onclick={handleVerify}
						>
							{#if verifying}
								<Spinner size={12} />
							{:else}
								{$t('toolServers.verify')}
							{/if}
						</button>
					{/if}
				</div>
				<button
					disabled={saving || !formUrl.trim()}
					onclick={handleSubmit}
					class="text-[13px] text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors duration-100 disabled:opacity-30 disabled:pointer-events-none"
				>
					{#if saving}
						<Spinner size={14} />
					{:else if editServer}
						{$t('settings.save')} →
					{:else}
						{$t('toolServers.add')} →
					{/if}
				</button>
			</div>
		</div>
	</Modal>
{/if}
