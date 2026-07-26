"""Horizontal progress-bar glyph drawing and OpenType feature generation."""

from sources.config import FontParams, X_HEIGHT


def _draw_rect(pen, x0, y0, x1, y1):
    """Draw a clockwise outer rectangle for TrueType outlines."""
    pen.moveTo((x0, y0))
    pen.lineTo((x0, y1))
    pen.lineTo((x1, y1))
    pen.lineTo((x1, y0))
    pen.closePath()


def _draw_rect_hole(pen, x0, y0, x1, y1):
    """Draw a counter-clockwise rectangular hole."""
    pen.moveTo((x0, y0))
    pen.lineTo((x1, y0))
    pen.lineTo((x1, y1))
    pen.lineTo((x0, y1))
    pen.closePath()


def draw_progress_glyphs(glyph_data, params=None):
    """Add progress_0 through progress_100 glyphs.

    Width controls the track length and weight controls its height and border.
    Each glyph contains an outlined track and a proportional solid fill.
    """
    if params is None:
        params = FontParams()

    max_value = params.max_value
    track_width = params.bar_width * 2
    track_height = max(params.line_thickness * 2, 2)
    border = max(params.line_thickness // 4, 1)
    border = min(border, (track_width - 2) // 2, (track_height - 2) // 2)
    center_y = X_HEIGHT // 2
    y0 = center_y - track_height // 2
    y1 = y0 + track_height
    inner_x0 = border
    inner_x1 = track_width - border
    inner_y0 = y0 + border
    inner_y1 = y1 - border
    inner_width = inner_x1 - inner_x0
    advance_width = track_width + params.point_width

    for value in range(max_value + 1):
        name = f"progress_{value}"

        def make_draw(progress_value):
            def draw(pen):
                _draw_rect(pen, 0, y0, track_width, y1)
                _draw_rect_hole(pen, inner_x0, inner_y0, inner_x1, inner_y1)

                if progress_value > 0:
                    fill_width = max(
                        round(inner_width * progress_value / max_value),
                        1,
                    )
                    fill_x = inner_x0 + fill_width
                    _draw_rect(pen, inner_x0, inner_y0, fill_x, inner_y1)

            return draw

        glyph_data[name] = (advance_width, make_draw(value))


def generate_progress_feature_code(max_value=100):
    """Generate direct ligatures for horizontal progress-bar syntax."""
    lines = ["lookup progress_liga {"]

    if max_value >= 100:
        lines.append(
            "  sub uni007B uni0068 uni003A uni0031 uni0030 uni0030 uni007D "
            "by progress_100;"
        )

    for tens in range(1, 10):
        for ones in range(10):
            value = tens * 10 + ones
            if value > min(max_value, 99):
                break
            lines.append(
                f"  sub uni007B uni0068 uni003A uni003{tens} uni003{ones} "
                f"uni007D by progress_{value};"
            )

    for value in range(min(max_value, 9) + 1):
        lines.append(
            f"  sub uni007B uni0068 uni003A uni003{value} uni007D "
            f"by progress_{value};"
        )

    lines.extend(["} progress_liga;", ""])
    return "\n".join(lines)
