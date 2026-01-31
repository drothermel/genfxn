<script lang="ts">
	import type { Query, QueryTag } from '$lib/types';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';

	interface Props {
		queries: Query[];
	}

	let { queries }: Props = $props();

	const tagVariants: Record<QueryTag, 'default' | 'secondary' | 'outline' | 'destructive'> = {
		typical: 'secondary',
		boundary: 'outline',
		coverage: 'default',
		adversarial: 'destructive'
	};

	function formatValue(value: unknown): string {
		if (Array.isArray(value)) {
			return `[${value.join(', ')}]`;
		}
		return String(value);
	}
</script>

<Card>
	<CardHeader>
		<CardTitle>Test Queries</CardTitle>
		<p class="text-sm text-gray-500">{queries.length} queries</p>
	</CardHeader>
	<CardContent>
		<div class="overflow-x-auto">
			<table class="w-full text-sm">
				<thead>
					<tr class="border-b text-left">
						<th class="pb-2 pr-4 font-medium text-gray-500">Input</th>
						<th class="pb-2 pr-4 font-medium text-gray-500">Output</th>
						<th class="pb-2 font-medium text-gray-500">Tag</th>
					</tr>
				</thead>
				<tbody>
					{#each queries as query}
						<tr class="border-b last:border-0">
							<td class="py-2 pr-4 font-mono">{formatValue(query.input)}</td>
							<td class="py-2 pr-4 font-mono">{formatValue(query.output)}</td>
							<td class="py-2">
								<Badge variant={tagVariants[query.tag]}>{query.tag}</Badge>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</CardContent>
</Card>
