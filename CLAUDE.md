# CLAUDE.md

From-scratch gas turbine performance model (standard atmosphere → ideal Brayton cycle → real
components → two-spool turbofan → off-design → trade studies).
Plan: `AERO-03-propulsion-from-scratch-PLAN.md` (tick the phase checkboxes as phases land).

## Commands
- `uv sync` — install deps (numpy, scipy, matplotlib; dev: pytest, ruff, nbclient)
- `uv run pytest` — tests
- `uv run ruff check . && uv run ruff format --check .` — lint/format (CI runs both). Ruff also
  formats the ```python blocks inside Markdown, so run it after editing docs too
- `uv run python validation/run_all.py` — regenerate every validation figure (`docs/figures/`)
  and results table (`validation/results/`); single scripts also run on their own
- `uv run python notebooks/build_notebooks.py` — regenerate and execute the notebooks (edit cell
  sources there, never the .ipynb JSON); rebuilds are byte-identical
- `uv run python docs/lessons/make_figures.py` — regenerate the lesson figures

## Layout
- `src/propulsion/` — single package; subpackages mirror the plan: `atmosphere`, `gas`,
  `brayton_cycle`, `component_models`, `turbofan_model`, `off_design_performance`,
  `trade_studies`; `plotting.py` shared.
- `tests/` — pytest, one file per module. `validation/` — scripts + cited reference data.
- `docs/` — theory note per module, validation report, figures; `docs/lessons/` is the lesson
  course, one lesson per phase (keep its numbers in sync with the code). `notebooks/` — demos.

## Conventions
- **SI units internally** (K, Pa, kg/s, N, J/kg). Helpers that take or return other units say so
  in the name (`*_lbf`, `*_ft`, `*_lb_per_lbf_h`, `*_deg`). TSFC is kg/(N·s) internally.
- Station numbers follow SAE ARP755 / Mattingly: 0 free stream, 2 fan/compressor face,
  13 fan exit, 19 fan nozzle exit, 25 HPC inlet, 3 HPC exit, 4 burner exit, 45 HPT exit,
  5 LPT exit, 9 core nozzle exit. `Tt`/`Pt` are stagnation, `T`/`P` static.
- Mattingly's ratio notation: `tau_x = Tt_out/Tt_in`, `pi_x = Pt_out/Pt_in` for component x;
  `tau_r`, `pi_r` ram; `tau_lambda = cpt Tt4 / (cpc T0)`; bypass ratio `alpha`.
- Gas model: calorically perfect, with separate cold (`cpc`, `gamma_c`) and hot (`cpt`,
  `gamma_t`) properties after the burner. Default values are assumptions, cited to the textbook.
- Pure NumPy/SciPy — no thermodynamics or engine-performance libraries.

## Docs (GitHub-rendered math)
- Display equations go in ```` ```math ```` fences (no Markdown processing inside).
- Inline `$...$` is processed as Markdown first: no `\,` or `\;` (they become `,` `;`), no `\\`
  row breaks (put matrices in a display block), and no `_` right after `}` `)` `]` (it starts
  emphasis; write `\tau_{c}^{\ast}`, not `\tau^{\ast}_{c}`).

## Testing rules
- Every test asserts against a closed-form result or a cited published value; name the source
  in a comment. Never loosen a tolerance to make a failing model pass without explaining why.
- Cite textbooks at chapter level unless the section/table number has been checked in the book.
- Reference data in `validation/reference_data/` must carry its citation (document, issue,
  table). Do not invent data: leave a value out if it cannot be checked against its source.
- Assumed design inputs (Tt4, component efficiencies, cp/gamma, fuel heating value) are
  labelled as assumptions, never presented as engine data.
- No employer references in the repo; name engine families and aircraft only.

## Workflow
- Commit small logical changes directly to `main`, push after `ruff` + `pytest` pass.
- Each phase lands as code + tests, then its lesson in `docs/lessons/` as a separate commit.
