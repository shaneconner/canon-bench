/* Freeze the known-item retrieval harness into one immutable artifact.

   The problem this solves. r1_decompose.mjs and r1_embed.mjs both read two live
   project stores at their paths and derive the eligible query set at execution
   time, so the corpus and the query population move as the projects are used.
   They did move between the two runs, which is why six of the eight BM25 cells
   disagree between them, and both stores have grown again since. Neither run
   reproduces.

   What this writes. One JSON file carrying everything a scorer needs and nothing
   it has to go and find: every article and journal document with the exact text
   that gets indexed, the derived eligible query set with its resolved targets,
   the deterministic sample, both query variants per sampled entry, and the
   self-entry that each query excludes. r1_frozen_score.mjs reads this file and
   opens nothing else, so its numbers are reproducible from the artifact alone.

   The sampling rule is copied from r1_embed.mjs unchanged, so a frozen run is
   comparable to the live runs rather than a different experiment: step is
   floor(eligible / maxQueries), take every step-th, then cap at maxQueries.

   Usage: node lab/ranking/r1_freeze.mjs [maxQueriesPerStore] [outPath] */

import { createHash } from "node:crypto";
import { existsSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { CanonStore } from "../../extensions/lib/store.ts";

const MAX_QUERIES = Number(process.argv[2] ?? 400);
const OUT = process.argv[3] ?? join(import.meta.dirname, "frozen-corpus.json");
const HOME = "/home/shane";
const PROJECTS = ["quorum", "pi-fold"];
const MAX_CHARS = 3500;

/* Both copied verbatim from r1_embed.mjs. If either changes there, the frozen
   artifact stops describing the same harness and this file has to change too.

   THE TWO RANKERS DO NOT SEE THE SAME STRING, and an earlier version of this
   exporter missed that. The live harness indexes the lexical retriever on the
   full document and truncates only the text it sends to the embedder, because
   the embedding model has a short context. Exporting one truncated string for
   both silently changed the lexical arm: 46 percent of quorum's documents and 38
   percent of pi-fold's reach the cap, so BM25 would have been scored over
   roughly half a corpus it normally sees whole. Both strings are exported. */
function variants(body) {
  const flat = body.replace(/\s+/g, " ").trim();
  const words = [];
  const seen = new Set();
  for (const raw of flat.toLowerCase().split(/[^a-z0-9_]+/)) {
    if (raw.length < 4 || seen.has(raw)) continue;
    seen.add(raw); words.push(raw);
    if (words.length >= 6) break;
  }
  return { full: flat.slice(0, MAX_CHARS), terse: words.join(" ") };
}
const docFull = (c) => `${c.path} ${c.capsule} ${c.body}`;
const docEmbed = (c) => docFull(c).slice(0, MAX_CHARS);

const frozen = { max_queries: MAX_QUERIES, max_chars: MAX_CHARS, projects: {} };

for (const project of PROJECTS) {
  const root = join(HOME, project, ".canon");
  if (!existsSync(root)) {
    process.stderr.write(`no store at ${root}; skipped\n`);
    continue;
  }
  const store = new CanonStore(root);

  const articles = [];
  for (const path of store.list()) {
    const a = store.read(path);
    if (a) articles.push({ path, capsule: a.capsule, body: a.body });
  }
  const articleSet = new Set(articles.map((a) => a.path));

  const entries = store.journalEntries();
  const journalDocs = entries.map((e) => ({
    path: `journal/${e.name.replace(/\.md$/, "")}`,
    capsule: e.subjects.join(", "),
    body: e.body,
  }));

  const resolveSubject = (s) => {
    if (articleSet.has(s)) return s;
    const cut = s.indexOf(":");
    if (cut !== -1 && articleSet.has(s.slice(cut + 1))) return s.slice(cut + 1);
    return undefined;
  };
  const eligible = entries
    .map((e) => ({ e, targets: [...new Set(e.subjects.map(resolveSubject).filter(Boolean))] }))
    .filter((q) => q.targets.length && q.e.body.trim().length > 40);
  const step = Math.max(1, Math.floor(eligible.length / MAX_QUERIES));
  const sample = eligible.filter((_, i) => i % step === 0).slice(0, MAX_QUERIES);

  frozen.projects[project] = {
    articles: articles.map((a) => ({ path: a.path, text: docFull(a), embed_text: docEmbed(a) })),
    journal: journalDocs.map((d) => ({ path: d.path, text: docFull(d), embed_text: docEmbed(d) })),
    eligible_count: eligible.length,
    step,
    queries: sample.map((q) => {
      const v = variants(q.e.body);
      return {
        self: `journal/${q.e.name.replace(/\.md$/, "")}`,
        targets: q.targets,
        full: v.full,
        terse: v.terse,
      };
    }),
  };

  process.stderr.write(
    `${project}: ${articles.length} articles, ${journalDocs.length} journal, ` +
    `${eligible.length} eligible, step ${step}, ${sample.length} sampled\n`);
}

const text = JSON.stringify(frozen, null, 1);
writeFileSync(OUT, text);
const digest = createHash("sha256").update(text).digest("hex");
process.stderr.write(`\nwrote ${OUT}\nsha256 ${digest}\n`);
