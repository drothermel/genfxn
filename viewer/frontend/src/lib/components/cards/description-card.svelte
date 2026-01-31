<script lang="ts">
	import type { Task } from '$lib/types';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';

	interface Props {
		task: Task;
	}

	let { task }: Props = $props();
</script>

{#if task.description}
	<Card>
		<CardHeader>
			<CardTitle>Description</CardTitle>
		</CardHeader>
		<CardContent>
			<p class="text-sm leading-relaxed text-gray-700">{task.description}</p>
		</CardContent>
	</Card>
{/if}
