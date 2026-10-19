import pytest
from telegram import MessageEntity
from telegram.constants import MessageEntityType

from antares_bot.text_process import (
    TEXT_LENGTH_LIMIT,
    MarkdownParser,
    TextObject,
    find_special_sequences,
    force_longtext_split,
    longtext_markdown_split,
    longtext_split,
    trim_spaces_before_line,
)


# --------------------------------------------------------- find_special_sequences


def test_find_special_sequences_needs_eight_chars():
    # 7 special chars: below COUNT_LIMIT
    assert find_special_sequences("a" + "@" * 7 + "b") == []
    assert find_special_sequences("a" + "@" * 8 + "b") == [(1, 9)]


def test_find_special_sequences_excluded_chars_do_not_trigger():
    # every char here is "special" but none is a *true* special char, so no
    # index ever starts a scan
    for text in ("`" * 12, "*" * 12, "-" * 12, "." * 12, " " * 12, "，" * 12):
        assert find_special_sequences(text) == []


def test_find_special_sequences_excluded_chars_still_extend_a_run():
    # '-' never starts a scan, but once '@' triggers one the surrounding '-'
    # count towards the run length
    assert find_special_sequences("----@---") == [(0, 8)]
    # 7 chars total: one short of COUNT_LIMIT
    assert find_special_sequences("---@---") == []


def test_find_special_sequences_rejects_consecutive_spaces():
    # single spaces are tolerated inside a run...
    assert find_special_sequences("@ @ @ @ @") == [(0, 9)]
    # ...two in a row void the whole candidate
    assert find_special_sequences("@ @ @  @ @") == []


def test_find_special_sequences_alphanumeric_breaks_the_run():
    assert find_special_sequences("@@@@a@@@@") == []


def test_find_special_sequences_multiple_non_overlapping():
    text = "@" * 8 + "word" + "@" * 8
    assert find_special_sequences(text) == [(0, 8), (12, 20)]


def test_find_special_sequences_cjk_breaks_the_run():
    assert find_special_sequences("@@@@中@@@@") == []


# ------------------------------------------------------- trim_spaces_before_line


def test_trim_spaces_before_line_strips_common_indent():
    assert trim_spaces_before_line("    a\n    b") == "a\nb"
    assert trim_spaces_before_line("    a\n      b") == "a\n  b"


def test_trim_spaces_before_line_noop_when_a_line_has_no_indent():
    code = "a\n    b"
    assert trim_spaces_before_line(code) is code


def test_trim_spaces_before_line_ignores_blank_lines_and_flattens_them():
    assert trim_spaces_before_line("  a\n\n  b") == "a\n\nb"
    assert trim_spaces_before_line("  a\n   \n  b") == "a\n\nb"


def test_trim_spaces_before_line_all_blank_is_unchanged():
    code = "   \n  "
    assert trim_spaces_before_line(code) is code


# --------------------------------------------------------------- longtext_split


def test_longtext_split_short_text_is_returned_whole():
    assert longtext_split("hello") == ["hello"]


def test_longtext_split_is_lossless():
    text = "\n".join("line %d" % i for i in range(2000))
    assert len(text) >= TEXT_LENGTH_LIMIT
    parts = longtext_split(text)
    assert len(parts) > 1
    assert "\n".join(parts) == text


@pytest.mark.parametrize(
    "lines,line_len",
    [
        (2000, 6),
        (4000, 1),  # worst case: separators outweigh the content
        (500, 50),
        (100, 500),
    ],
)
def test_longtext_split_every_part_is_within_limit(lines, line_len):
    text = "\n".join("x" * line_len for _ in range(lines))
    parts = longtext_split(text)
    assert all(len(p) <= TEXT_LENGTH_LIMIT for p in parts)
    assert "\n".join(parts) == text


def test_longtext_split_stays_under_the_telegram_cap():
    """TEXT_LENGTH_LIMIT is 4000; Telegram itself rejects anything over 4096."""
    text = "\n".join("x" for _ in range(4000))
    assert max(len(p) for p in longtext_split(text)) <= 4096


