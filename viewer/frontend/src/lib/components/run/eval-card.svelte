<script lang="ts">
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { CheckCircle, XCircle } from 'lucide-svelte';

	interface Props {
		evalData: Record<string, unknown>;
	}

	let { evalData }: Props = $props();

	const budget = $derived(evalData.budget as Record<string, unknown> | undefined);
	const structure = $derived(evalData.structure as Record<string, unknown> | undefined);
	const noCode = $derived(evalData.no_code as Record<string, unknown> | undefined);
</script>

<Card>
	<CardHeader>
		<CardTitle>Evaluation</CardTitle>
	</CardHeader>
	<CardContent class="space-y-4">
		{#if budget}
			<div>
				<h4 class="mb-2 text-sm font-medium text-gray-500">Budget</h4>
				<dl class="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
					{#if budget.budget_chars != null}
						<div>
							<dt class="text-xs text-gray-500">Budget</dt>
							<dd class="font-mono">{budget.budget_chars} chars</dd>
						</div>
					{/if}
					{#if budget.actual_chars != null}
						<div>
							<dt class="text-xs text-gray-500">Actual</dt>
							<dd class="font-mono">{budget.actual_chars} chars</dd>
						</div>
					{/if}
					{#if budget.budget_delta != null}
						<div>
							<dt class="text-xs text-gray-500">Delta</dt>
							<dd class="font-mono {Number(budget.budget_delta) < 0 ? 'text-green-600' : 'text-red-600'}">
								{Number(budget.budget_delta) > 0 ? '+' : ''}{budget.budget_delta}
							</dd>
						</div>
					{/if}
					<div>
						<dt class="text-xs text-gray-500">Status</dt>
						<dd>
							{#if budget.budget_ok}
								<span class="flex items-center gap-1 text-green-600">
									<CheckCircle class="h-4 w-4" /> OK
								</span>
							{:else}
								<span class="flex items-center gap-1 text-red-600">
									<XCircle class="h-4 w-4" /> Over
								</span>
							{/if}
						</dd>
					</div>
				</dl>
			</div>
		{/if}

		{#if structure}
			<div class="border-t pt-4">
				<h4 class="mb-2 text-sm font-medium text-gray-500">Structure</h4>
				<dl class="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
					{#each Object.entries(structure) as [key, value]}
						<div>
							<dt class="text-xs text-gray-500">{key.replace(/_/g, ' ')}</dt>
							<dd class="font-mono">{value}</dd>
						</div>
					{/each}
				</dl>
			</div>
		{/if}

		{#if noCode}
			<div class="border-t pt-4">
				<h4 class="mb-2 text-sm font-medium text-gray-500">No-Code Checks</h4>
				<div class="flex flex-wrap gap-2">
					{#if noCode.has_backticks}
						<Badge variant="destructive">has backticks</Badge>
					{:else}
						<Badge variant="outline">no backticks</Badge>
					{/if}
					{#if noCode.has_code_fence}
						<Badge variant="destructive">has code fence</Badge>
					{:else}
						<Badge variant="outline">no code fence</Badge>
					{/if}
					{#if noCode.has_function_signature}
						<Badge variant="destructive">has function sig</Badge>
					{:else}
						<Badge variant="outline">no function sig</Badge>
					{/if}
				</div>
				{#if noCode.python_keywords_found && Array.isArray(noCode.python_keywords_found) && noCode.python_keywords_found.length > 0}
					<div class="mt-2">
						<span class="text-xs text-gray-500">Python keywords found:</span>
						<span class="ml-2 font-mono text-xs text-red-600">
							{noCode.python_keywords_found.join(', ')}
						</span>
					</div>
				{/if}
			</div>
		{/if}

		{#if !budget && !structure && !noCode}
			<pre class="overflow-x-auto whitespace-pre-wrap rounded-lg border bg-gray-50 p-4 text-xs">{JSON.stringify(evalData, null, 2)}</pre>
		{/if}
	</CardContent>
</Card>
