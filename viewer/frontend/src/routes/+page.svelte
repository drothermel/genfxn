<script lang="ts">
	import { fetchTasks, fetchFamilies } from '$lib/api';
	import type { Task } from '$lib/types';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';

	let tasks: Task[] = $state([]);
	let families: string[] = $state([]);
	let selectedFamily: string = $state('');
	let loading = $state(true);
	let error: string | null = $state(null);

	function getDifficultyColor(difficulty: number): string {
		const colors: Record<number, string> = {
			1: 'bg-green-100 text-green-800 border-green-200',
			2: 'bg-lime-100 text-lime-800 border-lime-200',
			3: 'bg-yellow-100 text-yellow-800 border-yellow-200',
			4: 'bg-orange-100 text-orange-800 border-orange-200',
			5: 'bg-red-100 text-red-800 border-red-200'
		};
		return colors[difficulty] || 'bg-gray-100 text-gray-800 border-gray-200';
	}

	async function loadData() {
		loading = true;
		error = null;
		try {
			[families, tasks] = await Promise.all([
				fetchFamilies(),
				fetchTasks(selectedFamily || undefined)
			]);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		// Load on mount and re-fetch when family changes (selectedFamily is read inside loadData)
		loadData();
	});
</script>

<div class="container mx-auto max-w-5xl px-4 py-8">
	<header class="mb-8">
		<h1 class="text-3xl font-bold">genfxn Trace Viewer</h1>
		<p class="mt-2 text-muted-foreground">
			Explore generated function specifications and their traces
		</p>
	</header>

	<div class="mb-6 flex items-center gap-4">
		<label class="flex items-center gap-2 text-sm font-medium">
			Family:
			<select
				bind:value={selectedFamily}
				class="rounded-md border border-input bg-background px-3 py-2 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
			>
				<option value="">All</option>
				{#each families as family}
					<option value={family}>{family}</option>
				{/each}
			</select>
		</label>
		<span class="text-sm text-muted-foreground">
			{tasks.length} task{tasks.length !== 1 ? 's' : ''}
		</span>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="text-muted-foreground">Loading...</div>
		</div>
	{:else if error}
		<Card>
			<CardContent class="py-8 text-center">
				<p class="text-red-500">{error}</p>
				<p class="mt-2 text-sm text-muted-foreground">
					Make sure the backend is running on http://127.0.0.1:8000
				</p>
			</CardContent>
		</Card>
	{:else if tasks.length === 0}
		<Card>
			<CardContent class="py-8 text-center">
				<p class="text-muted-foreground">No tasks found</p>
			</CardContent>
		</Card>
	{:else}
		<div class="space-y-3">
			{#each tasks as task}
				<a href="/task/{task.task_id}" class="block">
					<Card class="transition-shadow hover:shadow-md">
						<CardHeader class="px-6 py-4">
							<div class="flex items-center justify-between">
								<div class="flex items-center gap-3">
									<CardTitle class="font-mono text-base">{task.task_id}</CardTitle>
									<Badge variant="secondary">{task.family}</Badge>
									{#if task.difficulty != null}
										<span
											class="inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium {getDifficultyColor(
												task.difficulty
											)}"
										>
											{task.difficulty}/5
										</span>
									{/if}
								</div>
								<div class="flex items-center gap-2 text-sm text-muted-foreground">
									<span>{task.queries.length} queries</span>
									{#if task.trace}
										<span>• {task.trace.steps.length} steps</span>
									{/if}
								</div>
							</div>
						</CardHeader>
					</Card>
				</a>
			{/each}
		</div>
	{/if}
</div>
