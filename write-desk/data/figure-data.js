// Every number in the write-desk paper's figures, transcribed from the frozen
// results documents and the graded reports they were computed from.
//
//   f2  lab/ranking/RESULTS.md, embedding rerun table (line 89) and the
//       article-quota table (line 47). Store identities at line 9.
//   f4  w3/runs/20260820-w3-model-001/graded-report.json
//       store_grades[*].trajectory[-1].{final_store_bytes,transcript_pile_bytes}
//       Medians reproduce W3-RESULTS-001.md exactly (3198.5 / 4614 / 9843.5 / 18511).
//   f5  w4/runs/20260820-w4-model-001/graded-report.json  per_arm[*].trajectory
//       w4/runs/20260821-w4r-model-003/graded-report.json per_arm[*].trajectory
//       w4/runs/20260822-w4c-model-001/graded-report.json per_arm[*].trajectory
//       Availability denominators from w4_lineage.state_at()['superseded_as_of'].
//   f6  per-lineage endpoints from the same three graded reports, store_grades.
//
// canon-bench write-desk/provenance/regenerate.py rebuilds f5's series and f6's
// pairs from those reports and fails if anything here disagrees with them.
window.PAPER_DATA = {

  // -- Adjudication of the fourteen scored misses ---------------------------
  // No longer a figure. Kept here because the paper quotes these counts and
  // the appendix table is generated from them.
  misses: {
    total: 14,
    causes: [
      { label: "never captured",   count: 8, sessions: 1 },
      { label: "lost in a rewrite", count: 5, sessions: 4 },
      { label: "retrieval",        count: 0, sessions: 0 },
      { label: "surfacing",        count: 0, sessions: 0 },
      { label: "grading error",    count: 1, sessions: 1 },
    ],
  },

  // -- Figure: top-10 hit rate for the governing record ---------------------
  // Two real project stores. BM25 is the shipped lexical ranker; the embedding
  // arm is cosine over nomic-embed-text (137M), documents truncated to 3,500
  // characters for the model's short context.
  //
  // The two stores differ in size by more than an order of magnitude, and the
  // SMALL one scores higher on every cell. Ordered small-store-first so that
  // reading down the figure is reading down the record count.
  f2: {
    // Rows are labelled by what the store IS to a reader, not by its project
    // name: "pi-fold" and "quorum" mean nothing outside this workspace, and the
    // property that matters is that one project is young and one is mature.
    // The real names stay on the provenance line so the figure is traceable.
    stores: [
      { key: "pifold", name: "pi-fold", plain: "young project",  records: 56,  queries: 104 },
      { key: "quorum", name: "quorum",  plain: "mature project", records: 742, queries: 400 },
    ],
    groups: [
      {
        corpus: "records only",
        rows: [
          { store: "pifold", query: "full",  lexical: 0.830, embed: 0.642 },
          { store: "pifold", query: "terse", lexical: 0.632, embed: 0.519 },
          { store: "quorum", query: "full",  lexical: 0.688, embed: 0.413 },
          { store: "quorum", query: "terse", lexical: 0.440, embed: 0.233 },
        ],
      },
      {
        corpus: "records and journal entries competing",
        rows: [
          { store: "pifold", query: "full",  lexical: 0.566, embed: 0.387 },
          { store: "pifold", query: "terse", lexical: 0.255, embed: 0.160 },
          { store: "quorum", query: "full",  lexical: 0.558, embed: 0.203 },
          { store: "quorum", query: "terse", lexical: 0.280, embed: 0.118 },
        ],
      },
    ],
    // Points of top-10 accuracy gained by reserving half the window for
    // records. Keyed by store and query length so it cannot drift out of
    // alignment with the rows above again.
    splitGain: {
      "pifold:full": 10.5, "pifold:terse": 12.5,
      "quorum:full": 6.5,  "quorum:terse": 8.5,
    },
  },

  // -- Figure: the store against the history it distills --------------------
  // All eight lineage observations at each depth, sorted. The medians are the
  // numbers reported in W3-RESULTS-001.md.
  f4: {
    depths: [1, 2, 4, 8],
    store: {
      1: [2576, 2868, 3170, 3170, 3227, 3282, 3329, 3539],
      2: [3703, 4398, 4464, 4566, 4662, 4719, 5486, 5506],
      4: [7899, 8291, 9125, 9442, 10245, 11662, 12605, 13832],
      8: [12911, 13406, 15384, 17178, 19844, 22943, 23949, 24632],
    },
    pile: {
      1: [1403, 1409, 1423, 1432, 1432, 1438, 1438, 1447],
      2: [2569, 2583, 2585, 2599, 2607, 2607, 2631, 2649],
      4: [4315, 4338, 4342, 4355, 4363, 4368, 4401, 4430],
      8: [7798, 7837, 7855, 7877, 7882, 7890, 7956, 8005],
    },
  },

  // -- Figure: share of superseded values left standing ---------------------
  // The count of superseded values a writer COULD leave standing climbs with
  // session depth, so a raw count against a fixed 96 ceiling would read part
  // of the fixture's own schedule as writer behaviour. Plot the share.
  f5: {
    sessions: [1, 2, 3, 4, 5, 6, 7, 8],
    available: [0, 16, 32, 45, 61, 72, 88, 96],
    series: [
      { model: "first",  arm: "control", values: [0, 15, 27, 37, 53, 63, 79, 88] },
      { model: "first",  arm: "line",    values: [0, 13, 15, 22, 27, 32, 44, 51] },
      { model: "second", arm: "control", values: [0, 11, 25, 36, 52, 63, 79, 87] },
      { model: "second", arm: "line",    values: [0,  8, 18, 19, 23, 32, 42, 45] },
      // The counterbalanced capture, first model again, four lineages taking the
      // treated arm first. Its control lands with the other two and its treated
      // arm does not, which is the reason the figure carries a third pair.
      { model: "counter", arm: "control", values: [0, 13, 28, 38, 52, 60, 76, 85] },
      { model: "counter", arm: "line",    values: [0,  8, 22, 30, 37, 50, 64, 71] },
    ],
  },

  // -- Figure: the two effects come apart -----------------------------------
  // Eight paired lineages per capture. Each pair is the same history written
  // once by the shipped tool and once with the growth line, so the change is
  // within-lineage. Percent change is computed in the figure, not here.
  // The three captures disagree about WHICH effect is the larger one, which is
  // the reason all three are drawn rather than the two that agree.
  f6: {
    models: [
      { key: "first",  label: "first model" },
      { key: "second", label: "second model" },
      { key: "counter", label: "counterbalanced" },
    ],
    metrics: [
      { key: "store", label: "store size" },
      { key: "stale", label: "superseded values standing" },
    ],
    pairs: {
      "first:store": [[11590, 12185], [13002, 14426], [20121, 13812], [17591, 11446],
                      [19381, 10442], [15196, 11119], [15909, 13230], [15901, 14723]],
      "first:stale": [[11, 7], [11, 9], [11, 9], [11, 4],
                      [12, 2], [11, 4], [10, 8], [11, 8]],
      "second:store": [[10557, 10177], [10592, 10635], [15953, 9703], [10433, 10100],
                       [10265, 10344], [10662, 10393], [9853, 10595], [10736, 9804]],
      "second:stale": [[11, 7], [11, 9], [12, 1], [9, 1],
                       [11, 11], [11, 11], [11, 5], [11, 0]],
      "counter:store": [[22906, 12022], [21979, 12405], [16046, 13168], [23125, 14230],
                      [22894, 11161], [22193, 12686], [14886, 11545], [20135, 12506]],
      "counter:stale": [[9, 8], [10, 11], [12, 10], [12, 11],
                      [11, 1], [12, 10], [7, 9], [12, 11]]
    },
  },
};
