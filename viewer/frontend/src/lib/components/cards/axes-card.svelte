<script lang="ts">
	import type { Task } from '$lib/types';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';

	interface Props {
		task: Task;
	}

	let { task }: Props = $props();

	const axes = $derived(task.axes);
	const isPiecewise = $derived(task.family === 'piecewise');

	function formatRange(range: unknown): string {
		if (Array.isArray(range) && range.length === 2) {
			return `[${range[0]}, ${range[1]}]`;
		}
		return String(range);
	}

	function formatList(items: unknown): string {
		if (Array.isArray(items)) {
			return items.join(', ');
		}
		return String(items);
	}
</script>

{#if axes}
	<Card>
		<CardHeader>
			<CardTitle>Sampling Axes</CardTitle>
		</CardHeader>
		<CardContent>
			<div class="grid gap-4 sm:grid-cols-2">
				{#if isPiecewise}
					<!-- Piecewise axes -->
					<div class="space-y-3">
						<h4 class="text-sm font-medium text-muted-foreground">Type Constraints</h4>
						<div class="space-y-2 text-sm">
							<div class="flex items-center justify-between">
								<span class="text-muted-foreground">Branches:</span>
								<code class="rounded bg-muted px-2 py-0.5">{axes.n_branches}</code>
							</div>
							<div class="flex items-center justify-between">
								<span class="text-muted-foreground">Expression types:</span>
								<div class="flex flex-wrap gap-1">
									{#each (axes.expr_types as string[]) ?? [] as exprType}
										<Badge variant="secondary">{exprType}</Badge>
									{/each}
								</div>
							</div>
						</div>
					</div>
					<div class="space-y-3">
						<h4 class="text-sm font-medium text-muted-foreground">Numeric Ranges</h4>
						<div class="space-y-2 text-sm">
							<div class="flex items-center justify-between">
								<span class="text-muted-foreground">Value range:</span>
								<code class="rounded bg-muted px-2 py-0.5">{formatRange(axes.value_range)}</code>
							</div>
							<div class="flex items-center justify-between">
								<span class="text-muted-foreground">Threshold range:</span>
								<code class="rounded bg-muted px-2 py-0.5">{formatRange(axes.threshold_range)}</code>
							</div>
							<div class="flex items-center justify-between">
								<span class="text-muted-foreground">Coefficient range:</span>
								<code class="rounded bg-muted px-2 py-0.5">{formatRange(axes.coeff_range)}</code>
							</div>
							<div class="flex items-center justify-between">
								<span class="text-muted-foreground">Divisor range:</span>
								<code class="rounded bg-muted px-2 py-0.5">{formatRange(axes.divisor_range)}</code>
							</div>
						</div>
					</div>
				{:else}
					<!-- Stateful axes -->
					<div class="space-y-3">
						<h4 class="text-sm font-medium text-muted-foreground">Type Constraints</h4>
						<div class="space-y-2 text-sm">
							<div>
								<span class="text-muted-foreground">Templates:</span>
								<div class="mt-1 flex flex-wrap gap-1">
									{#each (axes.templates as string[]) ?? [] as template}
										<Badge variant="secondary">{template}</Badge>
									{/each}
								</div>
							</div>
							<div>
								<span class="text-muted-foreground">Predicate types:</span>
								<div class="mt-1 flex flex-wrap gap-1">
									{#each (axes.predicate_types as string[]) ?? [] as predType}
										<Badge variant="outline">{predType}</Badge>
									{/each}
								</div>
							</div>
							<div>
								<span class="text-muted-foreground">Transform types:</span>
								<div class="mt-1 flex flex-wrap gap-1">
									{#each (axes.transform_types as string[]) ?? [] as transType}
										<Badge variant="outline">{transType}</Badge>
									{/each}
								</div>
							</div>
						</div>
					</div>
					<div class="space-y-3">
						<h4 class="text-sm font-medium text-muted-foreground">Numeric Ranges</h4>
						<div class="space-y-2 text-sm">
							<div class="flex items-center justify-between">
								<span class="text-muted-foreground">Value range:</span>
								<code class="rounded bg-muted px-2 py-0.5">{formatRange(axes.value_range)}</code>
							</div>
							<div class="flex items-center justify-between">
								<span class="text-muted-foreground">List length:</span>
								<code class="rounded bg-muted px-2 py-0.5">{formatRange(axes.list_length_range)}</code>
							</div>
							<div class="flex items-center justify-between">
								<span class="text-muted-foreground">Threshold range:</span>
								<code class="rounded bg-muted px-2 py-0.5">{formatRange(axes.threshold_range)}</code>
							</div>
							<div class="flex items-center justify-between">
								<span class="text-muted-foreground">Divisor range:</span>
								<code class="rounded bg-muted px-2 py-0.5">{formatRange(axes.divisor_range)}</code>
							</div>
							<div class="flex items-center justify-between">
								<span class="text-muted-foreground">Shift range:</span>
								<code class="rounded bg-muted px-2 py-0.5">{formatRange(axes.shift_range)}</code>
							</div>
							<div class="flex items-center justify-between">
								<span class="text-muted-foreground">Scale range:</span>
								<code class="rounded bg-muted px-2 py-0.5">{formatRange(axes.scale_range)}</code>
							</div>
						</div>
					</div>
				{/if}
			</div>
		</CardContent>
	</Card>
{/if}