def test_longtext_split_hard_splits_a_single_huge_line():
    text = "x" * 10000
    parts = longtext_split(text)
    assert len(parts) > 1
    assert parts[0] == "x" * 1000
    assert "".join(parts) == text


def test_longtext_split_keeps_a_code_block_intact():
    block = "```\n" + "\n".join("c%d" % i for i in range(100)) + "\n```"
    text = "\n".join("line %d" % i for i in range(1000)) + "\n" + block
    parts = longtext_split(text)
    assert any(p.startswith("```") and p.endswith("```") for p in parts)


def test_longtext_split_force_splits_when_everything_is_one_code_block():
    lines = ["```"] + ["c%d" % i for i in range(2000)] + ["```"]
    parts = longtext_split("\n".join(lines))
    assert len(parts) > 1
    # the fence could not be preserved, so the first part still starts with it
    assert parts[0].startswith("```")


def test_force_longtext_split_joins_lines_back():
    lines = ["line %d" % i for i in range(2000)]
    parts = force_longtext_split(list(lines))
    assert "\n".join(parts) == "\n".join(lines)


# ------------------------------------------------------------- MarkdownParser


def test_get_code_lang_extracts_supported_language():
    assert MarkdownParser.get_code_lang("python\nprint(1)") == ("print(1)", "python")


def test_get_code_lang_is_case_insensitive():
    assert MarkdownParser.get_code_lang("Python\nx") == ("x", "Python")


def test_get_code_lang_unknown_first_line_is_part_of_the_code():
    assert MarkdownParser.get_code_lang("notalang\nx") == ("notalang\nx", None)
    assert MarkdownParser.get_code_lang("print(1)") == ("print(1)", None)


@pytest.mark.parametrize(
    "splitted,expected",
    [
        (["a", "b"], ["a", "b"]),
        # odd number of trailing backslashes: the separator was escaped -> merge
        (["a\\", "b"], ["a\\b"]),
        # even number: a real separator -> keep the split
        (["a\\\\", "b"], ["a\\\\", "b"]),
        (["a\\\\\\", "b"], ["a\\\\\\b"]),
        (["a\\"], ["a\\"]),
    ],
)
def test_join_escaped(splitted, expected):
    assert MarkdownParser.join_escaped(splitted) == expected


def test_split_2_parts_prefers_a_newline_boundary():
    long_text = "a" * (TEXT_LENGTH_LIMIT - 10) + "\n" + "b" * 100
    first, second = MarkdownParser.split_2_parts(long_text)
    assert first == "a" * (TEXT_LENGTH_LIMIT - 10)
    assert second == "b" * 100


def test_split_2_parts_hard_cuts_without_a_newline():
    long_text = "a" * (TEXT_LENGTH_LIMIT + 50)
    first, second = MarkdownParser.split_2_parts(long_text)
    assert len(first) == TEXT_LENGTH_LIMIT
    assert len(second) == 50


def test_force_split_up_text_object_keeps_entity_and_language():
    obj = TextObject(
        text="x" * (TEXT_LENGTH_LIMIT * 2 + 5),
        entity_type=MessageEntityType.PRE,
        code_language="python",
    )
    parts = MarkdownParser.force_split_up_text_object(obj)
    assert len(parts) > 1
    assert all(p.entity_type == MessageEntityType.PRE for p in parts)
    assert all(p.code_language == "python" for p in parts)
    assert all(len(p.text) <= TEXT_LENGTH_LIMIT for p in parts)


def test_force_split_up_text_object_short_input_is_untouched():
    obj = TextObject(text="short", entity_type=None)
    assert MarkdownParser.force_split_up_text_object(obj) == [obj]


def test_split_special_partitions_around_sequences():
    text = "start" + "@" * 8 + "end"
    assert MarkdownParser.split_special(text) == ["start", "@" * 8, "end"]


# ------------------------------------------------------ longtext_markdown_split


