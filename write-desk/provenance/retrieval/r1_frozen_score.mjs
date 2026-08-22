/* Score the frozen known-item harness against one immutable corpus export.

   What is frozen and what is not. The corpus and the query set are frozen: this
   script opens no project store, so it cannot drift the way r1_decompose.mjs and
   r1_embed.mjs did between their two runs, and that was the defect it exists to
   remove. The execution around it is NOT hermetic, and saying so is the point of
   this paragraph. It imports the retriever from the working tree, it reads and
   writes an embedding cache keyed by model NAME and text rather than by model
   digest, and it calls whichever local Ollama artifact currently answers to
   nomic-embed-text. A model republished under the same tag would be picked up
   silently, and cached vectors from two versions could coexist. Pinning the
   retriever commit and the model digest, and keying the cache by digest, is the
   remaining work.

   What each ranker is given. The live harness does not show the two rankers the
   same text: it indexes the lexical retriever on whole documents and truncates
   only the strings it sends to the embedding model, which has a short context.
   The export therefore carries both, and this scorer keeps them apart. An earlier
   export carried one truncated string and fed it to both, which silently scored
   BM25 over about half the corpus; the script now refuses such an export.

   Three arms, not two, so the truncation defect can be priced on ONE corpus:
   embeddings over the truncated text, BM25 over the full documents (shipped
   behaviour), and BM25 over the truncated text (the defect). Comparing the first
   frozen run against this one would confound the truncation with the two
   documents the corpus gained between the exports; the lextrunc arm removes that.

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
  //
  // The two rankers get DIFFERENT strings, and that is the live harness's shape,
  // not a convenience here. r1_embed.mjs indexes the lexical retriever on whole
  // documents and truncates only what it sends to the embedder. Nearly half the
  // corpus is longer than the cap, so feeding one truncated string to both would
  // quietly replace the shipped lexical ranker with a different one.
  const asDocs = (rows) => rows.map((r) => ({ path: r.path, capsule: "", body: r.text }));
  const articles = asDocs(data.articles);
  const mixed = asDocs([...data.articles, ...data.journal]);

  const rows = [...data.articles, ...data.journal];
  if (rows.some((r) => typeof r.embed_text !== "string")) {
    process.stderr.write(
      `${project}: the export carries no embed_text. It predates the truncation fix ` +
      `and its lexical arm was scored over truncated documents; re-freeze it.\n`);
    process.exit(1);
  }
  const texts = rows.map((r) => r.embed_text);
  const vectors = await embedAll(texts);
  const vecByPath = new Map(mixed.map((d, i) => [d.path, vectors[i]]));

  const lexArt = new LexicalRetriever(); lexArt.index(articles);
  const lexMixed = new LexicalRetriever(); lexMixed.index(mixed);

  // The LEGACY lexical arm: BM25 over the truncated strings, which is what the
  // first frozen export gave it by mistake. It is scored here, on this same
  // corpus, so the cost of that defect is one controlled difference rather than
  // a comparison across two exports that also differ by two documents. Without
  // it the reported cost mixes the truncation with the corpus change.
  const asTrunc = (rows_) => rows_.map((r) => ({ path: r.path, capsule: "", body: r.embed_text }));
  const truncArticles = asTrunc(data.articles);
  const truncMixed = asTrunc([...data.articles, ...data.journal]);
  const lexArtTrunc = new LexicalRetriever(); lexArtTrunc.index(truncArticles);
  const lexMixedTrunc = new LexicalRetriever(); lexMixedTrunc.index(truncMixed);

  // Carry the corpus cardinalities into the result. The paper quotes them beside
  // the rates, and an earlier draft took them from a different run than the one
  // it plotted, so they travel with the scores from here on.
  const out = {
    corpus: {
      articles: data.articles.length,
      journal: data.journal.length,
      eligible: data.eligible_count,
      step: data.step,
      // The mixed corpus a query actually ranks against, with its own entry excluded.
      mixed_candidates: data.articles.length + data.journal.length - 1,
      // How much of the corpus the embedding arm never sees. The paper quotes
      // these, and they are the measurement that priced the truncation defect, so
      // they are computed here from the same rows the rankers were given rather
      // than recorded by hand somewhere else.
      truncated_docs: rows.filter((r) => r.embed_text.length < r.text.length).length,
      total_docs: rows.length,
      truncated_share: Math.round(
        (rows.filter((r) => r.embed_text.length < r.text.length).length / rows.length) * 1000) / 10,
      chars_total: rows.reduce((s, r) => s + r.text.length, 0),
      chars_dropped: rows.reduce((s, r) => s + (r.text.length - r.embed_text.length), 0),
      chars_dropped_share: Math.round(
        (rows.reduce((s, r) => s + (r.text.length - r.embed_text.length), 0) /
         rows.reduce((s, r) => s + r.text.length, 0)) * 1000) / 10,
    },
  };
  for (const variant of ["full", "terse"]) {
    const queryTexts = data.queries.map((q) => q[variant]);
    const queryVectors = await embedAll(queryTexts);
    let n = 0;
    const hits = { emb_art: 0, emb_mixed: 0, lex_art: 0, lex_mixed: 0,
                   lextrunc_art: 0, lextrunc_mixed: 0, oracle_art: 0, oracle_mixed: 0 };

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
      if (lexRank(lexArtTrunc, truncArticles).some((p) => targets.has(p))) hits.lextrunc_art += 1;
      if (lexRank(lexMixedTrunc, truncMixed).some((p) => targets.has(p))) hits.lextrunc_mixed += 1;
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
    if (variant === "corpus") continue;
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
