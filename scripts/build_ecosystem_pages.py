"""Generate Quarto pages for each ecosystem from config YAML files.

For each config/ecosystems/*/ecosystem.yaml, creates two pages under
content/3_ecosystem_assessments/{ecosystem_code}/:
  - {ecosystem_code}.qmd         — main assessment page
  - {ecosystem_code}_crit_b.qmd  — Criterion B computational notebook

Existing files are not overwritten unless --overwrite is passed.
"""

import argparse
from pathlib import Path

import yaml

CONFIG_DIR = Path("config/ecosystems")
OUTPUT_DIR = Path("content/3_ecosystem_assessments")
QUARTO_YML = Path("_quarto.yml")


def _build_criteria_table(criteria_status: dict) -> str:
    """Build an HTML criteria status table from the criteria_status dict."""
    rows = []
    criteria_order = [
        ("A", ["A1", "A2a", "A2b", "A3"]),
        ("B", ["B1", "B2", "subcriteria", "B3"]),
        ("C", ["C1", "C2a", "C2b", "C3"]),
        ("D", ["D1", "D2a", "D2b", "D3"]),
        ("E", ["E"]),
    ]
    for criterion, subcriteria in criteria_order:
        status = criteria_status.get(criterion, {})
        for i, sub in enumerate(subcriteria):
            value = status.get(sub, "NE")
            if i == 0:
                rows.append(
                    f'    <tr>\n'
                    f'      <td rowspan="{len(subcriteria)}">Criterion {criterion}</td>\n'
                    f'      <td>{sub}</td>\n'
                    f'      <td>{value}</td>\n'
                    f'    </tr>'
                )
            else:
                rows.append(
                    f'    <tr>\n'
                    f'      <td>{sub}</td>\n'
                    f'      <td>{value}</td>\n'
                    f'    </tr>'
                )

    return (
        '<table class="criteria-table">\n'
        '  <thead>\n'
        '    <tr>\n'
        '      <th colspan="2">Criteria</th>\n'
        '      <th>Status</th>\n'
        '    </tr>\n'
        '  </thead>\n'
        '  <tbody>\n'
        + "\n".join(rows) + "\n"
        '  </tbody>\n'
        '</table>'
    )


def _slugify_label(code: str) -> str:
    """Convert an ecosystem code to a Quarto cross-ref label.

    E.g. 'T1.1.1' -> 't1-1-1'
    """
    return code.lower().replace(".", "-")