def _entity_texts(text: str, entities: list[MessageEntity]) -> list[tuple[str, str]]:
    # entity offsets are utf-16 based; re-encode to slice correctly
    utf16 = text.encode("utf-16-le")
    out = []
    for e in entities:
        chunk = utf16[e.offset * 2 : (e.offset + e.length) * 2]
        out.append((e.type, chunk.decode("utf-16-le")))
    return out


def test_markdown_split_bold_italic_and_code():
    texts, entities = longtext_markdown_split("a **b** c *d* e `f` g")
    assert texts == ["a b c d e f g"]
    # entities come out in text order, regardless of the split precedence
    assert _entity_texts(texts[0], entities[0]) == [
        (MessageEntityType.BOLD, "b"),
        (MessageEntityType.ITALIC, "d"),
        (MessageEntityType.CODE, "f"),
    ]


def test_markdown_split_code_block_with_language():
    texts, entities = longtext_markdown_split("intro\n```python\nprint(1)\n```\ntail")
    joined = "".join(texts)
    assert "print(1)" in joined
    pre = [e for group in entities for e in group if e.type == MessageEntityType.PRE]
    assert len(pre) == 1
    assert pre[0].language == "python"


def test_markdown_split_code_block_keeps_relative_indent():
    # `feed()` strips the block before dedenting, so the first line never has
    # leading spaces and `trim_spaces_before_line` finds a common indent of 0.
    # The relative indentation of the remaining lines is therefore preserved.
    texts, _ = longtext_markdown_split("```\n    a\n    b\n```")
    assert texts[0] == "a\n    b"


def test_markdown_split_code_block_body_is_stripped():
    texts, _ = longtext_markdown_split("```\n\n  code here  \n\n```")
    assert texts[0] == "code here"


def test_markdown_split_unclosed_marker_degrades_to_plain_text():
    texts, entities = longtext_markdown_split("a **b c")
    assert texts == ["a **b c"]
    assert entities == [[]]


def test_markdown_split_unclosed_code_fence_is_not_a_block():
    texts, entities = longtext_markdown_split("a\n```\nb")
    assert "```" in "".join(texts)
    assert all(e.type != MessageEntityType.PRE for group in entities for e in group)


def test_markdown_split_utf16_offsets():
    texts, entities = longtext_markdown_split("😀中 **bold**")
    text = texts[0]
    ((etype, matched),) = _entity_texts(text, entities[0])
    assert etype == MessageEntityType.BOLD
    assert matched == "bold"
    # "😀中 " is 3 codepoints but 4 utf-16 units (the emoji is a surrogate pair)
    assert text.index("bold") == 3
    assert entities[0][0].offset == 4


def test_markdown_split_long_input_produces_multiple_messages():
    text = "\n".join("**b%d** line" % i for i in range(1000))
    texts, entities = longtext_markdown_split(text)
    assert len(texts) > 1
    assert len(texts) == len(entities)
    for t, group in zip(texts, entities):
        assert len(t) <= TEXT_LENGTH_LIMIT
        for e in group:
            assert e.offset + e.length <= len(t.encode("utf-16-le")) // 2


def test_markdown_split_empty_input():
    assert longtext_markdown_split("") == ([], [])


@pytest.mark.parametrize(
    "source,label,url",
    [
        ("[说明](https://example.com)", "说明", "https://example.com"),
        (
            "[说明](https://example.com/a_(b)?a=x_y&b=2#part)",
            "说明",
            "https://example.com/a_(b)?a=x_y&b=2#part",
        ),
        (r"[a\[b\]](https://example.com/a\(b\))", "a[b]", "https://example.com/a(b)"),
        (
            "[**说明** `code`](https://example.com)",
            "**说明** `code`",
            "https://example.com",
        ),
        (
            "[a [b]](tg://resolve?domain=example)",
            "a [b]",
            "tg://resolve?domain=example",
        ),
    ],
)
def test_markdown_plain_text_link(source, label, url):
    texts, groups = longtext_markdown_split(source)
    assert texts == [label]
    assert groups == [
        [MessageEntity(MessageEntityType.TEXT_LINK, 0, len(label), url=url)]
    ]


