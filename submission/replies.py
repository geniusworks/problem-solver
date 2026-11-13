"""Reading Advent of Code's reply to a submitted answer.

A reply the parser does not recognise is UNKNOWN, and the submission step stops on it:
guessing what an unfamiliar reply meant could post inside a wait or post twice.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from bs4 import BeautifulSoup


class ReplyKind(str, Enum):
    ACCEPTED = "accepted"
    WRONG = "wrong"
    TOO_HIGH = "too_high"
    TOO_LOW = "too_low"
    # Posted inside a wait; the answer was not judged.
    TOO_RECENT = "too_recent"
    # The part is already solved, or not open to this account.
    WRONG_LEVEL = "wrong_level"
    UNKNOWN = "unknown"


# Replies that judged the answer, so it is never posted again.
JUDGED = frozenset({ReplyKind.ACCEPTED, ReplyKind.WRONG, ReplyKind.TOO_HIGH, ReplyKind.TOO_LOW})
# Replies that count against a part's wrong-answer budget. An unknown reply counts: it may
# have been a wrong answer.
COUNTS_AS_WRONG = frozenset({ReplyKind.WRONG, ReplyKind.TOO_HIGH, ReplyKind.TOO_LOW, ReplyKind.UNKNOWN})


@dataclass(frozen=True)
class Reply:
    kind: ReplyKind
    # The wait AoC states before the next answer, in seconds; None where it states none.
    wait_seconds: Optional[int]
    text: str


_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
          "eight": 8, "nine": 9, "ten": 10, "fifteen": 15, "twenty": 20, "thirty": 30}


def _minutes_to_wait(text: str) -> Optional[int]:
    """'please wait one minute' / 'wait 5 minutes' -> seconds."""
    match = re.search(r"wait (\w+) minutes?", text, re.IGNORECASE)
    if not match:
        return None
    word = match.group(1).lower()
    count = int(word) if word.isdigit() else _WORDS.get(word)
    return None if count is None else count * 60


def _time_left(text: str) -> Optional[int]:
    """'You have 1m 30s left to wait' / 'You have 41s left to wait' -> seconds."""
    match = re.search(r"you have (?:(\d+)m\s*)?(\d+)s left to wait", text, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1) or 0) * 60 + int(match.group(2))


def parse_reply(html: str) -> Reply:
    """Classify the page AoC returns for a posted answer."""
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")
    text = " ".join((article.get_text() if article else "").split())

    if text.startswith("That's the right answer"):
        return Reply(ReplyKind.ACCEPTED, None, text)

    if text.startswith("You gave an answer too recently"):
        wait = _time_left(text)
        if wait is None:
            return Reply(ReplyKind.UNKNOWN, None, text)
        return Reply(ReplyKind.TOO_RECENT, wait, text)

    if text.startswith("That's not the right answer"):
        wait = _minutes_to_wait(text)
        if wait is None:
            wait = _time_left(text)
        if wait is None:
            # A wrong answer always states its wait; one that does not is unfamiliar.
            return Reply(ReplyKind.UNKNOWN, None, text)
        lowered = text.lower()
        if "your answer is too high" in lowered:
            return Reply(ReplyKind.TOO_HIGH, wait, text)
        if "your answer is too low" in lowered:
            return Reply(ReplyKind.TOO_LOW, wait, text)
        return Reply(ReplyKind.WRONG, wait, text)

    if text.startswith("You don't seem to be solving the right level"):
        return Reply(ReplyKind.WRONG_LEVEL, None, text)

    return Reply(ReplyKind.UNKNOWN, None, text)
