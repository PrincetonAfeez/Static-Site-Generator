""" Test Template Adapter """

from __future__ import annotations

from ssg.template_adapter import TemplateRenderer


def test_template_escapes_strings_by_default():
    html = TemplateRenderer().render(
        "<p>{{ page.title }}</p>",
        {"page": {"title": '<script>alert("x")</script>'}},
    )

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_template_safe_filter_preserves_html():
    html = TemplateRenderer().render(
        "<div>{{ page.body | safe }}</div>",
        {"page": {"body": "<strong>ok</strong>"}},
    )

    assert html == "<div><strong>ok</strong></div>"


def test_template_if_block_omits_false_branch():
    html = TemplateRenderer().render(
        '{% if page.previous_url %}<a href="{{ page.previous_url }}">Prev</a>{% endif %}',
        {"page": {"previous_url": None}},
    )

    assert html == ""


def test_template_if_block_renders_true_branch():
    html = TemplateRenderer().render(
        '{% if page.previous_url %}<a href="{{ page.previous_url }}">Prev</a>{% endif %}',
        {"page": {"previous_url": "/older/"}},
    )

    assert html == '<a href="/older/">Prev</a>'


def test_template_rejects_nested_if_blocks():
    import pytest

    from ssg.errors import TemplateRenderError

    with pytest.raises(TemplateRenderError, match="nested"):
        TemplateRenderer().render(
            "{% if a %}A{% if b %}B{% endif %}C{% endif %}",
            {"a": True, "b": False},
        )


def test_template_renders_list_values_as_escaped_repr():
    html = TemplateRenderer().render(
        "<p>{{ page.tags }}</p>",
        {"page": {"tags": ["python", "docs"]}},
    )

    assert "python" in html
    assert "docs" in html
    assert html.startswith("<p>[")
    assert html.endswith("]</p>")


def test_template_list_values_are_not_double_escaped():
    html = TemplateRenderer().render(
        "<p>{{ page.tags }}</p>",
        {"page": {"tags": ["a<b"]}},
    )

    assert "&lt;b" in html
    assert "&amp;lt;" not in html


def test_template_if_block_omits_false_boolean():
    html = TemplateRenderer().render(
        "{% if page.generated %}generated{% endif %}",
        {"page": {"generated": False}},
    )

    assert html == ""


def test_template_if_block_omits_zero():
    html = TemplateRenderer().render(
        "{% if page.count %}yes{% endif %}",
        {"page": {"count": 0}},
    )

    assert html == ""
