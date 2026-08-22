/* R1 embedding rerun: does a semantic ranker clear the lexical ceiling on the
   same known-item harness? Same metrics and the same harness as r1_decompose;
   the ranker is cosine over local Ollama embeddings (nomic-embed-text, 137M;
   qwen3-embedding:8b was tried first and does not fit the 6GB card with long
   documents), so nothing leaves the machine and the run costs nothing.

   NOT the same stores and not the same queries, despite what an earlier version
   of this comment said. The paths below are live project stores and the eligible
   query set is derived at execution time, so both move as the projects are used.
   Six of the eight BM25 cells differ from the r1_decompose run by up to 0.008.
   The comparison this script supports is within one execution, where both rankers
   score one corpus state. Reruns will not reproduce either run's numbers. Embeddings cache to disk keyed by content hash, so reruns are
   incremental.

   Conditions reported per store and query variant, embedding vs shipped BM25:
     art_only@10  - the DEFAULT search surface since journal became opt-in
     mixed@10     - the journal:true combined ranking (pre-split, comparability)
   Usage: node lab/ranking/r1_embed.mjs [maxQueriesPerStore] */

import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { CanonStore } from "../../extensions/lib/store.ts";
import { LexicalRetriever } from "../../extensions/lib/retrieval.ts";

const MAX_QUERIES = Number(process.argv[2] ?? 400);
const HOME = "/home/shane";
const PROJECTS = ["quorum", "pi-fold"];
const MODEL = "nomic-embed-text";
const OLLAMA = process.env.OLLAMA_HOST || "http://127.0.0.1:11434";
const BATCH = 8;
const MAX_CHARS = 3500;
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
      out[i] = vector;
      cache[key] = vector;
      cacheDirty += 1;
    });
    if (cacheDirty >= 200) {
      writeFileSync(CACHE, JSON.stringify(cache));
      cacheDirty = 0;
    }
    process.stderr.write(`embedded ${Math.min(at + BATCH, missing.length)}/${missing.length}\r`);
  }
  if (cacheDirty) writeFileSync(CACHE, JSON.stringify(cache));
  return out;
}

function cosine(a, b) {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i += 1) {
    dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i];
  }
  return dot / (Math.sqrt(na) * Math.sqrt(nb) || 1);
}

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

const docText = (c) => `${c.path} ${c.capsule} ${c.body}`.slice(0, MAX_CHARS);

for (const project of PROJECTS) {
  const root = join(HOME, project, ".canon");
  if (!existsSync(root)) continue;
  const store = new CanonStore(root);
  const articles = [];
  for (const path of store.list()) {
    const a = store.read(path);
    if (a) articles.push({ path, capsule: a.capsule, body: a.body, updated: a.updated, declared: false });
  }
  const articleSet = new Set(articles.map((a) => a.path));
  const entries = store.journalEntries();
  const journalDocs = entries.map((e) => ({
    path: `journal/${e.name.replace(/\.md$/, "")}`,
    capsule: e.subjects.join(", "), body: e.body, updated: e.logged, declared: false,
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

  const mixed = [...articles, ...journalDocs];
  const mixedVectors = await embedAll(mixed.map(docText));
  const vecByPath = new Map(mixed.map((c, i) => [c.path, mixedVectors[i]]));

  const lexMixed = new LexicalRetriever(); lexMixed.index(mixed);
  const lexArt = new LexicalRetriever(); lexArt.index(articles);

  const out = {};
  for (const variant of ["full", "terse"]) {
    const queryTexts = sample.map((q) => variants(q.e.body)[variant]);
    const queryVectors = await embedAll(queryTexts);
    let n = 0;
    const hits = { emb_art: 0, emb_mixed: 0, lex_art: 0, lex_mixed: 0 };
    for (let qi = 0; qi < sample.length; qi += 1) {
      const q = sample[qi];
      const self = `journal/${q.e.name.replace(/\.md$/, "")}`;
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

      if (embRank(articles).some((p) => targets.has(p))) hits.emb_art += 1;
      if (embRank(mixed).some((p) => targets.has(p))) hits.emb_mixed += 1;
      if (lexRank(lexArt, articles).some((p) => targets.has(p))) hits.lex_art += 1;
      if (lexRank(lexMixed, mixed).some((p) => targets.has(p))) hits.lex_mixed += 1;
    }
    out[variant] = Object.fromEntries(Object.entries(hits).map(
      ([k, v]) => [k + "_recall_at_10", Math.round((v / n) * 1000) / 1000]));
    out[variant].n = n;
  }
  console.log(project, JSON.stringify(out, null, 2));
}
