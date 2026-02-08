import { describe, expect, it } from 'vitest';

import { sanitizeHighlightedHtml } from './sanitize';

describe('sanitizeHighlightedHtml', () => {
	it('removes script payloads', () => {
		const html =
			'<pre><code><span>ok</span><script>alert(1)</script></code></pre>';
		const sanitized = sanitizeHighlightedHtml(html);

		expect(sanitized).toContain('<pre');
		expect(sanitized).not.toContain('<script');
		expect(sanitized).not.toContain('alert(1)');
	});

	it('strips event handlers and non-shiki tags', () => {
		const html =
			'<pre onclick="alert(1)"><code><span onmouseover="alert(2)">x</span></code><img src=x onerror="alert(3)"></pre>';
		const sanitized = sanitizeHighlightedHtml(html);

		expect(sanitized).toContain('<pre>');
		expect(sanitized).toContain('<span>x</span>');
		expect(sanitized).not.toContain('onmouseover');
		expect(sanitized).not.toContain('onclick');
		expect(sanitized).not.toContain('<img');
	});

	it('removes unsafe style values', () => {
		const html =
			'<pre style="color:#24292e;background-color:#fff;position:fixed"><code><span style="color:#0550ae">f</span></code></pre>';
		const sanitized = sanitizeHighlightedHtml(html);

		expect(sanitized).not.toContain('position:fixed');
		expect(sanitized).toContain('style="color:#0550ae"');
	});

	it('preserves expected shiki markup', () => {
		const html =
			'<pre class="shiki github-light" style="background-color:#fff;color:#24292e" tabindex="0"><code><span style="color:#0550ae">return</span><span> </span><span style="color:#cf222e">x</span></code></pre>';
		const sanitized = sanitizeHighlightedHtml(html);

		expect(sanitized).toContain('class="shiki github-light"');
		expect(sanitized).toContain('tabindex="0"');
		expect(sanitized).toContain('style="background-color:#fff;color:#24292e"');
		expect(sanitized).toContain('style="color:#0550ae"');
	});
});
