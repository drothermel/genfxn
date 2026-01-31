<script lang="ts">
	import type { GenerationTrace } from '$lib/types';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { ChevronRight } from 'lucide-svelte';

	interface Props {
		trace: GenerationTrace;
	}

	let { trace }: Props = $props();

	let expandedSteps: Set<number> = $state(new Set());

	function toggleStep(index: number) {
		if (expandedSteps.has(index)) {
			expandedSteps.delete(index);
		} else {
			expandedSteps.add(index);
		}
		expandedSteps = new Set(expandedSteps);
	}

	function formatValue(value: unknown): string {
		return JSON.stringify(value, null, 2);
	}
</script>

<Card>
	<CardHeader>
		<CardTitle>Generation Trace</CardTitle>
		<p class="text-sm text-gray-500">{trace.steps.length} steps</p>
	</CardHeader>
	<CardContent>
		<div class="space-y-2">
			{#each trace.steps as step, i}
				<div class="rounded-lg border bg-gray-50">
					<button
						class="flex w-full items-start gap-3 p-3 text-left hover:bg-gray-100"
						onclick={() => toggleStep(i)}
					>
						<span
							class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gray-200 text-xs font-medium"
						>
							{i + 1}
						</span>
						<div class="min-w-0 flex-1">
							<div class="font-mono text-xs text-gray-500">{step.step}</div>
							<div class="text-sm">{step.choice}</div>
						</div>
						<ChevronRight
							class="h-4 w-4 flex-shrink-0 text-gray-400 transition-transform {expandedSteps.has(
								i
							)
								? 'rotate-90'
								: ''}"
						/>
					</button>
					{#if expandedSteps.has(i)}
						<div class="border-t bg-white p-3">
							<pre class="overflow-x-auto text-xs text-gray-700">{formatValue(step.value)}</pre>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	</CardContent>
</Card>
