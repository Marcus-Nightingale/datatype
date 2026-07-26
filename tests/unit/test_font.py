"""Structural checks for the checked-in variable font."""

from pathlib import Path

import pytest
import uharfbuzz as hb
from fontTools.ttLib import TTFont

from sources.config import FONT_VERSION


FONT_PATH = (
    Path(__file__).resolve().parents[2]
    / "fonts"
    / "variable"
    / "Datatype[wdth,wght].ttf"
)
VARIABLE_WOFF2_PATH = FONT_PATH.with_suffix(".woff2")
DOCS_FONT_PATH = Path(__file__).resolve().parents[2] / "docs" / "Datatype.woff2"


@pytest.fixture(scope="module")
def font():
    loaded_font = TTFont(FONT_PATH, lazy=True)
    yield loaded_font
    loaded_font.close()


def test_variable_font_has_required_tables(font):
    required_tables = {
        "cmap",
        "fvar",
        "gvar",
        "GSUB",
        "HVAR",
        "name",
        "OS/2",
        "STAT",
    }

    assert required_tables <= set(font.keys())


def test_variable_axes_match_public_contract(font):
    axes = {
        axis.axisTag: (axis.minValue, axis.defaultValue, axis.maxValue)
        for axis in font["fvar"].axes
    }

    assert axes == {
        "wdth": (50.0, 100.0, 150.0),
        "wght": (100.0, 400.0, 900.0),
    }
    assert len(font["fvar"].instances) == 9


def test_font_version_and_latin_core_coverage(font):
    assert font["head"].fontRevision == pytest.approx(float(FONT_VERSION), abs=0.001)
    assert len(font.getBestCmap()) == 319
    assert font["maxp"].numGlyphs == 11_097


def test_mixed_width_metadata_is_not_monospaced(font):
    assert font["post"].isFixedPitch == 0
    assert font["OS/2"].panose.bProportion != 9


def test_docs_font_matches_built_variable_font():
    assert DOCS_FONT_PATH.read_bytes() == VARIABLE_WOFF2_PATH.read_bytes()


def test_signed_sparkline_values_resolve_to_connected_segments(font):
    face = hb.Face(FONT_PATH.read_bytes())
    hb_font = hb.Font(face)
    buffer = hb.Buffer()
    buffer.add_str("{l:-100,0,100}")
    buffer.guess_segment_properties()

    hb.shape(hb_font, buffer, {"calt": True, "liga": True})
    glyph_names = [
        font.getGlyphName(info.codepoint)
        for info in buffer.glyph_infos
    ]

    assert glyph_names == [
        "spark_signed_start",
        "spark_0_to_50",
        "spark_signed_sep",
        "spark_50_to_100",
        "spark_signed_sep",
        "spark_p100",
        "spark_end",
    ]
