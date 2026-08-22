/* Score the frozen known-item harness. Reads frozen-corpus.json and nothing else.

   Every number this prints is reproducible from that one file plus the shipped
   LexicalRetriever and a local embedding model. It opens no project store, so it
   cannot drift the way r1_decompose.mjs and r1_embed.mjs did between their two
   runs.

   Reports the same eight cells as the live embedding rerun, per store and query
   variant, embedding against shipped BM25:
     art_only@10  - the DEFAULT search surface since journal became opt-in
     mixed@10     - the journal:true combined ranking

   Positive control. A ranker bug that returned nothing would print zeroes, and
   zeroes would read as a finding. So the script also scores an oracle ranker that
   puts each query's own targets first, and refuses to report unless the oracle
   scores 1.0 in every cell. If the oracle cannot find the targets, the harness is
   broken rather than the rankers.

   Usage: node lab/ranking/r1_frozen_score.mjs [frozen-corpus.json] */

import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { LexicalRetriever } from "../../extensions/lib/retrieval.ts";

const IN = process.argv[2] ?? join(import.meta.dirname, "frozen-corpus.json");
const MODEL = "nomic-embed-text";
const OLLAMA = process.env.OLLAMA_HOST || "http://127.0.0.1:11434";
const BATCH = 8;
const CACHE = join(import.meta.dirname, "embed-cache.json");

const sha = (text) => createHash("sha256").update(text).digest("hex");
const cache = existsSync(CACHE) ? JSON.parse(readFileSync(CACHE, "utf8")) : {};
let cacheDirty = 0;

async function embedAll(texts) {
  const out = new Array(texts.length);
  const missing = [];
  texts.forEach((text, i) => {
    const key = sha(MODEL + "\0" + text);
    if (cache[key]) out[i] = cache[key];
    else missing.push([i, key, text]);
  });
  for (let at = 0; at < missing.length; at += BATCH) {
    const slice = missing.slice(at, at + BATCH);
    let response;
    for (let attempt = 0; ; attempt += 1) {
      try {
        response = await fetch(`${OLLAMA}/api/embed`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model: MODEL, input: slice.map(([, , t]) => t) }),
        });
        break;
      } catch (error) {
        if (attempt >= 1) throw error;
        process.stderr.write(`\nbatch fetch failed (${error?.cause?.code ?? error}); retrying once\n`);
      }
    }
    if (!response.ok) throw new Error(`ollama ${response.status}: ${await response.text()}`);
    const json = await response.json();
    json.embeddings.forEach((vector, j) => {
      const [i, key] = slice[j];
      out[i] = vector; cache[key] = vector; cacheDirty += 1;
    });
    if (cacheDirty >= 200) { writeFileSync(CACHE, JSON.stringify(cache)); cacheDirty = 0; }
    process.stderr.write(`embedded ${Math.min(at + BATCH, missing.length)}/${missing.length}\r`);
  }
  if (cacheDirty) writeFileSync(CACHE, JSON.stringify(cache));
  return out;
}

function cosine(a, b) {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i += 1) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
  return dot / (Math.sqrt(na) * Math.sqrt(nb) || 1);
}

const raw = readFileSync(IN, "utf8");
process.stderr.write(`${IN}\nsha256 ${sha(raw)}\n\n`);
const frozen = JSON.parse(raw);

const results = {};
for (const [project, data] of Object.entries(frozen.projects)) {
  // The retriever indexes {path, capsule, body}; the frozen text is already the
  // exact concatenation the live harness indexed, so it goes in as the body with
  // the other fields empty rather than being rebuilt and risking a different string.
  const asDocs = (rows) => rows.map((r) => ({ path: r.path, capsule: "", body: r.text }));
  const articles = asDocs(data.articles);
  const mixed = asDocs([...data.articles, ...data.journal]);

  const texts = [...data.articles, ...data.journal].map((r) => r.text);
  const vectors = await embedAll(texts);
  const vecByPath = new Map(mixed.map((d, i) => [d.path, vectors[i]]));

  const lexArt = new LexicalRetriever(); lexArt.index(articles);
  const lexMixed = new LexicalRetriever(); lexMixed.index(mixed);

  const out = {};
  for (const variant of ["full", "terse"]) {
    const queryTexts = data.queries.map((q) => q[variant]);
    const queryVectors = await embedAll(queryTexts);
    let n = 0;
    const hits = { emb_art: 0, emb_mixed: 0, lex_art: 0, lex_mixed: 0, oracle_art: 0, oracle_mixed: 0 };

    for (let qi = 0; qi < data.queries.length; qi += 1) {
      const q = data.queries[qi];
      const self = q.self;
      const targets = new Set(q.targets);
      const qv = queryVectors[qi];
      if (!qv || !queryTexts[qi]) continue;
      n += 1;

      const embRank = (docs) => docs
        .filter((d) => d.path !== self)
        .map((d) => [d.path, cosine(qv, vecByPath.get(d.path))])
        .sort((a, b) => b[1] - a[1]).slice(0, 10).map(([p]) => p);
      const lexRank = (retriever, docs) => [...retriever.score(queryTexts[qi], docs).entries()]
        .filter(([p]) => p !== self)
        .sort((a, b) => b[1] - a[1]).slice(0, 10).map(([p]) => p);
      // Positive control: rank the known targets first. Anything below 1.0 means
      // a target is absent from the corpus or excluded by the self filter.
      const oracleRank = (docs) => docs
        .filter((d) => d.path !== self)
        .map((d) => [d.path, targets.has(d.path) ? 1 : 0])
        .sort((a, b) => b[1] - a[1]).slice(0, 10).map(([p]) => p);

      if (embRank(articles).some((p) => targets.has(p))) hits.emb_art += 1;
      if (embRank(mixed).some((p) => targets.has(p))) hits.emb_mixed += 1;
      if (lexRank(lexArt, articles).some((p) => targets.has(p))) hits.lex_art += 1;
      if (lexRank(lexMixed, mixed).some((p) => targets.has(p))) hits.lex_mixed += 1;
      if (oracleRank(articles).some((p) => targets.has(p))) hits.oracle_art += 1;
      if (oracleRank(mixed).some((p) => targets.has(p))) hits.oracle_mixed += 1;
    }

    out[variant] = { n };
    for (const [k, v] of Object.entries(hits)) {
      out[variant][`${k}_recall_at_10`] = Math.round((v / n) * 1000) / 1000;
    }
  }
  results[project] = out;
}

let broken = 0;
for (const [project, out] of Object.entries(results)) {
  for (const [variant, cells] of Object.entries(out)) {
    for (const surface of ["art", "mixed"]) {
      if (cells[`oracle_${surface}_recall_at_10`] !== 1) {
        process.stderr.write(
          `CONTROL FAILED ${project}/${variant}/${surface}: oracle at ` +
          `${cells[`oracle_${surface}_recall_at_10`]}, not 1.0\n`);
        broken += 1;
      }
    }
  }
}
if (broken) {
  process.stderr.write("\nthe harness cannot find its own targets; no result is reported.\n");
  process.exit(1);
}

console.log(JSON.stringify(results, null, 2));
process.stderr.write("\npositive control: oracle at 1.0 in every cell\n");
