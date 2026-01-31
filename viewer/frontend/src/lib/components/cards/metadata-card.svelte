<script lang="ts">
	import type { Task } from '$lib/types';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { getDifficultyColor } from '$lib/helpers/difficulty';

	interface Props {
		task: Task;
	}

	let { task }: Props = $props();

	const template = $derived(task.spec.template as string | undefined);
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
						<Badge class={getDifficultyColor(task.difficulty)}>{task.difficulty}/5</Badge>
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
