<script lang="ts">
	interface Props {
		predicate: Record<string, unknown>;
		variable?: string;
	}

	let { predicate, variable = 'x' }: Props = $props();

	function renderPredicate(pred: Record<string, unknown>, v: string): string {
		const safeV = typeof v === 'string' ? v : 'x';
		const kind = typeof pred.kind === 'string' ? pred.kind : '';
		switch (kind) {
			case 'even':
				return `${safeV} % 2 == 0`;
			case 'odd':
				return `${safeV} % 2 == 1`;
			case 'lt':
			case 'le':
			case 'gt':
			case 'ge': {
				const value = pred.value;
				if (value === undefined || value === null) {
					return `[${kind}: missing value] ${JSON.stringify(pred)}`;
				}
				return kind === 'lt'
					? `${safeV} < ${value}`
					: kind === 'le'
						? `${safeV} <= ${value}`
						: kind === 'gt'
							? `${safeV} > ${value}`
							: `${safeV} >= ${value}`;
			}
			case 'mod_eq': {
				const divisor = pred.divisor;
				const remainder = pred.remainder;
				if (divisor === undefined || divisor === null || remainder === undefined || remainder === null) {
					return `[mod_eq: missing divisor/remainder] ${JSON.stringify(pred)}`;
				}
				return `${safeV} % ${divisor} == ${remainder}`;
			}
			case 'in_set': {
				const values = pred.values;
				if (!Array.isArray(values) || values.length === 0) {
					return `[in_set: values must be non-empty array] ${JSON.stringify(pred)}`;
				}
				return `${safeV} in {${values.join(', ')}}`;
			}
			default:
				return kind ? `[unknown kind: ${kind}] ${JSON.stringify(pred)}` : JSON.stringify(pred);
		}
	}

	const rendered = $derived(renderPredicate(predicate, variable));
</script>

<code class="rounded bg-blue-50 px-1.5 py-0.5 text-blue-700">{rendered}</code>
