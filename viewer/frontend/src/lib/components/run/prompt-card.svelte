<script lang="ts">
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';

	interface Props {
		taskPrompt: string | null;
		systemPrompt: string | null;
	}

	let { taskPrompt, systemPrompt }: Props = $props();
</script>

<Card>
	<CardHeader>
		<CardTitle>Prompts</CardTitle>
	</CardHeader>
	<CardContent class="space-y-4">
		{#if systemPrompt}
			<div>
				<h4 class="mb-2 text-sm font-medium text-gray-500">System Prompt</h4>
				<pre class="overflow-x-auto whitespace-pre-wrap rounded-lg border bg-gray-50 p-4 text-sm">{systemPrompt}</pre>
			</div>
		{/if}
		{#if taskPrompt}
			<div>
				<h4 class="mb-2 text-sm font-medium text-gray-500">Task Prompt</h4>
				<pre class="overflow-x-auto whitespace-pre-wrap rounded-lg border bg-gray-50 p-4 text-sm">{taskPrompt}</pre>
			</div>
		{/if}
		{#if !systemPrompt && !taskPrompt}
			<p class="text-muted-foreground">No prompts available</p>
		{/if}
	</CardContent>
</Card>
