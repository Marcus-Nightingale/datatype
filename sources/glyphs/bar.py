"""Bar chart glyph drawing and OpenType feature generation."""

from sources.config import (
    CHART_HEIGHT, CHART_BASELINE, MAX_BAR_DATA_POINTS,
    FontParams,
)


def _draw_rect(pen, x0, y0, x1, y1):
    """Draw a clockwise outer rectangle for TrueType outlines."""
    pen.moveTo((x0, y0))
    pen.lineTo((x0, y1))
    pen.lineTo((x1, y1))
    pen.lineTo((x1, y0))
    pen.closePath()


def draw_bar_glyphs(glyph_data, params=None):
    """Add bar chart glyphs to glyph_data dict.

    Glyphs created:
    - bar_start: zero-width marker
    - bar_end: zero-width marker (adds right padding)
    - bar_sep: small gap between bars
    - bar_d0..bar_d9: intermediate digit glyphs (zero-width, never rendered)
    - bar_h0..bar_h{max_value}: individual bars at proportional heights
    - bar_signed_p0..bar_signed_p{max_value}: positive bars on a signed scale
    - bar_signed_n1..bar_signed_n{max_value}: negative bars on a signed scale
    """
    if params is None:
        params = FontParams()

    bar_width = params.bar_width
    bar_fill = params.bar_fill
    sep_width = params.sep_width
    end_width = params.end_width
    max_value = params.max_value
    drawn_w = max(round(bar_width * bar_fill), 1)
    x_offset = 0  # Left-align bars instead of centering

    # bar_start - zero width trigger glyph
    glyph_data["bar_start"] = (0, None)

    # bar_end - small padding to close the chart
    glyph_data["bar_end"] = (end_width, None)

    # bar_sep - small spacer between bars
    glyph_data["bar_sep"] = (sep_width, None)

    # Intermediate digit glyphs (zero-width, never rendered)
    for d in range(10):
        glyph_data[f"bar_d{d}"] = (0, None)

    # Signed-chart parsing helpers
    glyph_data["bar_signed_start"] = (0, None)
    glyph_data["bar_signed_sep"] = (sep_width, None)
    glyph_data["bar_negative"] = (0, None)
    for d in range(10):
        glyph_data[f"bar_sd{d}"] = (0, None)
        glyph_data[f"bar_nd{d}"] = (0, None)

    # bar_h0 - empty bar (has width but no drawing)
    glyph_data["bar_h0"] = (bar_width, None)

    # bar_h1 through bar_h{max_value}
    for h in range(1, max_value + 1):
        name = f"bar_h{h}"
        height = int(CHART_HEIGHT * h / max_value)

        def make_draw(xo, dw, ht):
            def draw(pen):
                _draw_rect(pen, xo, CHART_BASELINE, xo + dw, CHART_BASELINE + ht)
            return draw

        glyph_data[name] = (bar_width, make_draw(x_offset, drawn_w, height))

    # Signed bars share a centred zero baseline. Positive-only expressions keep
    # using bar_h* above, preserving their existing full-height rendering.
    signed_half_height = CHART_HEIGHT // 2
    zero_y = CHART_BASELINE + signed_half_height
    glyph_data["bar_signed_p0"] = (bar_width, None)

    for value in range(1, max_value + 1):
        height = round(signed_half_height * value / max_value)

        def make_positive_draw(xo, dw, zy, ht):
            def draw(pen):
                _draw_rect(pen, xo, zy, xo + dw, zy + ht)
            return draw

        def make_negative_draw(xo, dw, zy, ht):
            def draw(pen):
                _draw_rect(pen, xo, zy - ht, xo + dw, zy)
            return draw

        glyph_data[f"bar_signed_p{value}"] = (
            bar_width,
            make_positive_draw(x_offset, drawn_w, zero_y, height),
        )
        glyph_data[f"bar_signed_n{value}"] = (
            bar_width,
            make_negative_draw(x_offset, drawn_w, zero_y, height),
        )


