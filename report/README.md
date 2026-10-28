Optional PDF export (requires [pandoc](https://pandoc.org/) and a LaTeX engine):

```bash
pandoc report/report.md -o report/report.pdf --resource-path=.:report
```

Figures reference `../results/` from the Markdown source; keep `--resource-path` so images embed correctly.
