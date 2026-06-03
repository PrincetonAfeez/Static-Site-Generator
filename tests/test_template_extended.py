""" Test Template Extended """

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ssg.template_adapter import (
    TemplateRenderer,
    _is_truthy,
    format_template_value,
    resolve_expression,
)


def test_resolve_expression_empty_part():
    assert resolve_expression("page..title", {"page": {"title": "X"}}) is None


def test_resolve_expression_attribute_access():
    obj = SimpleNamespace(name="site")
    assert resolve_expression("site.name", {"site": obj}) == "site"


def test_resolve_expression_missing_key():
    assert resolve_expression("page.missing", {"page": {}}) is None


def test_format_template_value_safe_list():
    assert format_template_value(["a"], use_safe=True) == "['a']"


def test_format_template_value_dict_repr():
    assert format_template_value({"k": 1}) == "{'k': 1}"


def test_template_renders_none_as_empty():
    html = TemplateRenderer().render("{{ page.missing }}", {"page": {}})

    assert html == ""


def test_template_non_safe_filter_not_treated_as_safe():
    html = TemplateRenderer().render("{{ page.body | escape }}", {"page": {"body": "<b>"}})

    assert "&lt;b&gt;" in html


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, False),
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        ("", False),
        ("x", True),
        ([], False),
        ([1], True),
        ({}, False),
        ({"a": 1}, True),
        (object(), True),
    ],
)
def test_is_truthy_values(value, expected):
    assert _is_truthy(value) is expected


def test_template_if_truthy_nonstandard_type():
    html = TemplateRenderer().render(
        "{% if page.flag %}yes{% endif %}",
        {"page": {"flag": object()}},
    )

    assert html == "yes"
