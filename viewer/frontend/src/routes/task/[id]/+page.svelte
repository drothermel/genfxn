<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { fetchTask } from '$lib/api';
	import type { Task } from '$lib/types';
	import { Card, CardContent } from '$lib/components/ui/card';
	import MetadataCard from '$lib/components/cards/metadata-card.svelte';
	import TraceCard from '$lib/components/cards/trace-card.svelte';
	import CodeCard from '$lib/components/cards/code-card.svelte';
	import QueriesCard from '$lib/components/cards/queries-card.svelte';
	import SpecCard from '$lib/components/cards/spec-card.svelte';
	import AxesCard from '$lib/components/cards/axes-card.svelte';
	import { ArrowLeft } from 'lucide-svelte';

	let task: Task | null = $state(null);
	let loading = $state(true);
	let error: string | null = $state(null);

	const taskId = $derived(page.params.id);

	onMount(async () => {
		try {
			task = await fetchTask(taskId);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	});
</script>

<div class="container mx-auto max-w-5xl px-4 py-8">
	<div class="mb-6">
		<a href="/" class="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
			<ArrowLeft class="h-4 w-4" />
			Back to tasks
		</a>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="text-muted-foreground">Loading...</div>
		</div>
	{:else if error}
		<Card>
			<CardContent class="py-8 text-center">
				<p class="text-red-500">{error}</p>
			</CardContent>
		</Card>
	{:else if task}
		<header class="mb-8">
			<h1 class="font-mono text-2xl font-bold">{task.task_id}</h1>
		</header>

		<div class="space-y-6">
			<MetadataCard {task} />

			{#if task.axes}
				<AxesCard {task} />
			{/if}

			{#if task.trace}
				<TraceCard trace={task.trace} />
			{/if}

			<SpecCard {task} />

			<CodeCard code={task.code} />

			<QueriesCard queries={task.queries} />
		</div>
	{/if}
</div>