def _render_main_page(eco: dict) -> str:
    """Render the main assessment .qmd page from an ecosystem config dict."""
    code = eco["global_classification"]
    slug = _slugify_label(code)
    name = eco.get("ecosystem_name", code)
    authors = ", ".join(eco.get("authors", []))
    credits = eco.get("assessment_credits", {})

    criteria_table = _build_criteria_table(eco.get("criteria_status", {}))

    return f"""\
---
suppress-bibliography: true
---

# {name} {{.unnumbered}}

<!-- Authors -->
[Authors:]{{.parameter}}&nbsp;
{authors}

<!-- Biome -->
[Biome:]{{.parameter}}&nbsp;
{eco.get("biome", "TODO")}

<!-- Functional Group -->
[Functional Group:]{{.parameter}}&nbsp;
{eco.get("functional_group", "TODO")}

<!-- Global classification -->
[Global classification:]{{.parameter}}&nbsp;
{code}

<!-- IUCN Status -->
[IUCN Status:]{{.parameter}}&nbsp;
{eco.get("iucn_status", "TODO")}

<!-- Description -->
[Description:]{{.parameter}}&nbsp;
{eco.get("description", "TODO")}

<!-- Distribution -->
[Distribution:]{{.parameter}}&nbsp;
{eco.get("distribution", "TODO")}

<!-- Characteristic Native Biota -->
[Characteristic Native Biota:]{{.parameter}}&nbsp;
{eco.get("characteristic_native_biota", "TODO")}

<!-- Abiotic environment -->
[Abiotic environment:]{{.parameter}}&nbsp;
{eco.get("abiotic_environment", "TODO")}

<!-- Key processes and interactions -->
[Key processes and interactions:]{{.parameter}}&nbsp;
{eco.get("key_processes_and_interactions", "TODO")}

<!-- Major threats -->
[Major threats:]{{.parameter}}&nbsp;
{eco.get("major_threats", "TODO")}

<!-- Ecosystem collapse definition -->
[Ecosystem collapse definition:]{{.parameter}}&nbsp;
{eco.get("ecosystem_collapse_definition", "TODO")}

<!-- Assessment summary -->
[Assessment summary:]{{.parameter}}&nbsp;
**{eco.get("assessment_summary", "TODO")}**

<!-- Assessment information -->
[Assessment information:]{{.parameter}}&nbsp;
{criteria_table}

<!-- Assessment outcome -->
[Assessment outcome:]{{.parameter}}&nbsp;
**{eco.get("assessment_outcome", "TODO")}**

<!-- Year published -->
[Year published:]{{.parameter}}&nbsp;
{eco.get("year_published", "TODO")}

<!-- Date assessed -->
[Date assessed:]{{.parameter}}&nbsp;
{eco.get("date_assessed", "TODO")}

<!-- Assessment credits -->
[Assessment credits:]{{.parameter}}&nbsp;

Assessed by: {credits.get("assessed_by", "TODO")}

Reviewed by: {credits.get("reviewed_by", "TODO")}

Contributions by: {credits.get("contributions_by", "TODO")}

<!-- Criterion A -->
[[Criterion A](../../7_glossary.md#criterion-a):]{{.parameter}}&nbsp;
{eco.get("criterion_a_description", "TODO")}

<!-- Criterion B -->
[[Criterion B](../../7_glossary.md#criterion-b):]{{.parameter}}&nbsp;
{{{{embed}}}}`{slug}-crit-b-summary`

{eco.get("criterion_b_description", "TODO")}

<!-- Criterion C -->
[[Criterion C](../../7_glossary.md#criterion-c):]{{.parameter}}&nbsp;
{eco.get("criterion_c_description", "TODO")}

<!-- Criterion D -->
[[Criterion D](../../7_glossary.md#criterion-d):]{{.parameter}}&nbsp;
{eco.get("criterion_d_description", "TODO")}

<!-- Criterion E -->
[[Criterion E](../../7_glossary.md#criterion-e):]{{.parameter}}&nbsp;
{eco.get("criterion_e_description", "TODO")}
"""


def _render_crit_b_page(eco: dict) -> str:
    """Render the Criterion B computational notebook .qmd page."""
    code = eco["global_classification"]
    slug = _slugify_label(code)
    name = eco.get("ecosystem_name", code)

    return f"""\
---
jupyter: python3
---

# {code} Criterion B Details {{.unnumbered}}

This notebook provides step-by-step details on Criterion B calculations
for {name}.

# Setup

```{{python}}
import os

import yaml
from lonboard import Map
from rle_python_gee.ecosystems import Ecosystems
from rle_python_gee.eoo import make_eoo
from rle_python_gee.aoo import make_aoo_grid
```

```{{python}}
# Load the country config
config_path = os.path.join(os.environ['PIXI_PROJECT_ROOT'], 'config/country_config.yaml')
with open(config_path) as f:
    config = yaml.safe_load(f)
```

# Load Ecosystem Data

```{{python}}
ecosystem_code = '{code}'

source = config['ecosystem_source']
ecosystems = Ecosystems.from_file(
    source['data'],
    ecosystem_column=source['ecosystem_code_column'],
)
ecosystem = ecosystems.filter(ecosystem_code)
print(f'{{ecosystem.size()=}}')
```

# Extent of Occurrence (EOO) (subcriterion B1)

```{{python}}
eoo = make_eoo(ecosystem).compute()
print(f'EOO area: {{eoo.area_km2:.0f}} km²')
```

```{{python}}
display(Map(layers=eoo.to_layer() + ecosystem.to_layer()))
```

# Area of Occupancy (AOO) (subcriterion B2)

The protocol for this adjustment includes the following steps:

> - Intersect AOO grid with the ecosystem's distribution map.
> - Calculate extent of the ecosystem type in each grid cell ('area') and sum these areas to obtain the total ecosystem area ('total area').
> - Arrange grid cells in ascending order based on their area (smaller first).
> - Calculate accumulated sum of area per cell ('cumulative area').
> - Calculate 'cumulative proportion' by dividing 'cumulative area' by 'total area'.
> - Calculate AOO by counting the number of cells with a 'cumulative proportion' greater than 0.01.

```{{python}}
aoo_grid = make_aoo_grid(ecosystems).compute()
aoo_grid_filtered = aoo_grid.filter_by_ecosystem(ecosystem_code)
```

```{{python}}
aoo_count = ecosystem.calculate_aoo()
print(f'AOO: {{aoo_count}} grid cells')
```

```{{python}}
display(Map(layers=aoo_grid_filtered.to_layer() + ecosystem.to_layer()))
```

# Criterion B Summary

```{{python}}
#| label: {slug}-crit-b-summary
from IPython.display import Markdown, display
display(
    Markdown(
        f'AOO and EOO were measured as '
        f'{{aoo_count}} 10 x 10 km grid cells '
        f'and {{eoo.area_km2:.0f}} km², respectively. '
        f'See [Criterion B Details]({slug}-crit-b-details) for more information.'
    )
)
```
"""


