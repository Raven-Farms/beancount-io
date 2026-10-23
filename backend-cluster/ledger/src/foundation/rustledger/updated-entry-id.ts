import type { DirectiveJson } from "@rustledger/wasm";
import { buildEntryIdMap } from "./entry-hash";
import { getDirectiveSourceId } from "./plugins/provenance";
import type { EntrySourceLocation } from "./source-slice";

/** The lines a source-slice write just occupied inside one file. */
export interface ReplacedSourceRange {
  file: string;
  /** 0-based line the new content starts on (the replaced block's start). */
  startLine: number;
  /** How many lines the new content spans (`newContent.split("\n").length`). */
  lineCount: number;
}

/** The parts of a `LedgerSnapshot` this resolver reads. */
export interface EntryIdSnapshot {
  directives: readonly DirectiveJson[];
  sourceDetails?: Readonly<Record<string, EntrySourceLocation>>;
}

/**
 * Public entry ID of the directive whose source block now begins inside
 * `range`, resolved from a post-write ledger parse that carries source details
 * (`parseLedgerFiles(..., { includeSourceDetails: true })`).
 *
 * An entry's ID is content-derived (`hashEntry`, occurrence-disambiguated), so
 * editing an entry almost always changes it. Clients that keep the edited
 * entry on screen (transaction detail → edit → back) need the NEW identity,
 * which only a full, correctly booked parse of the committed content can
 * produce: the block parsed in isolation would mis-hash lot reductions and
 * lose file-level `pushtag` state.
 *
 * The source-details index is keyed by source-backed IDs (the pre-plugin
 * stream); the journal/context endpoints key on the post-plugin public IDs,
 * so the match is mapped through directive provenance. When several dated
 * blocks landed in the range (multi-entry content) the first one wins.
 * Returns `undefined` when nothing dated parsed inside the range — the caller
 * keeps the request's hash, the pre-existing behaviour.
 */
export function resolveEntryIdAtSource(
  snapshot: EntryIdSnapshot,
  range: ReplacedSourceRange,
): string | undefined {
  return resolveEntryIdsAtSources(snapshot, [range])[0];
}

/**
 * {@link resolveEntryIdAtSource} for many ranges over one parse: the ID map
 * is built once, so locating every entry a bulk write added stays linear in
 * the ledger (w23/060).
 */
export function resolveEntryIdsAtSources(
  snapshot: EntryIdSnapshot,
  ranges: readonly ReplacedSourceRange[],
): (string | undefined)[] {
  const details = snapshot.sourceDetails;
  if (details === undefined) return ranges.map(() => undefined);

  // Which ranges cover each line of each file.
  const covering = new Map<string, Map<number, number[]>>();
  ranges.forEach((range, index) => {
    let lines = covering.get(range.file);
    if (lines === undefined) {
      lines = new Map();
      covering.set(range.file, lines);
    }
    const firstLine = range.startLine + 1;
    const lastLine = range.startLine + Math.max(1, range.lineCount);
    for (let line = firstLine; line <= lastLine; line++) {
      lines.set(line, [...(lines.get(line) ?? []), index]);
    }
  });

  // The earliest source block starting inside each range.
  const found: { id?: string; line: number }[] = ranges.map(() => ({
    line: Number.POSITIVE_INFINITY,
  }));
  for (const [id, location] of Object.entries(details)) {
    const indexes = covering.get(location.filename)?.get(location.lineno);
    for (const index of indexes ?? []) {
      if (location.lineno < found[index].line) {
        found[index] = { id, line: location.lineno };
      }
    }
  }

  const wanted = new Set(found.flatMap(({ id }) => (id ? [id] : [])));
  const publicBySource = new Map<string, string>();
  if (wanted.size > 0) {
    const directives = snapshot.directives as DirectiveJson[];
    const publicIds = buildEntryIdMap(directives);
    for (const directive of directives) {
      const sourceId = getDirectiveSourceId(directive);
      if (sourceId === undefined || !wanted.has(sourceId)) continue;
      if (publicBySource.has(sourceId)) continue;
      const publicId = publicIds.get(directive);
      if (publicId !== undefined) publicBySource.set(sourceId, publicId);
    }
  }
  // No provenance (a parse that did not seed source IDs): the public stream IS
  // the source stream, so the source-backed ID is the public one.
  return found.map(({ id }) =>
    id === undefined ? undefined : (publicBySource.get(id) ?? id),
  );
}
