<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Editor } from '@tiptap/core';
	import StarterKit from '@tiptap/starter-kit';
	import { Markdown } from '@tiptap/markdown';
	import Placeholder from '@tiptap/extension-placeholder';
	import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
	import { all, createLowlight } from 'lowlight';

	import ModelSelector from './ModelSelector.svelte';
	import SendButton from './SendButton.svelte';
	import PlusMenu from './PlusMenu.svelte';
	import DictateButton from './DictateButton.svelte';

	interface Props {
		inputText: string;
		selectedModel: string;
		sending: boolean;
		streaming?: boolean;
		placeholder?: string;
		onsend: () => void;
		oncancel?: () => void;
	}
	let {
		inputText = $bindable(),
		selectedModel = $bindable(),
		sending,
		streaming = false,
		placeholder = 'Message...',
		onsend,
		oncancel,
	}: Props = $props();

	let editorEl: HTMLDivElement | undefined = $state();
	let editor: Editor | null = $state(null);

	// ── Lowlight setup ──────────────────────────────
	const lowlight = createLowlight(all);
	const _origHighlight = lowlight.highlight.bind(lowlight);
	lowlight.highlight = (lang: string, value: string, opts?: Record<string, unknown>) => {
		if (!lowlight.registered(lang)) return lowlight.highlightAuto(value);
		return _origHighlight(lang, value, opts);
	};

	// ── Editor lifecycle ────────────────────────────
	onMount(() => {
		if (!editorEl) return;

		editor = new Editor({
			element: editorEl,
			extensions: [
				StarterKit.configure({
					codeBlock: false,
					heading: { levels: [1, 2, 3] },
				}),
				Markdown,
				Placeholder.configure({ placeholder }),
				CodeBlockLowlight.configure({ lowlight }),
			],
			content: inputText || '',
			contentType: inputText ? 'markdown' : undefined,
			autofocus: true,
			editorProps: {
				attributes: {
					class: 'chat-prosemirror',
					spellcheck: 'true',
				},
				handleKeyDown: (view, event) => {
					if (event.key === 'Enter' && !event.shiftKey) {
						const { state } = view;
						const head = state.selection.$head;

						let inside = false;
						for (let d = head.depth; d > 0; d--) {
							const name = head.node(d).type.name;
							if (['codeBlock', 'bulletList', 'orderedList', 'listItem'].includes(name)) {
								inside = true;
								break;
							}
						}
						if (!inside) {
							event.preventDefault();
							onsend();
							return true;
						}
					}
					return false;
				},
			},
			onUpdate: ({ editor: e }) => {
				inputText = (e as any).getMarkdown() || '';
			},
		});
	});

	onDestroy(() => {
		editor?.destroy();
		editor = null;
	});

	// Sync external inputText changes (e.g. cleared after send)
	$effect(() => {
		if (!editor || editor.isDestroyed) return;
		const editorMd = (editor as any).getMarkdown() || '';
		if (inputText !== editorMd) {
			if (inputText === '') {
				editor.commands.clearContent();
			} else {
				editor.commands.setContent(inputText);
			}
		}
	});

	export function focus() {
		editor?.commands.focus();
	}

	export function resetHeight() {
		// TipTap auto-sizes; no-op kept for API compat
	}

	const canSend = $derived(inputText.trim() && selectedModel && !sending);
</script>

<div class="relative">
	<div class="rounded-3xl shadow-lg border border-gray-100/40 dark:border-white/4 focus-within:border-gray-200/50 focus-within:dark:border-white/8 transition px-1 bg-white dark:bg-gray-500/5">
		<!-- Editor area -->
		<div class="px-2.5">
			<div
				bind:this={editorEl}
				class="chat-editor-mount scrollbar-hidden"
				class:opacity-50={sending}
				class:pointer-events-none={sending}
			></div>
		</div>

		<!-- Toolbar. stopPropagation prevents TipTap from stealing focus -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="flex items-center justify-between mt-0.5 mb-2.5 mx-0.5"
			onmousedown={(e) => e.stopPropagation()}
		>
			<div class="ml-0.5 self-end flex items-center">
				<PlusMenu onfiles={(files) => { /* TODO: handle file uploads */ }} />
			</div>
			<div class="self-end mr-1 flex items-center gap-2">
				<ModelSelector bind:selectedModel />
				<DictateButton ontext={(text) => { inputText += text; }} />
				<SendButton {canSend} {streaming} {onsend} {oncancel} />
			</div>
		</div>
	</div>
