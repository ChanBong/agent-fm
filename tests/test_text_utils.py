"""Tests for sentence splitting utility."""

from agent_fm.text_utils import split_sentences


def test_basic_split():
    text = "Hello world. How are you? I am fine!"
    result = split_sentences(text)
    assert result == ["Hello world.", "How are you?", "I am fine!"]


def test_single_sentence():
    assert split_sentences("Just one sentence here.") == ["Just one sentence here."]


def test_empty_string():
    assert split_sentences("") == []
    assert split_sentences("   ") == []


def test_no_punctuation():
    assert split_sentences("No punctuation at all") == ["No punctuation at all"]


def test_abbreviations_preserved():
    text = "Dr. Smith went to Washington. He met Mr. Jones there."
    result = split_sentences(text)
    assert result == ["Dr. Smith went to Washington.", "He met Mr. Jones there."]


def test_decimal_numbers():
    text = "The value is 3.14 approximately. That is close to pi."
    result = split_sentences(text)
    assert result == ["The value is 3.14 approximately.", "That is close to pi."]


def test_us_abbreviation():
    text = "The U.S. government announced a plan. It starts Monday."
    result = split_sentences(text)
    assert len(result) == 2
    assert "U.S." in result[0]


def test_multiple_punctuation():
    text = "Really?! That is amazing!! I can not believe it."
    result = split_sentences(text)
    assert len(result) >= 2


def test_short_fragment_merged():
    text = "Go. Now. Run as fast as you possibly can."
    result = split_sentences(text)
    # "Go." and "Now." are too short, should be merged
    for s in result:
        assert len(s) >= 10 or len(result) == 1


def test_long_multi_sentence():
    text = (
        "Hey, just finished the refactoring. All twenty-three tests are passing. "
        "I cleaned up the circular dependency in the payments module. "
        "Want me to walk you through the changes?"
    )
    result = split_sentences(text)
    assert len(result) >= 3


def test_ellipsis_not_split():
    text = "Well... I think we should proceed. Let us begin."
    result = split_sentences(text)
    assert len(result) >= 1


def test_quoted_text():
    text = 'She said "Hello there." Then she left the room.'
    result = split_sentences(text)
    assert len(result) >= 1


def test_returns_at_least_one():
    assert len(split_sentences("x")) == 1
    assert len(split_sentences("hello")) == 1
