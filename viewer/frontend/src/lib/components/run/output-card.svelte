<script lang="ts">
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';

	interface Props {
		output: string | null;
		decoderOutputs: Record<string, string>;
	}

	let { output, decoderOutputs }: Props = $props();

	const decoderNames = $derived(Object.keys(decoderOutputs).sort());
	let selectedDecoder: string = $state('');

	$effect(() => {
		if (decoderNames.length > 0 && !selectedDecoder) {
			selectedDecoder = decoderNames[0];
		}
	});
</script>

<Card>
	<CardHeader>
		<CardTitle>Output</CardTitle>
	</CardHeader>
	<CardContent class="space-y-4">
		{#if output}
			<div>
				<h4 class="mb-2 text-sm font-medium text-gray-500">Model Output (output.txt)</h4>
				<pre class="overflow-x-auto whitespace-pre-wrap rounded-lg border bg-gray-50 p-4 text-sm">{output}</pre>
			</div>
		{/if}

		{#if decoderNames.length > 0}
			<div class="border-t pt-4">
				<div class="mb-2 flex items-center gap-2">
					<h4 class="text-sm font-medium text-gray-500">Decoder Outputs</h4>
					<div class="flex gap-1">
						{#each decoderNames as decoder}
							<button
								type="button"
								onclick={() => (selectedDecoder = decoder)}
								class="rounded px-2 py-1 text-xs transition-colors {selectedDecoder === decoder
									? 'bg-primary text-primary-foreground'
									: 'bg-muted hover:bg-muted/80'}"
							>
								{decoder}
							</button>
						{/each}
					</div>
				</div>
				{#if selectedDecoder && decoderOutputs[selectedDecoder]}
					<pre class="overflow-x-auto whitespace-pre-wrap rounded-lg border bg-gray-50 p-4 text-sm">{decoderOutputs[selectedDecoder]}</pre>
				{/if}
			</div>
		{/if}

		{#if !output && decoderNames.length === 0}
			<p class="text-muted-foreground">No output available</p>
		{/if}
	</CardContent>
</Card>
