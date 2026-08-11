from antares_bot.format_exc import (
    _matcher,
    _short_format,
    format_exception_with_local_vars,
    format_local_value,
)


# ------------------------------------------------------------- _short_format


def test_short_format_hides_application_and_bot(bot_app):
    assert _short_format(bot_app.application) == "<object data hidden>"
    assert _short_format(bot_app.bot) == "<object data hidden>"


def test_short_format_quotes_strings():
    assert _short_format("hi") == '"hi"'


def test_short_format_truncates_long_values():
    out = _short_format("x" * 1000)
    assert out.endswith('...<Too long to show>"')
    assert len(out) <= 256 + 2


def test_short_format_plain_values():
    assert _short_format(5) == "5"
    assert _short_format(None) == "None"


# --------------------------------------------------------- format_local_value


def test_format_local_value_includes_type_and_value():
    assert format_local_value("n", 5) == "n = <int> 5"
    assert format_local_value("s", "x") == 's = <str> "x"'


def test_format_local_value_survives_a_broken_repr():
    class Bad:
        def __str__(self):
            raise RuntimeError

    assert format_local_value("b", Bad()) == "b = <Bad> error to get value"


# -------------------------------------------------------------------- _matcher


def test_matcher_returns_the_indent_of_file_lines():
    assert _matcher('  File "x", line 1') == 2
    assert _matcher('File "x"') == 0
    assert _matcher("  Traceback") == -1


# ------------------------------------------ format_exception_with_local_vars


def _raise_with_locals():
    magic_local = "sentinel-value"
    other = 12345
    raise ValueError("boom " + str(other) + magic_local[:0])


def test_format_exception_with_local_vars_reports_locals():
    try:
        _raise_with_locals()
    except ValueError as e:
        lines = format_exception_with_local_vars(type(e), e, e.__traceback__)
    text = "".join(lines)
    assert "ValueError: boom" in text
    assert "Local variables:" in text
    assert "magic_local" in text
    assert "sentinel-value" in text
    assert "other = <int> 12345" in text


def test_format_exception_with_local_vars_accepts_a_single_argument():
    try:
        _raise_with_locals()
    except ValueError as e:
        lines = format_exception_with_local_vars(e)
    assert any("ValueError" in line for line in lines)


def test_format_exception_with_local_vars_handles_chained_exceptions():
    try:
        try:
            raise KeyError("inner")
        except KeyError as inner:
            raise ValueError("outer") from inner
    except ValueError as e:
        text = "".join(format_exception_with_local_vars(type(e), e, e.__traceback__))
    assert "KeyError" in text
    assert "ValueError" in text
