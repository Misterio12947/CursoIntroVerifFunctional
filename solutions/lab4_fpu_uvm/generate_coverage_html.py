#!/usr/bin/env python3
"""
Genera coverage_report.html a partir de coverage.yml.

Uso:
    python3 generate_coverage_html.py

Lee coverage.yml (escrito por cocotb_coverage.coverage_db.export_to_yaml)
y produce coverage_report.html con tablas de cobertura por CoverPoint.

Diseño: archivo único, solo stdlib, sin dependencias externas.
"""

import sys
import html as html_lib
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML no está instalado. cocotb-coverage debería traerlo "
          "como dependencia. Instálalo con: pip install pyyaml")
    sys.exit(1)


def load_coverage(path):
    """Carga el YAML de cobertura."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def render_bar(pct, width=200):
    """Barra de progreso HTML inline (SVG)."""
    pct = max(0.0, min(100.0, float(pct)))
    fill_width = int(width * pct / 100)
    color = "#22c55e" if pct >= 100 else ("#eab308" if pct >= 50 else "#ef4444")
    return (
        f'<svg width="{width}" height="18" style="vertical-align:middle">'
        f'  <rect x="0" y="0" width="{width}" height="18" fill="#e5e7eb"/>'
        f'  <rect x="0" y="0" width="{fill_width}" height="18" fill="{color}"/>'
        f'  <text x="{width//2}" y="13" text-anchor="middle" '
        f'        font-family="monospace" font-size="11" fill="#000">'
        f'    {pct:.1f}%'
        f'  </text>'
        f'</svg>'
    )


def render_html(coverage_data):
    """Convierte el dict de cobertura a HTML."""
    rows = []
    overall_total = 0
    overall_hit = 0

    for name in sorted(coverage_data.keys()):
        item = coverage_data[name]
        if not isinstance(item, dict):
            continue
        # cocotb-coverage exporta cada CoverPoint con keys 'size', 'coverage', 'bins'.
        size = item.get("size", 0)
        cov_count = item.get("coverage", 0)
        pct = (100.0 * cov_count / size) if size > 0 else 0.0
        overall_total += size
        overall_hit += cov_count

        bins_html = "<ul style='margin:0;padding-left:20px'>"
        bins = item.get("bins", {})
        if isinstance(bins, dict):
            for bin_name, hits in bins.items():
                bin_str = html_lib.escape(str(bin_name))
                status = "✅" if hits > 0 else "❌"
                color = "#16a34a" if hits > 0 else "#dc2626"
                bins_html += (
                    f"<li style='color:{color}'>{status} "
                    f"<code>{bin_str}</code>: {hits} hits</li>"
                )
        bins_html += "</ul>"

        rows.append(f"""
        <tr>
          <td><code>{html_lib.escape(name)}</code></td>
          <td style="text-align:right">{cov_count} / {size}</td>
          <td>{render_bar(pct)}</td>
          <td>{bins_html}</td>
        </tr>""")

    overall_pct = (100.0 * overall_hit / overall_total) if overall_total > 0 else 0.0

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Coverage Report — Lab 4 FPU</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif;
          max-width: 1100px; margin: 2em auto; padding: 0 1em;
          color: #1f2937; background: #f9fafb; }}
  h1 {{ color: #111827; border-bottom: 2px solid #6366f1; padding-bottom: 8px; }}
  .summary {{ background: white; padding: 1em 1.5em; border-radius: 8px;
              box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 1.5em; }}
  table {{ width: 100%; border-collapse: collapse; background: white;
           border-radius: 8px; overflow: hidden;
           box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  th {{ background: #6366f1; color: white; padding: 12px; text-align: left; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 3px;
          font-size: 0.9em; }}
  .footer {{ margin-top: 2em; color: #6b7280; font-size: 0.85em; text-align: center; }}
</style>
</head>
<body>

<h1>Coverage Report — Lab 4 FPU</h1>

<div class="summary">
  <strong>Cobertura global:</strong>
  {render_bar(overall_pct, width=400)}
  &nbsp;&nbsp;{overall_hit} / {overall_total} bins hit
</div>

<table>
  <thead>
    <tr>
      <th>CoverPoint</th>
      <th>Hits / Size</th>
      <th>Cobertura</th>
      <th>Bins</th>
    </tr>
  </thead>
  <tbody>
    {''.join(rows)}
  </tbody>
</table>

<div class="footer">
  Generado por <code>generate_coverage_html.py</code> · cocotb-coverage 1.2.0
</div>

</body>
</html>
"""


def main():
    yml_path = Path("coverage.yml")
    if not yml_path.exists():
        print("ERROR: coverage.yml no encontrado. Ejecuta primero 'make' "
              "para generar el reporte de cobertura.")
        sys.exit(1)

    coverage_data = load_coverage(yml_path)
    html_content = render_html(coverage_data)

    out_path = Path("coverage_report.html")
    out_path.write_text(html_content, encoding="utf-8")
    print(f"Coverage HTML escrito en: {out_path.resolve()}")


if __name__ == "__main__":
    main()
