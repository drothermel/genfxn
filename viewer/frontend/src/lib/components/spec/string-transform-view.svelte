<script lang="ts">
	interface Props {
		transform: Record<string, unknown>;
		variable?: string;
	}

	let { transform, variable = 's' }: Props = $props();

	/** Escape a JS string for use inside a Python double-quoted string literal. */
	function escapePythonString(s: string): string {
		let out = '';
		for (let i = 0; i < s.length; i++) {
			const c = s[i];
			const code = c.charCodeAt(0);
			switch (c) {
				case '\\':
					out += '\\\\';
					break;
				case '"':
					out += '\\"';
					break;
				case '\n':
					out += '\\n';
					break;
				case '\r':
					out += '\\r';
					break;
				case '\t':
					out += '\\t';
					break;
				default:
					if (code < 32 || code === 127) {
						out += '\\x' + code.toString(16).padStart(2, '0');
					} else {
						out += c;
					}
			}
		}
		return out;
	}

	function renderTransform(t: Record<string, unknown>, v: string): string {
		const kind = t.kind as string;
		switch (kind) {
			case 'identity':
				return v;
			case 'lowercase':
				return `${v}.lower()`;
			case 'uppercase':
				return `${v}.upper()`;
			case 'capitalize':
				return `${v}.capitalize()`;
			case 'swapcase':
				return `${v}.swapcase()`;
			case 'reverse':
				return `${v}[::-1]`;
			case 'replace':
				return `${v}.replace("${escapePythonString(String(t.old ?? ''))}", "${escapePythonString(String(t.new ?? ''))}")`;
			case 'strip': {
				const chars = t.chars as string | null;
				if (chars) {
					return `${v}.strip("${escapePythonString(chars)}")`;
				}
				return `${v}.strip()`;
			}
			case 'prepend':
				return `"${escapePythonString(String(t.prefix ?? ''))}" + ${v}`;
			case 'append':
				return `${v} + "${escapePythonString(String(t.suffix ?? ''))}"`;
			default:
				return JSON.stringify(t);
		}
	}

	const rendered = $derived(renderTransform(transform, variable));
</script>

<code class="rounded bg-teal-50 px-1.5 py-0.5 text-teal-700">{rendered}</code>
