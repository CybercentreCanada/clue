import { render, screen } from '@testing-library/react';
import MarkdownPlugin from 'lib/plugins/markdown';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import Markdown from './index';

const renderMarkdown = (md: string) =>
  render(
    <MemoryRouter>
      <Markdown md={md} />
    </MemoryRouter>
  ).container;

// Regression checks for untrusted action/fetcher Markdown. JSDOM inspects the
// resulting DOM; it does not establish whether injected JavaScript executes in a browser.
describe('Markdown from external results', () => {
  // These elements can host scripts, navigate, submit data, or alter the page.
  // A sanitized renderer must remove them, not merely rewrite their URLs.
  it.each([
    ['iframe srcdoc script', '<iframe srcdoc="<script>window.xss = true</script>"></iframe>', 'iframe'],
    ['iframe external page', '<iframe src="https://example.invalid/collect"></iframe>', 'iframe'],
    ['inline script', '<script>window.xss = true</script>', 'script'],
    ['SVG event handler', '<svg onload="window.xss = true"><circle r="10" /></svg>', 'svg'],
    [
      'SVG foreignObject',
      '<svg><foreignObject><iframe srcdoc="<script>window.xss=true</script>"></iframe></foreignObject></svg>',
      'svg'
    ],
    ['object data URL', '<object data="data:text/html,<script>window.xss = true</script>"></object>', 'object'],
    ['embed data URL', '<embed src="data:text/html,<script>window.xss = true</script>">', 'embed'],
    ['form submission', '<form action="https://example.invalid/collect"><input name="token"></form>', 'form'],
    ['style injection', '<style>body { display: none }</style>', 'style'],
    ['meta refresh', '<meta http-equiv="refresh" content="0;url=https://example.invalid/collect">', 'meta']
  ])('does not render %s from raw HTML', (_name, md, tag) => {
    const container = renderMarkdown(md);

    expect(container.querySelector(tag)).not.toBeInTheDocument();
  });

  // Safe elements may remain, but executable event attributes and URLs must not.
  it.each([
    ['image error handler', '<img src="bad.png" onerror="window.xss = true">', 'img', 'onerror'],
    ['link with javascript URL', '[open](javascript:window.xss=true)', 'a', 'href'],
    ['raw link with javascript URL', '<a href="javascript:window.xss=true">open</a>', 'a', 'href']
  ])('does not expose %s', (_name, md, tag, attribute) => {
    const container = renderMarkdown(md);

    expect(container.querySelector(tag)?.getAttribute(attribute) ?? '').not.toMatch(/(?:javascript:|window\.xss)/i);
  });

  // Sanitizing attacker input should not break ordinary Markdown content.
  it('preserves ordinary Markdown and safe links', () => {
    renderMarkdown('**Analyst note** [details](https://example.invalid/report)');

    expect(screen.getByText('Analyst note').tagName).toBe('STRONG');
    expect(screen.getByRole('link', { name: 'details' })).toHaveAttribute('href', 'https://example.invalid/report');
  });

  it('preserves bullet lists and safe HTTP links', () => {
    renderMarkdown('- First item\n- [Report](http://example.invalid/report)');

    expect(screen.getByRole('list').tagName).toBe('UL');
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getByRole('link', { name: 'Report' })).toHaveAttribute('href', 'http://example.invalid/report');
  });

  it('preserves GFM tables through the custom table components', () => {
    renderMarkdown('| Indicator | Verdict |\n| --- | --- |\n| 127.0.0.1 | Unknown |');

    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Indicator' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: '127.0.0.1' })).toBeInTheDocument();
  });

  it('preserves inline code and custom alert code blocks', () => {
    renderMarkdown('`sample`\n\n```alert\nAnalyst note\n```');

    expect(screen.getByText('sample').tagName).toBe('CODE');
    expect(screen.getByRole('alert')).toHaveTextContent('Analyst note');
  });

  // Both plugin entry points supply untrusted text to the same Markdown renderer.
  it.each([
    [
      'action output',
      (plugin: MarkdownPlugin, payload: string) =>
        plugin.actionResult({ result: { outcome: 'success', format: 'markdown', output: payload } })
    ],
    [
      'fetcher data',
      (plugin: MarkdownPlugin, payload: string) =>
        plugin.fetcherResult({ result: { outcome: 'success', format: 'markdown', data: payload } })
    ]
  ])('sanitizes %s passed through the Markdown plugin', (_name, renderResult) => {
    const payload = '<iframe srcdoc="<script>window.xss = true</script>"></iframe>';
    const plugin = new MarkdownPlugin();
    const { container } = render(<MemoryRouter>{renderResult(plugin, payload)}</MemoryRouter>);

    expect(container.querySelector('iframe')).not.toBeInTheDocument();
  });
});
