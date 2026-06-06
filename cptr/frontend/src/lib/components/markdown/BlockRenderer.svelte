<script lang="ts">
	import { type Token, type Tokens } from 'marked';

	import CodeBlock from './CodeBlock.svelte';
	import MermaidBlock from './MermaidBlock.svelte';
	import InlineRenderer from './InlineRenderer.svelte';

	interface Props {
		tokens: Token[];
	}

	let { tokens }: Props = $props();
</script>

{#each tokens as token}
	{#if token.type === 'heading'}
		{@const h = token as Tokens.Heading}
		<svelte:element this={`h${h.depth}`}>
			<InlineRenderer items={h.tokens} />
		</svelte:element>

	{:else if token.type === 'paragraph'}
		<p><InlineRenderer items={(token as Tokens.Paragraph).tokens} /></p>

	{:else if token.type === 'code'}
		{#if (token as Tokens.Code).lang === 'mermaid'}
			<MermaidBlock code={(token as Tokens.Code).text} />
		{:else}
			<CodeBlock language={(token as Tokens.Code).lang ?? ''} code={(token as Tokens.Code).text} />
		{/if}

	{:else if token.type === 'blockquote'}
		<blockquote>
			<svelte:self tokens={(token as Tokens.Blockquote).tokens} />
		</blockquote>

	{:else if token.type === 'list'}
		{@const list = token as Tokens.List}
		<svelte:element this={list.ordered ? 'ol' : 'ul'} start={list.ordered ? list.start : undefined}>
			{#each list.items as item}
				<li>
					{#if item.task}
						<input type="checkbox" checked={item.checked} disabled />
					{/if}
					{#if item.tokens}
						<svelte:self tokens={item.tokens} />
					{/if}
				</li>
			{/each}
		</svelte:element>

	{:else if token.type === 'table'}
		{@const table = token as Tokens.Table}
		<table>
			<thead>
				<tr>
					{#each table.header as cell, i}
						<th style={table.align[i] ? `text-align:${table.align[i]}` : ''}>
							<InlineRenderer items={cell.tokens} />
						</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each table.rows as row}
					<tr>
						{#each row as cell, i}
							<td style={table.align[i] ? `text-align:${table.align[i]}` : ''}>
								<InlineRenderer items={cell.tokens} />
							</td>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>

	{:else if token.type === 'hr'}
		<hr class="border-gray-100/60 dark:border-gray-850/40" />

	{:else if token.type === 'text'}
		{#if 'tokens' in token && token.tokens}
			<InlineRenderer items={token.tokens} />
		{:else}
			{token.raw}
		{/if}

	{:else if token.type === 'html'}
		<!-- Skip raw HTML for safety -->

	{:else if token.type === 'def'}
		<!-- Link reference definition, no visual output -->

	{:else if token.type === 'space'}
		<!-- skip -->
	{/if}
{/each}
