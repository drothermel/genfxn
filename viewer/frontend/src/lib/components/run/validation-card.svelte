<script lang="ts">
	import type { ValidationResult } from '$lib/types';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { CheckCircle, XCircle, AlertCircle } from 'lucide-svelte';
	import { codeToHtml } from 'shiki';

	interface Props {
		validations: ValidationResult[];
	}

	let { validations }: Props = $props();

	let selectedIdx = $state(0);
	const selected = $derived(validations[selectedIdx]);

	let highlightedCode: string = $state('');

	$effect(() => {
		const code = selected?.extracted_code;
		if (!code) {
			highlightedCode = '';
			return;
		}
		let cancelled = false;
		codeToHtml(code, { lang: 'python', theme: 'github-light' })
			.then((html) => {
				if (!cancelled) highlightedCode = html;
			})
			.catch(() => {
				if (!cancelled) highlightedCode = '';
			});
		return () => {
			cancelled = true;
		};
	});

	function getPassRateColor(rate: number | null): string {
		if (rate === null) return 'bg-gray-100 text-gray-600';
		if (rate >= 1.0) return 'bg-green-100 text-green-700';
		if (rate >= 0.5) return 'bg-yellow-100 text-yellow-700';
		return 'bg-red-100 text-red-700';
	}
</script>

<Card>
	<CardHeader>
		<div class="flex items-center justify-between">
			<CardTitle>Validation Results</CardTitle>
			{#if validations.length > 1}
				<div class="flex gap-1">
					{#each validations as v, i}
						<button
							type="button"
							onclick={() => (selectedIdx = i)}
							class="rounded px-2 py-1 text-xs transition-colors {selectedIdx === i
								? 'bg-primary text-primary-foreground'
								: 'bg-muted hover:bg-muted/80'}"
						>
							{v.decoder_name}
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</CardHeader>
	<CardContent>
		{#if selected}
			<div class="space-y-4">
				<div class="flex flex-wrap items-center gap-3">
					<Badge variant="secondary">{selected.decoder_name}</Badge>

					{#if selected.test_pass_rate != null}
						<span
							class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-sm font-medium {getPassRateColor(
								selected.test_pass_rate
							)}"
						>
							{#if selected.test_pass_rate >= 1.0}
								<CheckCircle class="h-4 w-4" />
							{:else if selected.test_pass_rate > 0}
								<AlertCircle class="h-4 w-4" />
							{:else}
								<XCircle class="h-4 w-4" />
							{/if}
							{(selected.test_pass_rate * 100).toFixed(0)}% pass rate
						</span>
					{/if}

					{#if selected.is_valid_python === true}
						<Badge variant="outline" class="text-green-600">valid python</Badge>
					{:else if selected.is_valid_python === false}
						<Badge variant="destructive">invalid python</Badge>
					{/if}

					{#if selected.has_expected_function === true}
						<Badge variant="outline" class="text-green-600">has f()</Badge>
					{:else if selected.has_expected_function === false}
						<Badge variant="destructive">missing f()</Badge>
					{/if}
				</div>

				{#if selected.python_error}
					<div class="rounded-lg border border-red-200 bg-red-50 p-3">
						<h4 class="mb-1 text-sm font-medium text-red-700">Python Error</h4>
						<pre class="whitespace-pre-wrap text-xs text-red-600">{selected.python_error}</pre>
					</div>
				{/if}

				{#if selected.extracted_code}
					<div>
						<h4 class="mb-2 text-sm font-medium text-gray-500">Extracted Code</h4>
						{#if highlightedCode}
							<div class="overflow-x-auto rounded-lg border bg-gray-50 p-4 text-sm">
								{@html highlightedCode}
							</div>
						{:else}
							<pre class="overflow-x-auto rounded-lg border bg-gray-50 p-4 text-sm">{selected.extracted_code}</pre>
						{/if}
					</div>
				{/if}

				{#if selected.test_case_results && selected.test_case_results.length > 0}
					<div>
						<h4 class="mb-2 text-sm font-medium text-gray-500">
							Test Cases ({selected.test_case_results.filter((t) => t.passed).length}/{selected
								.test_case_results.length} passed)
						</h4>
						<div class="max-h-96 space-y-2 overflow-y-auto">
							{#each selected.test_case_results as tc, i}
								<div
									class="rounded-lg border p-3 text-xs {tc.passed
										? 'border-green-200 bg-green-50'
										: 'border-red-200 bg-red-50'}"
								>
									<div class="flex items-center gap-2">
										{#if tc.passed}
											<CheckCircle class="h-4 w-4 text-green-600" />
										{:else}
											<XCircle class="h-4 w-4 text-red-600" />
										{/if}
										<span class="font-medium">Test {i + 1}</span>
									</div>
									<div class="mt-2 grid gap-2 md:grid-cols-3">
										<div>
											<span class="text-gray-500">Input:</span>
											<pre class="mt-1 font-mono">{JSON.stringify(tc.input_value)}</pre>
										</div>
										<div>
											<span class="text-gray-500">Expected:</span>
											<pre class="mt-1 font-mono">{JSON.stringify(tc.expected_output)}</pre>
										</div>
										<div>
											<span class="text-gray-500">Actual:</span>
											<pre class="mt-1 font-mono">{JSON.stringify(tc.actual_output)}</pre>
										</div>
									</div>
									{#if tc.error}
										<div class="mt-2 text-red-600">
											<span class="text-gray-500">Error:</span> {tc.error}
										</div>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		{:else}
			<p class="text-muted-foreground">No validation results</p>
		{/if}
	</CardContent>
</Card>
