<script lang="ts">
	import { page } from '$app/stores';
	import AutomationsPanel from '$lib/components/automations/AutomationsPanel.svelte';

	const automationId = $derived($page.params.id);
</script>

<svelte:head>
	<title>Automation / cptr</title>
</svelte:head>

<AutomationsPanel {automationId} />