def _update_quarto_yml(eco_configs: list[Path]) -> None:
    """Update _quarto.yml to include ecosystem assessment pages.

    Inserts ecosystem pages before 'references.qmd' in the chapters list.
    Removes any previously inserted ecosystem assessment entries first.
    """
    text = QUARTO_YML.read_text()

    # Build the new entries grouped by ecosystem
    new_entries = []
    for eco_path in eco_configs:
        with open(eco_path) as f:
            eco = yaml.safe_load(f)
        code = eco["global_classification"]
        prefix = f"{OUTPUT_DIR}/{code}/{code}"
        name = eco.get("ecosystem_name", code)
        new_entries.append(f'    - part: "{name} ({code})"')
        new_entries.append(f"      chapters:")
        new_entries.append(f'        - text: "{code} Assessment"')
        new_entries.append(f"          file: {prefix}.qmd")
        new_entries.append(f"        - {prefix}_crit_b.qmd")

    # Remove existing ecosystem assessment blocks.
    # A block is: "- part: ..." + "chapters:" + chapter lines referencing OUTPUT_DIR
    lines = text.splitlines()
    filtered = []
    i = 0
    while i < len(lines):
        # Detect a part/section block for ecosystem assessments
        if lines[i].strip().startswith("- part:") or lines[i].strip().startswith("- section:"):
            # Look ahead to see if this part contains ecosystem assessment pages
            j = i + 1
            while j < len(lines) and (
                lines[j].strip() in ("chapters:", "contents:")
                or lines[j].strip().startswith("- text:")
                or lines[j].strip().startswith("text:")
                or f"{OUTPUT_DIR}/" in lines[j]
            ):
                j += 1
            if j > i + 1:  # We consumed at least one line after the part
                i = j
                continue
        # Also remove flat (non-grouped) ecosystem assessment lines
        if f"{OUTPUT_DIR}/" in lines[i]:
            i += 1
            continue
        filtered.append(lines[i])
        i += 1

    # Insert new entries before references.qmd
    result = []
    for ln in filtered:
        if ln.strip() == "- references.qmd":
            result.extend(new_entries)
        result.append(ln)

    QUARTO_YML.write_text("\n".join(result) + "\n")
    print(f"  Updated {QUARTO_YML}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Overwrite existing .qmd files",
    )
    args = parser.parse_args()

    eco_configs = sorted(CONFIG_DIR.glob("*/ecosystem.yaml"))
    if not eco_configs:
        print(f"No ecosystem configs found in {CONFIG_DIR}/")
        return

    for eco_path in eco_configs:
        with open(eco_path) as f:
            eco = yaml.safe_load(f)

        code = eco["global_classification"]
        out_dir = OUTPUT_DIR / code
        main_page = out_dir / f"{code}.qmd"
        crit_b_page = out_dir / f"{code}_crit_b.qmd"

        out_dir.mkdir(parents=True, exist_ok=True)

        for page_path, renderer in [
            (main_page, _render_main_page),
            (crit_b_page, _render_crit_b_page),
        ]:
            if page_path.exists() and not args.overwrite:
                print(f"  Skipping {page_path} (already exists)")
                continue
            page_path.write_text(renderer(eco))
            print(f"  Created {page_path}")

    # Update _quarto.yml chapters list
    _update_quarto_yml(eco_configs)

    print(f"\nDone. Pages are in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
