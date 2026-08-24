import type { SourceInfo } from "../types/events";

// Webpage sources link out (real URL); PDF sources have no public URL to
// link to, so they render as a plain, non-clickable label instead of a dead
// or misleading link.
export function SourceChips({ sources }: { sources: SourceInfo[] }) {
  if (sources.length === 0) return null;

  // De-duplicate by url_or_filename - the same page can legitimately back
  // multiple cited claims in one answer.
  const seen = new Set<string>();
  const unique = sources.filter((s) => {
    if (seen.has(s.url_or_filename)) return false;
    seen.add(s.url_or_filename);
    return true;
  });

  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {unique.map((source) =>
        source.doc_type === "webpage" ? (
          <a
            key={source.url_or_filename}
            href={source.url_or_filename}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 text-xs text-[var(--brand-green-dark)] hover:bg-[var(--brand-green-light)]"
            title={source.url_or_filename}
          >
            {source.title || source.url_or_filename}
          </a>
        ) : (
          <span
            key={source.url_or_filename}
            className="rounded-full border border-[var(--border)] bg-[var(--surface-muted)] px-2.5 py-1 text-xs text-[var(--text-muted)]"
            title={source.url_or_filename}
          >
            {source.title || source.url_or_filename}
          </span>
        ),
      )}
    </div>
  );
}
