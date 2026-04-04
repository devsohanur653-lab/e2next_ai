/**
 * Lightweight markdown-to-HTML converter.
 * Handles: bold, italic, code blocks, inline code, lists, line breaks, links.
 */
export function renderMarkdown(text) {
  if (!text) return ''

  let html = text
    // Escape HTML entities
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Code blocks (```...```)
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre class="e2-code-block"><code>${code.trim()}</code></pre>`
  })

  // Inline code (`...`)
  html = html.replace(/`([^`]+)`/g, '<code class="e2-inline-code">$1</code>')

  // Bold (**...**)
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')

  // Italic (*...*)
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')

  // Links [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" class="e2-link">$1</a>')

  // Unordered lists (- item or * item)
  html = html.replace(/^[\s]*[-*]\s+(.+)$/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul class="e2-list">$&</ul>')

  // Numbered lists (1. item)
  html = html.replace(/^[\s]*\d+\.\s+(.+)$/gm, '<li>$1</li>')

  // Headers
  html = html.replace(/^### (.+)$/gm, '<h4 class="e2-h4">$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3 class="e2-h3">$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2 class="e2-h2">$1</h2>')

  // Line breaks
  html = html.replace(/\n/g, '<br/>')

  return html
}