def generate_bar_feature_code(max_value=100):
    """Generate OpenType feature code for bar chart substitution.

    Uses intermediate digits + combine strategy:
    1. Ligature: {b: → bar_start
    2. Detect whether a minus sign switches the expression to a signed scale
    3. Propagation: digits and punctuation → intermediate chart glyphs
    4. Combine intermediates into unsigned or signed bar glyphs
    5. Close: } → bar_end

    Returns:
        feature code string
    """
    lines = []

    # --- Glyph classes ---
    bar_prop_ctx = ["bar_start", "bar_sep"] + [f"bar_d{i}" for i in range(10)]
    lines.append(f"@bar_prop_ctx = [{' '.join(bar_prop_ctx)}];")

    bar_signed_prop_ctx = (
        ["bar_signed_start", "bar_signed_sep"]
        + [f"bar_sd{i}" for i in range(10)]
    )
    lines.append(f"@bar_signed_prop_ctx = [{' '.join(bar_signed_prop_ctx)}];")

    bar_negative_prop_ctx = ["bar_negative"] + [f"bar_nd{i}" for i in range(10)]
    lines.append(f"@bar_negative_prop_ctx = [{' '.join(bar_negative_prop_ctx)}];")

    bar_close_ctx = (
        ["bar_start", "bar_sep", "bar_signed_start", "bar_signed_sep"]
        + [f"bar_h{i}" for i in range(max_value + 1)]
        + [f"bar_signed_p{i}" for i in range(max_value + 1)]
        + [f"bar_signed_n{i}" for i in range(1, max_value + 1)]
    )
    lines.append(f"@bar_close_ctx = [{' '.join(bar_close_ctx)}];")

    bar_digits = [f"uni003{d}" for d in range(10)]
    lines.append(f"@bar_digits = [{' '.join(bar_digits)}];")
    lines.append(f"@bar_signed_scan = [{' '.join(bar_digits)} uni002C];")
    lines.append("")

    # --- Lookup: opening ligature {b: → bar_start ---
    lines.append("lookup bar_open {")
    lines.append("  sub uni007B uni0062 uni003A by bar_start;")
    lines.append("} bar_open;")
    lines.append("")

    # --- Detect a minus anywhere in the expression ---
    # The longest valid prefix is twenty three-digit values plus separators.
    lines.append("lookup bar_detect_signed {")
    for distance in range(MAX_BAR_DATA_POINTS * 4 + 1):
        scan = " ".join(["@bar_signed_scan"] * distance)
        lookahead = f" {scan}" if scan else ""
        lines.append(
            f"  sub bar_start'{lookahead} uni002D by bar_signed_start;"
        )
    lines.append("} bar_detect_signed;")
    lines.append("")

    # --- Lookup: digit → intermediate ---
    lines.append("lookup bar_to_intermediate {")
    for d in range(10):
        lines.append(f"  sub uni003{d} by bar_d{d};")
    lines.append("} bar_to_intermediate;")
    lines.append("")

    # --- Lookup: comma → bar_sep ---
    lines.append("lookup bar_comma {")
    lines.append("  sub uni002C by bar_sep;")
    lines.append("} bar_comma;")
    lines.append("")

    # --- Signed digit, sign, and comma substitutions ---
    lines.append("lookup bar_to_signed_intermediate {")
    for d in range(10):
        lines.append(f"  sub uni003{d} by bar_sd{d};")
    lines.append("} bar_to_signed_intermediate;")
    lines.append("")

    lines.append("lookup bar_to_negative_intermediate {")
    for d in range(10):
        lines.append(f"  sub uni003{d} by bar_nd{d};")
    lines.append("} bar_to_negative_intermediate;")
    lines.append("")

    lines.append("lookup bar_minus {")
    lines.append("  sub uni002D by bar_negative;")
    lines.append("} bar_minus;")
    lines.append("")

    lines.append("lookup bar_signed_comma {")
    lines.append("  sub uni002C by bar_signed_sep;")
    lines.append("} bar_signed_comma;")
    lines.append("")

    # --- Lookup: propagation (calt chain) ---
    lines.append("lookup bar_propagate {")
    lines.append("  sub @bar_prop_ctx @bar_digits' lookup bar_to_intermediate;")
    lines.append("  sub @bar_prop_ctx uni002C' lookup bar_comma;")
    lines.append("} bar_propagate;")
    lines.append("")

    lines.append("lookup bar_signed_propagate {")
    lines.append(
        "  sub @bar_signed_prop_ctx @bar_digits' "
        "lookup bar_to_signed_intermediate;"
    )
    lines.append(
        "  sub @bar_signed_prop_ctx uni002D' lookup bar_minus;"
    )
    lines.append(
        "  sub @bar_signed_prop_ctx uni002C' lookup bar_signed_comma;"
    )
    lines.append(
        "  sub @bar_negative_prop_ctx @bar_digits' "
        "lookup bar_to_negative_intermediate;"
    )
    lines.append(
        "  sub @bar_negative_prop_ctx uni002C' lookup bar_signed_comma;"
    )
    lines.append("} bar_signed_propagate;")
    lines.append("")

    # --- Lookup: combine ligature (multi-digit → value) ---
    lines.append("lookup bar_combine_liga {")
    if max_value >= 100:
        lines.append("  sub bar_d1 bar_d0 bar_d0 by bar_h100;")
    for tens in range(1, 10):
        for ones in range(0, 10):
            val = tens * 10 + ones
            if val > max_value:
                break
            lines.append(f"  sub bar_d{tens} bar_d{ones} by bar_h{val};")
    lines.append("} bar_combine_liga;")
    lines.append("")

    # --- Lookup: combine single (lone intermediate → value) ---
    lines.append("lookup bar_combine_single {")
    for d in range(min(10, max_value + 1)):
        lines.append(f"  sub bar_d{d} by bar_h{d};")
    lines.append("} bar_combine_single;")
    lines.append("")

    # --- Combine signed values ---
    lines.append("lookup bar_signed_combine_liga {")
    if max_value >= 100:
        lines.append(
            "  sub bar_sd1 bar_sd0 bar_sd0 by bar_signed_p100;"
        )
        lines.append(
            "  sub bar_negative bar_nd1 bar_nd0 bar_nd0 "
            "by bar_signed_n100;"
        )
    for tens in range(1, 10):
        for ones in range(10):
            value = tens * 10 + ones
            if value > max_value:
                break
            lines.append(
                f"  sub bar_sd{tens} bar_sd{ones} by bar_signed_p{value};"
            )
            lines.append(
                f"  sub bar_negative bar_nd{tens} bar_nd{ones} "
                f"by bar_signed_n{value};"
            )
    lines.append("} bar_signed_combine_liga;")
    lines.append("")

    lines.append("lookup bar_signed_combine_single {")
    for value in range(min(10, max_value + 1)):
        lines.append(f"  sub bar_sd{value} by bar_signed_p{value};")
        negative_result = (
            "bar_signed_p0" if value == 0 else f"bar_signed_n{value}"
        )
        lines.append(
            f"  sub bar_negative bar_nd{value} by {negative_result};"
        )
    lines.append("} bar_signed_combine_single;")
    lines.append("")

    # --- Lookup: close substitution ---
    lines.append("lookup bar_close_sub {")
    lines.append("  sub uni007D by bar_end;")
    lines.append("} bar_close_sub;")
    lines.append("")

    # --- Lookup: close (calt chain) ---
    lines.append("lookup bar_close {")
    lines.append("  sub @bar_close_ctx uni007D' lookup bar_close_sub;")
    lines.append("} bar_close;")
    lines.append("")

    return "\n".join(lines)
