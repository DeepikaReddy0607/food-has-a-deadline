import React from 'react';

interface FormattedMarkdownProps {
  content: string;
  className?: string;
}

/**
 * Lightweight, zero-dependency Markdown renderer for AI assistant messages.
 * Formats headings, tables, bullet/numbered lists, bold/italic text, and inline code.
 */
export const FormattedMarkdown: React.FC<FormattedMarkdownProps> = ({ content, className = '' }) => {
  if (!content) return null;

  // Helper to parse inline styles: bold, italic, code
  const renderInline = (text: string): React.ReactNode => {
    // Split by inline code, bold, italic
    const parts: React.ReactNode[] = [];
    let remaining = text;
    let key = 0;

    // Regex for inline code: `code`
    // bold: **text**
    // italic: *text*
    const tokenRegex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
    let match: RegExpExecArray | null;
    let lastIndex = 0;

    while ((match = tokenRegex.exec(remaining)) !== null) {
      if (match.index > lastIndex) {
        parts.push(remaining.slice(lastIndex, match.index));
      }

      const token = match[0];
      if (token.startsWith('`') && token.endsWith('`')) {
        parts.push(
          <code key={key++} className="px-1 py-0.5 bg-muted/60 text-primary font-mono text-[11px] rounded border border-border/50">
            {token.slice(1, -1)}
          </code>
        );
      } else if (token.startsWith('**') && token.endsWith('**')) {
        parts.push(
          <strong key={key++} className="font-semibold text-foreground">
            {token.slice(2, -2)}
          </strong>
        );
      } else if (token.startsWith('*') && token.endsWith('*')) {
        parts.push(
          <em key={key++} className="italic">
            {token.slice(1, -1)}
          </em>
        );
      }

      lastIndex = tokenRegex.lastIndex;
    }

    if (lastIndex < remaining.length) {
      parts.push(remaining.slice(lastIndex));
    }

    return parts.length > 0 ? parts : text;
  };

  // Split lines and parse blocks
  const lines = content.split('\n');
  const blocks: React.ReactNode[] = [];
  let i = 0;
  let blockKey = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // 1. Headings
    if (trimmed.startsWith('#### ')) {
      blocks.push(
        <h4 key={blockKey++} className="text-xs font-bold text-foreground mt-2 mb-1">
          {renderInline(trimmed.slice(5))}
        </h4>
      );
      i++;
      continue;
    }
    if (trimmed.startsWith('### ')) {
      blocks.push(
        <h3 key={blockKey++} className="text-sm font-bold text-foreground mt-2.5 mb-1 text-primary">
          {renderInline(trimmed.slice(4))}
        </h3>
      );
      i++;
      continue;
    }
    if (trimmed.startsWith('## ')) {
      blocks.push(
        <h2 key={blockKey++} className="text-base font-bold text-foreground mt-3 mb-1.5 pb-1 border-b border-border/50">
          {renderInline(trimmed.slice(3))}
        </h2>
      );
      i++;
      continue;
    }
    if (trimmed.startsWith('# ')) {
      blocks.push(
        <h1 key={blockKey++} className="text-lg font-bold text-foreground mt-3 mb-2 pb-1 border-b border-border/60">
          {renderInline(trimmed.slice(2))}
        </h1>
      );
      i++;
      continue;
    }

    // 2. Tables: Check for GFM table header (| col | col |) followed by (|---|---|)
    if (trimmed.startsWith('|') && trimmed.endsWith('|') && i + 1 < lines.length && lines[i + 1].trim().startsWith('|') && lines[i + 1].includes('---')) {
      const headerLine = trimmed;
      const headers = headerLine
        .split('|')
        .slice(1, -1)
        .map((h) => h.trim());

      i += 2; // skip header and separator lines
      const rows: string[][] = [];

      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        const rowCells = lines[i]
          .trim()
          .split('|')
          .slice(1, -1)
          .map((c) => c.trim());
        rows.push(rowCells);
        i++;
      }

      blocks.push(
        <div key={blockKey++} className="my-2.5 overflow-x-auto rounded-lg border border-border/60 shadow-xs">
          <table className="w-full border-collapse text-left text-xs">
            <thead className="bg-muted/50 border-b border-border/60">
              <tr>
                {headers.map((h, hIdx) => (
                  <th key={hIdx} className="px-3 py-2 font-semibold text-foreground text-[11px] uppercase tracking-wider">
                    {renderInline(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40 bg-card">
              {rows.map((row, rIdx) => (
                <tr key={rIdx} className="hover:bg-muted/20 transition-colors">
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="px-3 py-2 text-foreground/90 whitespace-nowrap">
                      {renderInline(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // 3. Unordered Lists (* or -)
    if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
      const items: string[] = [];
      while (i < lines.length && (lines[i].trim().startsWith('* ') || lines[i].trim().startsWith('- '))) {
        items.push(lines[i].trim().slice(2));
        i++;
      }
      blocks.push(
        <ul key={blockKey++} className="my-1.5 ml-4 list-disc space-y-1 text-xs">
          {items.map((item, itIdx) => (
            <li key={itIdx} className="leading-relaxed">
              {renderInline(item)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // 4. Ordered Lists (1. 2. etc.)
    if (/^\d+\.\s/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s/, ''));
        i++;
      }
      blocks.push(
        <ol key={blockKey++} className="my-1.5 ml-4 list-decimal space-y-1 text-xs">
          {items.map((item, itIdx) => (
            <li key={itIdx} className="leading-relaxed">
              {renderInline(item)}
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // 5. Blank line
    if (trimmed === '') {
      i++;
      continue;
    }

    // 6. Regular paragraph
    blocks.push(
      <p key={blockKey++} className="my-1 leading-relaxed">
        {renderInline(line)}
      </p>
    );
    i++;
  }

  return <div className={`space-y-1 ${className}`}>{blocks}</div>;
};
