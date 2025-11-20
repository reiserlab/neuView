"""
Interactive Scatterplot Service

Simplified service that coordinates other specialized services to create
interactive scatterplot page with plots related to the spatial metrics per type.
"""

import logging
from pathlib import Path
import pandas as pd
from math import ceil, floor, log10, isfinite
from ..result import Err
from jinja2 import Environment, FileSystemLoader, Template
from ..config import Config
from ..utils import get_templates_dir

from .index_service import IndexService
from ..visualization.rendering.rendering_config import ScatterConfig

logger = logging.getLogger(__name__)


class ScatterplotService:
    """Service for creating scatterplots with markers for all available neuron types."""

    def __init__(self):

        self.config = Config.load("config.yaml")
        self.scatter_config = ScatterConfig()

        if isinstance(self.scatter_config.scatter_dir, str):
            self.plot_output_dir = self.scatter_config.scatter_dir
            plot_dir = Path(self.plot_output_dir)
            plot_dir.mkdir(parents=True, exist_ok=True)

        # Initialize cache manager for neuron type data
        self.cache_manager = None
        if (
            self.config
            and hasattr(self.config, "output")
            and hasattr(self.config.output, "directory")
        ):
            self.output_dir = self.config.output.directory
            from ..cache import create_cache_manager

            self.cache_manager = create_cache_manager(self.output_dir)

    async def create_scatterplots(self):
        """Create scatterplots of spatial metrics for optic lobe neuron types."""

        try:
            page_generator = (
                None  # or a tiny stub object if your constructors assume methods exist
            )
            index = IndexService(self.config, page_generator)

            # 3) Use the instance properly
            neuron_types, _ = index.discover_neuron_types(Path(self.output_dir))
            if not neuron_types:
                return Err("No neuron type HTML files found in output directory")

            # Initialize connector if needed for database lookups
            connector = await index.initialize_connector_if_needed(
                neuron_types, self.output_dir
            )

            # Correct neuron names (convert filenames back to original names)
            corrected_neuron_types, _ = index.correct_neuron_names(
                neuron_types, connector
            )

            # Generate scatterplot data for corrected neuron types
            plot_data = self._extract_plot_data(corrected_neuron_types)

            # Within loop for side
            side = "both"

            for region in ["ME", "LO", "LOP"]:
                points = self._extract_points(plot_data, side=side, region=region)

                ctx = self._prepare(
                    self.scatter_config, points, side=side, region=region
                )

                template_dir = get_templates_dir()
                template_env = Environment(loader=FileSystemLoader(template_dir))
                template = template_env.get_template(self.scatter_config.template_name)
                svg_content = template.render(**ctx)

                # Write the index file
                svg_path = f"{self.plot_output_dir}/{region}_{self.scatter_config.scatter_fname}"

                # If saving the images - check if they exist first
                with open(svg_path, "w", encoding="utf-8") as f:
                    f.write(svg_content)

            return

        except Exception as e:
            logger.error(f"Failed to create scatterplots: {e}")
            return Err(f"Failed to create scatterplots: {str(e)}")

    def _extract_plot_data(self, neuron_types):
        """Generate plot data from list of neuron types."""

        cached_data_lazy = (
            self.cache_manager.get_cached_data_lazy() if self.cache_manager else None
        )

        plot_data, cached_count, missing_cache_count = [], 0, 0

        names = neuron_types.keys() if isinstance(neuron_types, dict) else neuron_types

        for neuron_name in names:

            cache_data = (
                cached_data_lazy.get(neuron_name)
                if cached_data_lazy is not None
                else None
            )

            entry = {
                "name": neuron_name,
                "total_count": 0,
                "left_count": 0,
                "right_count": 0,
                "middle_count": 0,
                "undefined_count": 0,
                "has_undefined": False,
                "spatial_metrics": {},
            }

            if cache_data is not None:
                # ---- counts ----
                if (
                    hasattr(cache_data, "total_count")
                    and cache_data.total_count is not None
                ):
                    entry["total_count"] = cache_data.total_count

                ssc = {}
                if (
                    hasattr(cache_data, "soma_side_counts")
                    and cache_data.soma_side_counts
                ):
                    ssc = cache_data.soma_side_counts

                if isinstance(ssc, dict):
                    if "left" in ssc and ssc["left"] is not None:
                        entry["left_count"] = ssc["left"]
                    if "right" in ssc and ssc["right"] is not None:
                        entry["right_count"] = ssc["right"]
                    if "middle" in ssc and ssc["middle"] is not None:
                        entry["middle_count"] = ssc["middle"]

                    undefined_sum = 0
                    if "unknown" in ssc and ssc["unknown"] is not None:
                        undefined_sum += ssc["unknown"]
                    if "undefined" in ssc and ssc["undefined"] is not None:
                        undefined_sum += ssc["undefined"]
                    entry["undefined_count"] = undefined_sum
                    entry["has_undefined"] = undefined_sum > 0

                # ---- spatial metrics (raw) ----
                sm = {}
                if (
                    hasattr(cache_data, "spatial_metrics")
                    and cache_data.spatial_metrics
                ):
                    sm = cache_data.spatial_metrics

                # ---- roi_summary source (for incl_scatter) ----
                roi_source = {}
                if hasattr(cache_data, "roi_summary") and cache_data.roi_summary:
                    rs = cache_data.roi_summary
                    if isinstance(rs, dict):
                        roi_source = rs
                    elif isinstance(rs, list):
                        # turn [{'name': 'ME', ...}, ...] into {'ME': {...}, ...} if applicable
                        tmp = {}
                        for item in rs:
                            if isinstance(item, dict) and "name" in item:
                                nm = item["name"]
                                tmp[nm] = item
                        roi_source = tmp

                # ---- write incl_scatter into each side/region dict ----
                # If you only want it under "both", change sides_to_update = ("both",)
                sides_to_update = ("both", "L", "R")
                for region in ("ME", "LO", "LOP"):
                    incl_val = None
                    if isinstance(roi_source, dict) and region in roi_source:
                        region_src = roi_source[region]
                        if (
                            isinstance(region_src, dict)
                            and "incl_scatter" in region_src
                        ):
                            incl_val = region_src["incl_scatter"]

                    for side_key in sides_to_update:
                        if isinstance(sm, dict):
                            if side_key not in sm or sm[side_key] is None:
                                sm[side_key] = {}
                            side_dict = sm[side_key]
                            if region not in side_dict or side_dict[region] is None:
                                side_dict[region] = {}
                            region_dict = side_dict[region]
                            if isinstance(region_dict, dict):
                                region_dict["incl_scatter"] = incl_val

                # finally attach sm
                entry["spatial_metrics"] = sm

                logger.debug(f"Used cached data for {neuron_name}")
                cached_count += 1
            else:
                logger.debug(f"No cached data available for {neuron_name}")
                missing_cache_count += 1

            plot_data.append(entry)

        plot_data.sort(key=lambda x: x["name"])

        if missing_cache_count > 0:
            logger.warning(
                f"Plot data generation completed: {len(plot_data)} entries, "
                f"{cached_count} with cache, {missing_cache_count} missing cache. "
                f"Run 'quickpage generate' to populate cache."
            )
        else:
            logger.info(
                f"Plot data generation completed: {len(plot_data)} entries, all with cached data"
            )

        return plot_data

    def _extract_points(self, plot_data, side, region):
        """
        Collate the data points required to make the spatial
        metric scatterplots.
        """
        pts = []
        for rec in plot_data:

            incl = (
                rec.get("spatial_metrics", {})
                .get(side, {})
                .get(region, {})
                .get("incl_scatter")
            )

            # Only include types that have "incl_scatter" == 1.
            # Pass threshold for syn % and syn #.
            if incl == 1:
                name = rec.get("name", "unknown")
                x = rec.get("total_count")
                y = (
                    rec.get("spatial_metrics", {})
                    .get(side, {})
                    .get(region, {})
                    .get("cell_size")
                )
                c = (
                    rec.get("spatial_metrics", {})
                    .get(side, {})
                    .get(region, {})
                    .get("coverage")
                )
                col_count = (
                    rec.get("spatial_metrics", {})
                    .get(side, {})
                    .get(region, {})
                    .get("cols_innervated")
                )

                # require x,y positive for log scales
                if x is None or y is None or c is None:
                    continue
                try:
                    x = float(x)
                    y = float(y)
                    c = float(c)
                except Exception:
                    continue
                if x <= 0 or y <= 0:
                    continue

                # Optional data quality filter from prior script
                if col_count is not None:
                    try:
                        if float(col_count) <= 9:
                            continue
                    except Exception:
                        pass

                pts.append(
                    {
                        "name": name,
                        "x": x,
                        "y": y,
                        "coverage": c,
                        "col_count": (
                            float(col_count) if col_count is not None else None
                        ),
                    }
                )
        return pts

    def _prepare(
        self,
        config,
        points,
        side=None,
        region=None,
    ):
        """Compute pixel positions for an SVG scatter plot (color by coverage)."""

        # Range depends on values of "points"
        xmin = min(p["x"] for p in points)
        xmax = max(p["x"] for p in points)
        ymin = min(p["y"] for p in points)
        ymax = max(p["y"] for p in points)

        # expand bounds slightly so dots don't sit on the frame (keep >0)
        pad_x = xmin * 0.05
        pad_y = ymin * 0.08
        xmin = max(1e-12, xmin - pad_x)
        ymin = max(1e-12, ymin - pad_y)
        xmax *= 1.05
        ymax *= 1.08

        lxmin, lxmax = log10(xmin), log10(xmax)
        lymin, lymax = log10(ymin), log10(ymax)
        dx = lxmax - lxmin
        dy = lymax - lymin

        if dx > dy:
            # expand Y range to match X span (around geometric center)
            cy = (lymin + lymax) / 2.0
            lymin, lymax = cy - dx / 2.0, cy + dx / 2.0
            ymin, ymax = 10**lymin, 10**lymax
        elif dy > dx:
            # expand X range to match Y span (around geometric center)
            cx = (lxmin + lxmax) / 2.0
            lxmin, lxmax = cx - dy / 2.0, cx + dy / 2.0
            xmin, xmax = 10**lxmin, 10**lxmax

        # coverage color scaling with 98th percentile clipping
        coverages = [p["coverage"] for p in points]
        cmin = min(coverages)
        cmax = self._percentile(coverages, 98.0) or max(coverages)
        crng = (cmax - cmin) if isfinite(cmax - cmin) and (cmax - cmin) > 0 else 1.0

        # Inner drawing range to create a visible gap to axes
        inner_x0, inner_x1 = config.axis_gap_px, max(
            config.axis_gap_px, config.plot_w - config.axis_gap_px
        )
        inner_y0, inner_y1 = (
            config.plot_h - config.axis_gap_px,
            config.axis_gap_px,
        )  # inverted

        def sx(v):
            return self._scale_log10(v, xmin, xmax, inner_x0, inner_x1)

        def sy(v):
            return self._scale_log10(v, ymin, ymax, inner_y0, inner_y1)

        for p in points:
            p["sx"] = sx(p["x"])
            p["sy"] = sy(p["y"])  # SVG y grows downward
            # color by coverage (clipped at cmax)
            t_raw = (min(p["coverage"], cmax) - cmin) / crng
            t = max(0.0, min(1.0, t_raw))
            p["color"] = self._cov_to_rgb(t)
            p["r"] = config.marker_size
            p["line_width"] = config.marker_line_width
            p["type"] = f"{p['name']}"
            p["tooltip"] = (
                f"{p['name']} - {region}({side}):\n"
                f" {int(p['x'])} cells:\n"
                f" cell_size: {p['y']:.2f}\n"
                f" coverage: {p['coverage']:.2f}"
            )

        # Reference (anti-diagonal) guide lines under points
        col_counts = [p["col_count"] for p in points if p.get("col_count")]
        if col_counts:
            n_cols_region = max(col_counts)
        else:
            n_cols_region = 10 ** ((log10(xmin * ymin) + log10(xmax * ymax)) / 4)

        # Add guide lines to scatter plot
        multipliers = [0.2, 0.5, 1, 2, 5]

        def guide_width(m):
            if m < 0.5 or m > 2:
                return 0.25
            elif m != 1:
                return 0.4
            else:
                return 0.8

        guide_lines = []
        for m in multipliers:
            k = n_cols_region * m  # x*y = k
            x0_clip = max(xmin, k / ymax)
            x1_clip = min(xmax, k / ymin)
            if x0_clip >= x1_clip:
                continue  # out of view
            y0 = k / x0_clip
            y1 = k / x1_clip
            guide_lines.append(
                {
                    "x1": sx(x0_clip),
                    "y1": sy(y0),
                    "x2": sx(x1_clip),
                    "y2": sy(y1),
                    "w": guide_width(m),
                }
            )

        # Precompute pixel tick positions for Jinja (avoid math inside template)
        def log_pos_x(t):
            return self._scale_log10(t, xmin, xmax, inner_x0, inner_x1)

        def log_pos_y(t):
            return self._scale_log10(t, ymin, ymax, inner_y0, inner_y1)

        xtick_data = [{"t": t, "px": log_pos_x(t)} for t in config.xticks]
        ytick_data = [{"t": t, "py": log_pos_y(t)} for t in config.yticks]

        ctx = self._prepare_template_variables(
            points, guide_lines, config, region, xtick_data, ytick_data, cmin, cmax
        )

        return ctx

    def _prepare_template_variables(
        self, points, guide_lines, config, region, xtick_data, ytick_data, cmin, cmax
    ):
        """Prepare variables for template rendering.
        Args:
            points: Processed scatter points
            guide_lines: Points to draw plot guidelines
            config: Scatter configuration
            region: Optic lobe region for which to generate plot. ME, LO or LOP.
        Returns:
            Dictionary of template variables
        """
        template_vars = {
            "width": config.width,
            "height": config.height,
            "margin_top": config.margin_top,
            "margin_right": config.margin_right,
            "margin_bottom": config.margin_bottom,
            "margin_left": config.margin_left,
            "plot_w": config.plot_w,
            "plot_h": config.plot_h,
            "cmin": cmin,
            "cmax": cmax,
            "points": points,
            "xtick_data": xtick_data,
            "ytick_data": ytick_data,
            "guide_lines": guide_lines,
            "title": region,
            "xlabel": config.xlabel,
            "ylabel": config.ylabel,
            "legend_label": config.legend_label,
            "legend_w": config.legend_w,
        }

        return template_vars

    def _log_ticks(self, vmin, vmax):
        """Ticks for a log10 axis between (vmin, vmax), inclusive."""
        if vmin <= 0 or vmax <= 0 or vmin >= vmax:
            return []
        lo = floor(log10(vmin))
        hi = ceil(log10(vmax))
        return [10**e for e in range(lo, hi + 1)]

    def _scale_log10(self, v, vmin, vmax, a, b):
        """Log10 scaling to pixels."""
        lv = log10(v)
        lmin = log10(vmin)
        lmax = log10(vmax)
        if lmax == lmin:
            return (a + b) / 2.0
        return a + (lv - lmin) * (b - a) / (lmax - lmin)

    def _lerp(self, a, b, t):
        return a + (b - a) * t

    def _cov_to_rgb(self, t):
        """
        Map t in [0,1] to a white→dark red gradient.
        start = white (255,255,255), end = dark red (~180,0,0)
        """
        r0, g0, b0 = 255, 255, 255
        r1, g1, b1 = 180, 0, 0
        r = int(round(self._lerp(r0, r1, t)))
        g = int(round(self._lerp(g0, g1, t)))
        b = int(round(self._lerp(b0, b1, t)))
        return f"rgb({r},{g},{b})"

    def _percentile(self, values, p):
        """
        p in [0, 100]. Returns None on no finite data.
        Uses pandas.Series.quantile with the right keyword for the installed version.
        """
        s = pd.Series(values, dtype="float64").dropna()
        if s.empty:
            return None

        q = p / 100
        # Prefer the 2.x API if available; fall back to 1.5.x
        try:
            return float(s.quantile(q, method="linear"))  # pandas 2.x
        except TypeError:
            return float(s.quantile(q, interpolation="linear"))  # pandas 1.5.x
