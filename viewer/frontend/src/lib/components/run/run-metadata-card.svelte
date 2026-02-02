<script lang="ts">
	import type { RunMeta } from '$lib/types';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';

	interface Props {
		meta: RunMeta;
	}

	let { meta }: Props = $props();

	function formatTimestamp(ts: string | null): string {
		if (!ts) return '-';
		try {
			return new Date(ts).toLocaleString();
		} catch {
			return ts;
		}
	}
</script>

<Card>
	<CardHeader>
		<CardTitle>Metadata</CardTitle>
	</CardHeader>
	<CardContent>
		<dl class="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
			<div>
				<dt class="font-medium text-gray-500">Run ID</dt>
				<dd class="mt-1 font-mono">{meta.run_id}</dd>
			</div>
			<div>
				<dt class="font-medium text-gray-500">Model</dt>
				<dd class="mt-1 font-mono text-xs">{meta.model}</dd>
			</div>
			<div>
				<dt class="font-medium text-gray-500">Tag</dt>
				<dd class="mt-1">
					<Badge variant="secondary">{meta.tag}</Badge>
				</dd>
			</div>
			{#if meta.task}
				<div>
					<dt class="font-medium text-gray-500">Task ID</dt>
					<dd class="mt-1 font-mono text-xs">{meta.task.task_id ?? '-'}</dd>
				</div>
				<div>
					<dt class="font-medium text-gray-500">Task Family</dt>
					<dd class="mt-1">
						{#if meta.task.family}
							<Badge variant="outline">{meta.task.family}</Badge>
						{:else}
							-
						{/if}
					</dd>
				</div>
			{/if}
			{#if meta.prompt_name}
				<div>
					<dt class="font-medium text-gray-500">Prompt</dt>
					<dd class="mt-1 font-mono text-xs">
						{meta.prompt_name}
						{#if meta.prompt_version != null}
							<span class="text-muted-foreground">v{meta.prompt_version}</span>
						{/if}
					</dd>
				</div>
			{/if}
			{#if meta.timestamp_utc}
				<div>
					<dt class="font-medium text-gray-500">Timestamp</dt>
					<dd class="mt-1 text-xs">{formatTimestamp(meta.timestamp_utc)}</dd>
				</div>
			{/if}
			{#if meta.engine}
				<div>
					<dt class="font-medium text-gray-500">Engine</dt>
					<dd class="mt-1">{meta.engine}</dd>
				</div>
			{/if}
		</dl>

		{#if meta.budgets}
			<div class="mt-4 border-t pt-4">
				<h4 class="mb-2 text-sm font-medium text-gray-500">Budgets</h4>
				<dl class="grid grid-cols-3 gap-4 text-sm">
					{#each Object.entries(meta.budgets) as [key, value]}
						<div>
							<dt class="text-xs text-gray-500">{key}</dt>
							<dd class="font-mono">{value}</dd>
						</div>
					{/each}
				</dl>
			</div>
		{/if}

		{#if meta.sampling}
			<div class="mt-4 border-t pt-4">
				<h4 class="mb-2 text-sm font-medium text-gray-500">Sampling</h4>
				<dl class="grid grid-cols-3 gap-4 text-sm">
					{#each Object.entries(meta.sampling) as [key, value]}
						<div>
							<dt class="text-xs text-gray-500">{key}</dt>
							<dd class="font-mono">{value}</dd>
						</div>
					{/each}
				</dl>
			</div>
		{/if}
	</CardContent>
</Card>
