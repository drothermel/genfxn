<script lang="ts">
	import type { Task } from '$lib/types';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';

	interface Props {
		task: Task;
	}

	let { task }: Props = $props();

	const template = $derived(task.spec.template as string | undefined);

	function getDifficultyColor(difficulty: number): string {
		const colors: Record<number, string> = {
			1: 'bg-green-100 text-green-800',
			2: 'bg-lime-100 text-lime-800',
			3: 'bg-yellow-100 text-yellow-800',
			4: 'bg-orange-100 text-orange-800',
			5: 'bg-red-100 text-red-800'
		};
		return colors[difficulty] || 'bg-gray-100 text-gray-800';
	}
</script>

<Card>
	<CardHeader>
		<CardTitle>Metadata</CardTitle>
	</CardHeader>
	<CardContent>
		<dl class="grid grid-cols-2 gap-4 text-sm">
			<div>
				<dt class="font-medium text-gray-500">Task ID</dt>
				<dd class="mt-1 font-mono">{task.task_id}</dd>
			</div>
			<div>
				<dt class="font-medium text-gray-500">Family</dt>
				<dd class="mt-1">
					<Badge variant="secondary">{task.family}</Badge>
				</dd>
			</div>
			{#if template}
				<div>
					<dt class="font-medium text-gray-500">Template</dt>
					<dd class="mt-1">
						<Badge variant="outline">{template}</Badge>
					</dd>
				</div>
			{/if}
			{#if task.difficulty != null}
				<div>
					<dt class="font-medium text-gray-500">Difficulty</dt>
					<dd class="mt-1">
						<span
							class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {getDifficultyColor(
								task.difficulty
							)}"
						>
							{task.difficulty}/5
						</span>
					</dd>
				</div>
			{/if}
			<div>
				<dt class="font-medium text-gray-500">Queries</dt>
				<dd class="mt-1">{task.queries.length}</dd>
			</div>
		</dl>
	</CardContent>
</Card>
