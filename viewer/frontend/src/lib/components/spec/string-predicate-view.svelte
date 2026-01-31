<script lang="ts">
	interface Props {
		predicate: Record<string, unknown>;
		variable?: string;
	}

	let { predicate, variable = 's' }: Props = $props();

	function renderPredicate(pred: Record<string, unknown>, v: string): string {
		const kind = pred.kind as string;
		switch (kind) {
			case 'starts_with':
				return `${v}.startswith("${pred.prefix}")`;
			case 'ends_with':
				return `${v}.endswith("${pred.suffix}")`;
			case 'contains':
				return `"${pred.substring}" in ${v}`;
			case 'is_alpha':
				return `${v}.isalpha()`;
			case 'is_digit':
				return `${v}.isdigit()`;
			case 'is_upper':
				return `${v}.isupper()`;
			case 'is_lower':
				return `${v}.islower()`;
			case 'length_cmp': {
				const opMap: Record<string, string> = {
					lt: '<',
					le: '<=',
					gt: '>',
					ge: '>=',
					eq: '=='
				};
				return `len(${v}) ${opMap[pred.op as string] ?? '=='} ${pred.value}`;
			}
			default:
				return JSON.stringify(pred);
		}
	}

	const rendered = $derived(renderPredicate(predicate, variable));
</script>

<code class="rounded bg-amber-50 px-1.5 py-0.5 text-amber-700">{rendered}</code>