def test_markdown_links_with_surrounding_formatting_and_emoji():
    texts, groups = longtext_markdown_split(
        "😀 **粗体** [中😀](https://example.com/1)[二](https://example.com/2) *斜体*"
    )
    assert texts == ["😀 粗体 中😀二 斜体"]
    assert _entity_texts(texts[0], groups[0]) == [
        (MessageEntityType.BOLD, "粗体"),
        (MessageEntityType.TEXT_LINK, "中😀"),
        (MessageEntityType.TEXT_LINK, "二"),
        (MessageEntityType.ITALIC, "斜体"),
    ]
    links = [e for e in groups[0] if e.type == MessageEntityType.TEXT_LINK]
    assert [(e.offset, e.length, e.url) for e in links] == [
        (6, 3, "https://example.com/1"),
        (9, 1, "https://example.com/2"),
    ]


@pytest.mark.parametrize(
    "source",
    [
        "[text](https://example.com",
        "[text]",
        "[](https://example.com)",
        "[text]()",
        "![text](https://example.com)",
        r"\[text](https://example.com)",
        '[text](https://example.com "title")',
        "[text\nmore](https://example.com)",
        "[text](https://example.com\n/path)",
        "[text][reference]",
    ],
)
def test_markdown_unsupported_link_is_literal(source):
    texts, groups = longtext_markdown_split(source)
    assert texts == [source]
    assert groups == [[]]


@pytest.mark.parametrize("wrapper", ["`{}`", "```\n{}\n```"])
def test_markdown_link_in_code_is_literal(wrapper):
    source = "[text](https://example.com)"
    texts, groups = longtext_markdown_split(wrapper.format(source))
    assert texts == [source]
    assert _entity_texts(texts[0], groups[0]) == [
        (MessageEntityType.CODE if wrapper == "`{}`" else MessageEntityType.PRE, source)
    ]


def test_markdown_code_then_link_and_literal_backticks_in_label():
    texts, groups = longtext_markdown_split(
        "`[code](https://example.com)` [a `b`](https://example.com/link)"
    )
    assert texts == ["[code](https://example.com) a `b`"]
    assert _entity_texts(texts[0], groups[0]) == [
        (MessageEntityType.CODE, "[code](https://example.com)"),
        (MessageEntityType.TEXT_LINK, "a `b`"),
    ]
    assert groups[0][1].url == "https://example.com/link"


@pytest.mark.parametrize("length", [3999, 4000, 4001, 8005])
@pytest.mark.parametrize("prefix", ["", "prefix " * 570])
def test_markdown_long_link_keeps_url_across_chunks(length, prefix):
    label = "x" * length
    url = "https://example.com"
    texts, groups = longtext_markdown_split(prefix + f"[{label}]({url})")
    assert "".join(texts) == prefix + label
    assert len(texts) == len(groups)
    linked_text = []
    for text, entities in zip(texts, groups):
        assert len(text) <= TEXT_LENGTH_LIMIT
        for entity in entities:
            assert entity.type == MessageEntityType.TEXT_LINK
            assert entity.url == url
            assert 0 <= entity.offset < entity.offset + entity.length <= len(text)
        linked_text.extend(value for _, value in _entity_texts(text, entities))
    assert "".join(linked_text) == label


def test_markdown_long_link_label_preserves_spaces():
    label = " " + "word " * 1700
    url = "https://example.com"
    texts, groups = longtext_markdown_split(f"[{label}]({url})")
    assert "".join(texts) == label
    assert all(e.url == url for group in groups for e in group)


def test_markdown_escaped_backtick_does_not_end_code_before_link_syntax():
    source = r"`a\` [text](https://example.com)`"
    texts, groups = longtext_markdown_split(source)
    assert all(e.type != MessageEntityType.TEXT_LINK for group in groups for e in group)
    assert "[text](https://example.com)" in texts[0]
