const DISALLOWED_TAGS = new Set([
	'script',
	'style',
	'iframe',
	'object',
	'embed',
	'link',
	'meta'
]);

function isDangerousUrl(value: string): boolean {
	const normalized = value.trim().toLowerCase();
	return normalized.startsWith('javascript:') || normalized.startsWith('data:text/html');
}

export function sanitizeHighlightedHtml(html: string): string {
	if (typeof document === 'undefined') {
		return '';
	}

	const template = document.createElement('template');
	template.innerHTML = html;

	for (const element of template.content.querySelectorAll('*')) {
		const tag = element.tagName.toLowerCase();
		if (DISALLOWED_TAGS.has(tag)) {
			element.remove();
			continue;
		}

		for (const attr of [...element.attributes]) {
			const name = attr.name.toLowerCase();
			const value = attr.value;
			if (name.startsWith('on')) {
				element.removeAttribute(attr.name);
				continue;
			}
			if ((name === 'href' || name === 'src') && isDangerousUrl(value)) {
				element.removeAttribute(attr.name);
			}
		}
	}

	return template.innerHTML;
}
