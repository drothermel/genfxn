<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { codeToHtml } from 'shiki';

	interface Props {
		code: string;
	}

	let { code }: Props = $props();
	let highlightedHtml: string = $state('');

	onMount(async () => {
		highlightedHtml = await codeToHtml(code, {
			lang: 'python',
			theme: 'github-light'
		});
	});
</script>

<Card>
	<CardHeader>
		<CardTitle>Generated Code</CardTitle>
	</CardHeader>
	<CardContent>
		{#if highlightedHtml}
			<div class="overflow-x-auto rounded-lg border bg-gray-50 p-4 text-sm">
				{@html highlightedHtml}
			</div>
		{:else}
			<pre class="overflow-x-auto rounded-lg border bg-gray-50 p-4 text-sm">{code}</pre>
		{/if}
	</CardContent>
</Card>
