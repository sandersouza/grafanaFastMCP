"""Tests for schema generation and normalization in the FastMCP shim.

Focus on edge cases: arrays without items, anyOf normalization, required cleanup,
and mapping/sequence annotations.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence, Union

from mcp.server.fastmcp import FastMCP


def _build_tool(app: FastMCP):
    @app.tool(name="sample", title="Sample", description="Schema cases")
    async def sample_tool(
        a_str: str,
        a_int: int,
        a_num: float,
        a_bool: bool,
        a_list_any: list,  # no items annotation
        a_list_str: list[str],
        a_seq_union: Sequence[Union[str, int]],
        a_map_any: dict,
        a_mapping: Mapping[str, int],
        a_optional: Optional[int],
        *,
        kw_no_annot=None,  # keyword-only without annotation
        **kwargs: Any,
    ) -> Dict[str, Any]:
        # reference all args so static analyzers don't flag them as unused
        _ = (
            a_str,
            a_int,
            a_num,
            a_bool,
            a_list_any,
            a_list_str,
            a_seq_union,
            a_map_any,
            a_mapping,
            a_optional,
            kw_no_annot,
            kwargs,
        )
        return {"ok": True}

    return sample_tool


def test_schema_build_and_normalize_covers_edge_cases() -> None:
    app = FastMCP()
    _build_tool(app)
    # Obtain normalized schema via the public discovery API
    import asyncio
    tools = asyncio.run(app.list_tools())
    assert tools and tools[0].parameters["type"] == "object"
    norm = tools[0].parameters

    assert norm["type"] == "object"
    props = norm["properties"]
    # Required should include all non-default, non-variadic parameters
    # (excluding ctx)
    assert set(
        norm["required"]) >= {
        "a_str",
        "a_int",
        "a_num",
        "a_bool",
        "a_list_any",
        "a_list_str",
        "a_seq_union",
        "a_map_any",
        "a_mapping",
        "a_optional"}

    # Arrays always have an items schema (fallback if missing)
    assert props["a_list_any"]["type"] == "array"
    assert "items" in props["a_list_any"] and props["a_list_any"]["items"]
    assert props["a_list_str"]["items"]["type"] == "string"

    # anyOf from union is preserved and normalized
    anyof = props["a_seq_union"]["items"].get("anyOf", [])
    assert {opt.get("type") for opt in anyof} >= {"string", "integer"}

    # Objects are normalized
    assert props["a_map_any"]["type"] == "object"
    assert props["a_mapping"]["type"] == "object"

    # Optional collapses to inner schema in this shim
    # (Optional[int] -> {"type": "integer"})
    assert props["a_optional"]["type"] == "integer"
