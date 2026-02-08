import createDOMPurify from 'dompurify';

const SHIKI_ALLOWED_TAGS = ['pre', 'code', 'span', 'br'];
const SHIKI_ALLOWED_ATTR = ['class', 'style', 'tabindex'];
const SAFE_STYLE_RE =
	/^(?:\s*(?:color|background-color|font-style|font-weight|text-decoration)\s*:\s*[^;]+;?\s*)*$/i;

const domPurify =
	typeof window === 'undefined' ? null : createDOMPurify(window);

if (domPurify) {
	domPurify.addHook(
		'uponSanitizeAttribute',
		(_node: Element, data: { attrName: string; attrValue: string; keepAttr: boolean }) => {
		if (data.attrName !== 'style') {
			return;
		}
		const style = data.attrValue.trim();
		if (!SAFE_STYLE_RE.test(style)) {
			data.keepAttr = false;
		}
		}
	);
}

export function sanitizeHighlightedHtml(html: string): string {
	if (!domPurify) {
		return '';
	}

	return domPurify.sanitize(html, {
		ALLOWED_TAGS: SHIKI_ALLOWED_TAGS,
		ALLOWED_ATTR: SHIKI_ALLOWED_ATTR,
		ALLOW_ARIA_ATTR: false,
		ALLOW_DATA_ATTR: false
	});
}
