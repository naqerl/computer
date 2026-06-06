<script lang="ts">

	interface Props {
		language: string;
		code: string;
		/** Optional diff-style callbacks for chat tool approval */
		onapply?: ((code: string) => void) | undefined;
		onreject?: (() => void) | undefined;
	}

	let { language, code, onapply, onreject }: Props = $props();

	let codeEl: HTMLElement | undefined = $state();
	let highlighted = $state(false);
	let copied = $state(false);

	// Detect diff blocks
	let isDiff = $derived(language === 'diff');

	// Parse diff lines for coloring
	let diffLines = $derived.by(() => {
		if (!isDiff) return [];
		return code.split('\n').map(line => ({
			text: line,
			type: line.startsWith('+') ? 'add' as const
				: line.startsWith('-') ? 'del' as const
				: line.startsWith('@@') ? 'range' as const
				: 'ctx' as const,
		}));
	});

	// Cache hljs module
	let hljsModule: any = null;

	// Highlight non-diff code: reactive so it re-runs on prop changes (streaming)
	$effect(() => {
		if (isDiff || !codeEl) return;
		const currentCode = code;
		const currentLang = language;

		(async () => {
			try {
				if (!hljsModule) {
					hljsModule = (await import('highlight.js')).default;
				}
				if (codeEl && currentCode === code) {
					if (currentLang && hljsModule.getLanguage(currentLang)) {
						codeEl.innerHTML = hljsModule.highlight(currentCode, { language: currentLang }).value;
					} else {
						codeEl.innerHTML = hljsModule.highlightAuto(currentCode).value;
					}
					highlighted = true;
				}
			} catch {
				// Fallback: just show plain text
			}
		})();
	});

	function handleCopy() {
		navigator.clipboard.writeText(code);
		copied = true;
		setTimeout(() => { copied = false; }, 2000);
	}
</script>

<div class="code-block">
	<div class="code-header">
		<span class="code-lang">{language || 'text'}</span>
		<div class="code-actions">
			{#if isDiff && onapply}
				<button class="code-action apply" onclick={() => onapply?.(code)}>Apply</button>
				<button class="code-action reject" onclick={() => onreject?.()}>Reject</button>
			{/if}
			<button class="code-action copy" onclick={handleCopy}>
				{copied ? '✓' : 'Copy'}
			</button>
		</div>
	</div>

	{#if isDiff}
		<pre class="code-pre diff"><code>{#each diffLines as line}<span class="diff-line diff-{line.type}">{line.text}
</span>{/each}</code></pre>
	{:else}
		<pre class="code-pre"><code bind:this={codeEl}>{code}</code></pre>
	{/if}
</div>

<style>
	@reference "../../../app.css";

	.code-block {
		border-radius: 8px;
		overflow: hidden;
		background: var(--color-gray-100);
		border: 1px solid var(--color-gray-200);
	}

	:global(.dark) .code-block {
		background: rgba(255, 255, 255, 0.03);
		border-color: rgba(255, 255, 255, 0.06);
	}

	.code-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		height: 30px;
		padding: 0 10px;
		border-bottom: 1px solid var(--color-gray-200);
		background: var(--color-gray-50);
	}

	:global(.dark) .code-header {
		border-bottom-color: rgba(255, 255, 255, 0.06);
		background: rgba(255, 255, 255, 0.02);
	}

	.code-lang {
		font-size: 11px;
		font-weight: 500;
		color: var(--color-gray-500);
		text-transform: lowercase;
	}

	.code-actions {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.code-action {
		font-size: 11px;
		padding: 2px 8px;
		border-radius: 4px;
		color: var(--color-gray-500);
		transition: all 0.1s;
	}

	.code-action:hover {
		color: var(--color-gray-700);
		background: var(--color-gray-200);
	}

	:global(.dark) .code-action:hover {
		color: var(--color-gray-300);
		background: rgba(255, 255, 255, 0.08);
	}

	.code-action.apply {
		color: #16a34a;
	}

	.code-action.apply:hover {
		background: rgba(22, 163, 74, 0.1);
	}

	.code-action.reject {
		color: #dc2626;
	}

	.code-action.reject:hover {
		background: rgba(220, 38, 38, 0.1);
	}

	.code-pre {
		margin: 0;
		padding: 12px 16px;
		overflow-x: auto;
		font-size: 13px;
		line-height: 1.5;
		font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
	}

	.code-pre code {
		font-family: inherit;
	}

	/* ── Diff line coloring ──────────────────────── */

	.diff-line {
		display: block;
	}

	.diff-line.diff-add {
		background: rgba(22, 163, 74, 0.1);
		color: #16a34a;
	}

	:global(.dark) .diff-line.diff-add {
		background: rgba(34, 197, 94, 0.1);
		color: #4ade80;
	}

	.diff-line.diff-del {
		background: rgba(220, 38, 38, 0.08);
		color: #dc2626;
	}

	:global(.dark) .diff-line.diff-del {
		background: rgba(248, 113, 113, 0.1);
		color: #f87171;
	}

	.diff-line.diff-range {
		color: #8b5cf6;
	}

	:global(.dark) .diff-line.diff-range {
		color: #a78bfa;
	}

	/* ── highlight.js token colors ────────────────── */

	.code-pre :global(.hljs-keyword),
	.code-pre :global(.hljs-selector-tag),
	.code-pre :global(.hljs-built_in) {
		color: #d73a49;
	}

	.code-pre :global(.hljs-string),
	.code-pre :global(.hljs-attr) {
		color: #032f62;
	}

	.code-pre :global(.hljs-comment),
	.code-pre :global(.hljs-quote) {
		color: #6a737d;
		font-style: italic;
	}

	.code-pre :global(.hljs-number),
	.code-pre :global(.hljs-literal) {
		color: #005cc5;
	}

	.code-pre :global(.hljs-title),
	.code-pre :global(.hljs-section) {
		color: #6f42c1;
	}

	.code-pre :global(.hljs-type),
	.code-pre :global(.hljs-name) {
		color: #22863a;
	}

	.code-pre :global(.hljs-meta) {
		color: #735c0f;
	}

	/* Dark mode hljs overrides */

	:global(.dark) .code-pre :global(.hljs-keyword),
	:global(.dark) .code-pre :global(.hljs-selector-tag),
	:global(.dark) .code-pre :global(.hljs-built_in) {
		color: #ff7b72;
	}

	:global(.dark) .code-pre :global(.hljs-string),
	:global(.dark) .code-pre :global(.hljs-attr) {
		color: #a5d6ff;
	}

	:global(.dark) .code-pre :global(.hljs-comment),
	:global(.dark) .code-pre :global(.hljs-quote) {
		color: #8b949e;
	}

	:global(.dark) .code-pre :global(.hljs-number),
	:global(.dark) .code-pre :global(.hljs-literal) {
		color: #79c0ff;
	}

	:global(.dark) .code-pre :global(.hljs-title),
	:global(.dark) .code-pre :global(.hljs-section) {
		color: #d2a8ff;
	}

	:global(.dark) .code-pre :global(.hljs-type),
	:global(.dark) .code-pre :global(.hljs-name) {
		color: #7ee787;
	}

	:global(.dark) .code-pre :global(.hljs-meta) {
		color: #d29922;
	}
</style>
