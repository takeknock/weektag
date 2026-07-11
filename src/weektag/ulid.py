"""Mini-ULID: 8-char time-sortable id (ADR 0004).

Layout: 6 Crockford-base32 chars of seconds since 2020-01-01 UTC (sortable
until 2054), followed by 2 random chars. Second-level precision is enough
for a single-user CLI; prefix matching is the primary lookup.
"""

from __future__ import annotations

import datetime as dt
import secrets

CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

_EPOCH = dt.datetime(2020, 1, 1, tzinfo=dt.UTC)
_TS_CHARS = 6
_RAND_CHARS = 2


def _encode(value: int, width: int) -> str:
    chars = []
    for _ in range(width):
        chars.append(CROCKFORD[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))


def mini_ulid(now: dt.datetime | None = None) -> str:
    if now is None:
        now = dt.datetime.now().astimezone()
    seconds = int((now - _EPOCH).total_seconds())
    rand = secrets.randbelow(32**_RAND_CHARS)
    return _encode(seconds, _TS_CHARS) + _encode(rand, _RAND_CHARS)
