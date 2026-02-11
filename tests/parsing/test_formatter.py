from src.telegram.formatter import TELEGRAM_MAX_LENGTH, format_telegram, split_message


class TestFormatTelegram:
    def test_escapes_special_chars(self):
        result = format_telegram("Hello! How are you?")
        assert "\\!" in result

    def test_preserves_code_blocks(self):
        text = "Here is code:\n```python\nprint('hello')\n```"
        result = format_telegram(text)
        assert "```python" in result
        assert "print('hello')" in result

    def test_preserves_inline_code(self):
        text = "Use the `print()` function"
        result = format_telegram(text)
        assert "`print()`" in result

    def test_converts_bold(self):
        text = "This is **bold** text"
        result = format_telegram(text)
        assert "*bold*" in result

    def test_converts_italic(self):
        text = "This is *italic* text"
        result = format_telegram(text)
        assert "_italic_" in result

    def test_empty_string(self):
        assert format_telegram("") == ""

    def test_plain_text_with_dots(self):
        result = format_telegram("version 1.2.3 is out")
        assert "\\." in result


class TestSplitMessage:
    def test_short_message_unchanged(self):
        result = split_message("Hello world")
        assert result == ["Hello world"]

    def test_splits_at_paragraph_boundary(self):
        text = "A" * 3000 + "\n\n" + "B" * 3000
        result = split_message(text)
        assert len(result) == 2
        assert result[0].strip().endswith("A" * 3000)
        assert result[1].strip().startswith("B" * 3000)

    def test_splits_long_message(self):
        text = "A" * 5000
        result = split_message(text)
        assert len(result) >= 2
        assert all(len(chunk) <= TELEGRAM_MAX_LENGTH for chunk in result)

    def test_preserves_code_blocks(self):
        text = "before\n```python\n" + "x = 1\n" * 500 + "```\nafter"
        result = split_message(text)
        for chunk in result:
            if "```python" in chunk:
                assert "```" in chunk[chunk.index("```python") + 10 :]

    def test_empty_string(self):
        assert split_message("") == [""]

    def test_exactly_max_length(self):
        text = "A" * TELEGRAM_MAX_LENGTH
        result = split_message(text)
        assert len(result) == 1
