<script lang="ts">
	import { page } from '$app/state';
	import { fetchRun } from '$lib/api';
	import type { RunData } from '$lib/types';
	import { Card, CardContent } from '$lib/components/ui/card';
	import RunMetadataCard from '$lib/components/run/run-metadata-card.svelte';
	import PromptCard from '$lib/components/run/prompt-card.svelte';
	import OutputCard from '$lib/components/run/output-card.svelte';
	import EvalCard from '$lib/components/run/eval-card.svelte';
	import ValidationCard from '$lib/components/run/validation-card.svelte';
	import { ArrowLeft } from 'lucide-svelte';

	let run: RunData | null = $state(null);
	let loading = $state(true);
	let error: string | null = $state(null);

	const tag = $derived(decodeURIComponent(page.params.tag));
	const model = $derived(decodeURIComponent(page.params.model));
	const runId = $derived(page.params.run_id);

	$effect(() => {
		const t = tag;
		const m = model;
		const r = runId;
		if (!t || !m || !r) {
			loading = false;
			return;
		}
		loading = true;
		error = null;
		run = null;
		fetchRun(t, m, r)
			.then((data) => {
				if (page.params.run_id === r) run = data;
			})
			.catch((e) => {
				if (page.params.run_id === r) {
					error = e instanceof Error ? e.message : 'Unknown error';
				}
			})
			.finally(() => {
				if (page.params.run_id === r) loading = false;
			});
	});
</script>

<div class="container mx-auto max-w-5xl px-4 py-8">
	<div class="mb-6">
		<a
			href="/runs"
			class="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
		>
			<ArrowLeft class="h-4 w-4" />
			Back to runs
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
	{:else if run}
		<header class="mb-8">
			<h1 class="font-mono text-2xl font-bold">{run.meta.run_id}</h1>
			<p class="mt-1 text-sm text-muted-foreground">
				{run.meta.tag} / {run.meta.model}
			</p>
		</header>

		<div class="space-y-6">
			<RunMetadataCard meta={run.meta} />

			<PromptCard taskPrompt={run.task_prompt} systemPrompt={run.system_prompt} />

			<OutputCard output={run.output} decoderOutputs={run.decoder_outputs} />

			{#if run.eval}
				<EvalCard evalData={run.eval} />
			{/if}

			{#if run.validations.length > 0}
				<ValidationCard validations={run.validations} />
			{/if}
		</div>
	{/if}
</div>