</div>

<style>
	@reference "../../../app.css";

	/* ── ProseMirror editor ───────────────────────── */

	.chat-editor-mount :global(.chat-prosemirror) {
		@apply pt-2.5 pb-2 px-1 min-h-6 max-h-96 overflow-y-auto text-sm leading-relaxed text-gray-900 dark:text-gray-100 outline-none break-words;
	}

	/* Placeholder */
	.chat-editor-mount :global(.chat-prosemirror p.is-editor-empty:first-child::before) {
		content: attr(data-placeholder);
		@apply float-left text-gray-400 dark:text-gray-600 pointer-events-none h-0;
	}

	/* Paragraphs */
	.chat-editor-mount :global(.chat-prosemirror p) {
		@apply mb-1;
	}
	.chat-editor-mount :global(.chat-prosemirror p:last-child) {
		@apply mb-0;
	}

	/* Lists */
	.chat-editor-mount :global(.chat-prosemirror ul),
	.chat-editor-mount :global(.chat-prosemirror ol) {
		@apply mb-1 pl-4.5 text-sm;
	}
	.chat-editor-mount :global(.chat-prosemirror li) {
		@apply my-0.5;
	}
	.chat-editor-mount :global(.chat-prosemirror li > p) {
		@apply mb-0.5;
	}

	/* Inline code */
	.chat-editor-mount :global(.chat-prosemirror code) {
		@apply bg-gray-100 dark:bg-white/8 rounded-sm px-1 py-px text-xs font-mono;
	}

	/* Code blocks */
	.chat-editor-mount :global(.chat-prosemirror pre) {
		@apply bg-gray-100 dark:bg-white/4 rounded-md px-3 py-2 overflow-x-auto my-1 text-xs font-mono;
	}
	.chat-editor-mount :global(.chat-prosemirror pre code) {
		@apply bg-transparent p-0 rounded-none text-inherit;
	}

	/* Blockquote */
	.chat-editor-mount :global(.chat-prosemirror blockquote) {
		@apply my-1 py-0.5 pl-3 border-l-2 border-gray-300 dark:border-white/12 text-gray-500 dark:text-gray-400;
	}

	/* Strong */
	.chat-editor-mount :global(.chat-prosemirror strong) {
		@apply font-semibold;
	}

	/* Headings */
	.chat-editor-mount :global(.chat-prosemirror h1) { @apply text-base font-semibold my-1; }
	.chat-editor-mount :global(.chat-prosemirror h2) { @apply text-sm font-semibold my-1; }
	.chat-editor-mount :global(.chat-prosemirror h3) { @apply text-[13px] font-semibold my-1; }

	/* HR */
	.chat-editor-mount :global(.chat-prosemirror hr) {
		@apply border-none border-t border-gray-200 dark:border-white/8 my-2;
	}

	/* Syntax highlighting */
	.chat-editor-mount :global(.hljs-keyword) { color: #c678dd; }
	.chat-editor-mount :global(.hljs-string) { color: #98c379; }
	.chat-editor-mount :global(.hljs-number) { color: #d19a66; }
	.chat-editor-mount :global(.hljs-comment) { color: #5c6370; font-style: italic; }
	.chat-editor-mount :global(.hljs-function) { color: #61afef; }
	.chat-editor-mount :global(.hljs-title) { color: #61afef; }
	.chat-editor-mount :global(.hljs-built_in) { color: #e5c07b; }
</style>
