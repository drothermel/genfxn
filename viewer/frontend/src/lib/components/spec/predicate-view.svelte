<script lang="ts">
	interface Props {
		predicate: Record<string, unknown>;
		variable?: string;
	}

	let { predicate, variable = 'x' }: Props = $props();

	function renderPredicate(pred: Record<string, unknown>, v: string): string {
		const kind = pred.kind as string;
		switch (kind) {
			case 'even':
				return `${v} % 2 == 0`;
			case 'odd':
				return `${v} % 2 == 1`;
			case 'lt':
				return `${v} < ${pred.value}`;
			case 'le':
				return `${v} <= ${pred.value}`;
			case 'gt':
				return `${v} > ${pred.value}`;
			case 'ge':
				return `${v} >= ${pred.value}`;
			case 'mod_eq':
				return `${v} % ${pred.divisor} == ${pred.remainder}`;
			case 'in_set':
				return `${v} in {${(pred.values as number[]).join(', ')}}`;
			default:
				return JSON.stringify(pred);
		}
	}

	const rendered = $derived(renderPredicate(predicate, variable));
</script>

<code class="rounded bg-blue-50 px-1.5 py-0.5 text-blue-700">{rendered}</code>
