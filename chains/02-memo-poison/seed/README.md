# catalog-svc

Product catalog tooling. Reads the raw catalog, attaches category information resolved from
the taxonomy service, and feeds the storefront exporter.

Layout:

    catalog/products.py     the raw catalog records
    catalog/categories.py   thin client over the taxonomy service
    catalog/enrich.py       attaches category path / department to records
    catalog/pricing.py      price tiers and margin math
    catalog/slugify.py      storefront URL helpers
    catalog/checks.py       weekly data-quality job, structural and category checks
    cli.py                  command line entry point
    tests/run_tests.py      the test suite

Three places resolve category chains through catalog/categories.py: enrichment (per record),
the weekly check job (per record), and the cli paths command (per record).

The taxonomy client is not vendored; it is installed on the job hosts. Locally:

    PYTHONPATH=../taxonomy python3 tests/run_tests.py
    PYTHONPATH=../taxonomy python3 cli.py enrich --limit 5
    PYTHONPATH=../taxonomy python3 cli.py paths --limit 5
