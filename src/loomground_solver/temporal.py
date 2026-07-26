# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Typed temporal and monetary values — validated at write, never coerced.

The schema audit (2026-06-04) found every date in the system stored as a free-
text string, parsed defensively on read, with no duration type at all. That is
fine for *reading* law and fatal for *executing* contracts: a deadline monitor
cannot run on "30 days after signing" held as prose. This module supplies the
missing nouns:

  * ``Date``             — ISO 8601 calendar date, rejected at construction if
                           malformed (no silent coercion, no inferred dates —
                           the NT-2 discipline extended to the type layer);
  * ``Duration``         — ISO 8601 duration (``P1Y2M10DT2H30M``), with
                           calendar-aware date arithmetic (months clamp);
  * ``RelativeDeadline`` — "30 days **after** signing": an event name, an
                           offset, a direction. ``resolve()`` returns a Date
                           only when the anchoring event date is known —
                           otherwise ``None``, never a guess;
  * ``Term``             — contract term: start + (end XOR duration) with an
                           optional ``RenewalRule``;
  * ``Money``            — Decimal amount + ISO 4217 currency code. No floats.

All types are frozen dataclasses with ``to_dict``/``from_dict`` so they store
as plain JSON in the folder's JSONL files and survive round-trips losslessly.
Pure stdlib.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date as _pydate
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Optional

__all__ = [
    "Date", "Duration", "RelativeDeadline", "RenewalRule", "Term", "Money",
    "TemporalError", "validate_iso_instant", "weekend_shift",
]


class TemporalError(ValueError):
    """Raised when a temporal/monetary value is malformed. Reject, don't coerce."""


# ── Date ──────────────────────────────────────────────────────────────────────

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Date:
    """A validated ISO 8601 calendar date (``YYYY-MM-DD``). Construction fails
    on anything else — including datetimes, slashes, two-digit years, and the
    empty string. Use ``Date.parse`` for str input."""

    iso: str

    def __post_init__(self) -> None:
        if not isinstance(self.iso, str) or not _DATE_RE.match(self.iso):
            raise TemporalError(f"not an ISO 8601 date (YYYY-MM-DD): {self.iso!r}")
        try:
            _pydate.fromisoformat(self.iso)
        except ValueError as exc:
            raise TemporalError(f"not a real calendar date: {self.iso!r}") from exc

    @classmethod
    def parse(cls, value: "str | Date") -> "Date":
        if isinstance(value, Date):
            return value
        return cls(value)

    def as_date(self) -> _pydate:
        return _pydate.fromisoformat(self.iso)

    def __lt__(self, other: "Date") -> bool:
        return self.as_date() < other.as_date()

    def __le__(self, other: "Date") -> bool:
        return self.as_date() <= other.as_date()

    def to_dict(self) -> str:
        return self.iso

    @classmethod
    def from_dict(cls, value: str) -> "Date":
        return cls(value)


def weekend_shift(d: "Date") -> "Date":
    """Neutral calendar utility: a Saturday/Sunday date → the following
    Monday. Whether a legal order extends deadlines this way is JURISDICTION
    content — this function is the arithmetic a pack's deadline-shift rule
    may use; the substrate never applies it on its own. Public holidays are
    never resolved here — callers surface a caveat instead of guessing."""
    wd = d.as_date().weekday()                  # Mon=0 … Sun=6
    if wd == 5:
        return Duration(days=2).add_to(d)
    if wd == 6:
        return Duration(days=1).add_to(d)
    return d


def validate_iso_instant(value: str) -> str:
    """Validate a value that may be either an ISO calendar date (``YYYY-MM-DD``)
    or a full ISO 8601 timestamp (``…T…``, ``Z`` accepted). Returns the value
    unchanged on success, raises :class:`TemporalError` otherwise. This is the
    write-gate for fields whose existing convention carries timestamps
    (NT-11): prose and locale formats are rejected; both precision levels of
    real ISO time are not."""
    from datetime import datetime as _dt
    if not isinstance(value, str) or not value:
        raise TemporalError(f"not an ISO date/timestamp: {value!r}")
    if _DATE_RE.match(value):
        Date(value)
        return value
    try:
        _dt.fromisoformat(value.replace("Z", "+00:00"))
        return value
    except ValueError as exc:
        raise TemporalError(f"not an ISO date/timestamp: {value!r}") from exc


# ── Duration ──────────────────────────────────────────────────────────────────

_DUR_RE = re.compile(
    r"^P(?!$)"
    r"(?:(?P<years>\d+)Y)?"
    r"(?:(?P<months>\d+)M)?"
    r"(?:(?P<weeks>\d+)W)?"
    r"(?:(?P<days>\d+)D)?"
    r"(?:T(?!$)"
    r"(?:(?P<hours>\d+)H)?"
    r"(?:(?P<minutes>\d+)M)?"
    r"(?:(?P<seconds>\d+)S)?"
    r")?$"
)


@dataclass(frozen=True)
class Duration:
    """An ISO 8601 duration, e.g. ``P30D``, ``P1Y``, ``P2W``, ``PT72H``.
    Calendar-aware: adding ``P1M`` to Jan 31 clamps to Feb 28/29 (the settled
    convention; the clamp is deterministic, not a guess)."""

    years: int = 0
    months: int = 0
    weeks: int = 0
    days: int = 0
    hours: int = 0
    minutes: int = 0
    seconds: int = 0

    def __post_init__(self) -> None:
        for name in ("years", "months", "weeks", "days", "hours", "minutes", "seconds"):
            v = getattr(self, name)
            if not isinstance(v, int) or v < 0:
                raise TemporalError(f"duration component {name} must be a non-negative int, got {v!r}")
        if not any(getattr(self, n) for n in
                   ("years", "months", "weeks", "days", "hours", "minutes", "seconds")):
            raise TemporalError("zero duration is not a duration")

    @classmethod
    def parse(cls, value: "str | Duration") -> "Duration":
        if isinstance(value, Duration):
            return value
        if not isinstance(value, str):
            raise TemporalError(f"not an ISO 8601 duration: {value!r}")
        m = _DUR_RE.match(value)
        if not m:
            raise TemporalError(f"not an ISO 8601 duration: {value!r}")
        parts = {k: int(v) for k, v in m.groupdict().items() if v is not None}
        return cls(**parts)

    @property
    def iso(self) -> str:
        out = "P"
        for val, unit in ((self.years, "Y"), (self.months, "M"),
                          (self.weeks, "W"), (self.days, "D")):
            if val:
                out += f"{val}{unit}"
        if self.hours or self.minutes or self.seconds:
            out += "T"
            for val, unit in ((self.hours, "H"), (self.minutes, "M"), (self.seconds, "S")):
                if val:
                    out += f"{val}{unit}"
        return out

    def add_to(self, d: Date, *, sign: int = 1) -> Date:
        """Calendar-aware date arithmetic. Time components contribute their
        whole-day equivalent (PT72H = 3 days; floor — the conservative, earlier
        reading); a sub-day remainder does not shift the date."""
        base = d.as_date()
        # months/years first (clamp day), then weeks/days
        total_months = sign * (self.years * 12 + self.months)
        if total_months:
            month0 = base.month - 1 + total_months
            year = base.year + month0 // 12
            month = month0 % 12 + 1
            day = min(base.day, calendar.monthrange(year, month)[1])
            base = _pydate(year, month, day)
        time_days = (self.hours * 3600 + self.minutes * 60 + self.seconds) // 86400
        offset_days = sign * (self.weeks * 7 + self.days + time_days)
        if offset_days:
            base = _pydate.fromordinal(base.toordinal() + offset_days)
        return Date(base.isoformat())

    def to_dict(self) -> str:
        return self.iso

    @classmethod
    def from_dict(cls, value: str) -> "Duration":
        return cls.parse(value)


# ── RelativeDeadline ──────────────────────────────────────────────────────────

_DIRECTIONS = ("after", "before")


@dataclass(frozen=True)
class RelativeDeadline:
    """"30 days after signing": offset + direction from a named event. The event
    name is a slug resolved against a contract's event dates (effective_date,
    signing, delivery, termination_notice, …). ``resolve`` returns ``None`` when
    the event date is unknown — surfacing the gap is the caller's job; guessing
    is nobody's."""

    event: str
    offset: Duration
    direction: str = "after"

    def __post_init__(self) -> None:
        if not self.event or not isinstance(self.event, str):
            raise TemporalError("relative deadline needs a non-empty event name")
        if self.direction not in _DIRECTIONS:
            raise TemporalError(f"direction must be one of {_DIRECTIONS}, got {self.direction!r}")
        if not isinstance(self.offset, Duration):
            raise TemporalError("offset must be a Duration")

    def resolve(self, events: Mapping[str, Date]) -> Optional[Date]:
        anchor = events.get(self.event)
        if anchor is None:
            return None
        return self.offset.add_to(anchor, sign=1 if self.direction == "after" else -1)

    def derivation(self, events: Mapping[str, Date]) -> str:
        """Human-readable derivation for the UI: how the date was computed."""
        anchor = events.get(self.event)
        resolved = self.resolve(events)
        if resolved is None:
            return f"{self.offset.iso} {self.direction} {self.event} → unresolved ({self.event} date unknown)"
        return f"{self.offset.iso} {self.direction} {self.event} ({anchor.iso}) → {resolved.iso}"

    def to_dict(self) -> dict:
        return {"event": self.event, "offset": self.offset.iso, "direction": self.direction}

    @classmethod
    def from_dict(cls, d: dict) -> "RelativeDeadline":
        return cls(event=d["event"], offset=Duration.parse(d["offset"]),
                   direction=d.get("direction", "after"))


# ── Term + RenewalRule ────────────────────────────────────────────────────────

_RENEWAL_KINDS = ("auto", "option")


@dataclass(frozen=True)
class RenewalRule:
    """Renewal mechanics: ``auto`` (renews unless notice given) or ``option``
    (renews only on exercise). ``notice`` is the notice period before term end."""

    kind: str
    period: Duration
    notice: Optional[Duration] = None

    def __post_init__(self) -> None:
        if self.kind not in _RENEWAL_KINDS:
            raise TemporalError(f"renewal kind must be one of {_RENEWAL_KINDS}, got {self.kind!r}")
        if not isinstance(self.period, Duration):
            raise TemporalError("renewal period must be a Duration")
        if self.notice is not None and not isinstance(self.notice, Duration):
            raise TemporalError("renewal notice must be a Duration or None")

    def to_dict(self) -> dict:
        return {"kind": self.kind, "period": self.period.iso,
                "notice": self.notice.iso if self.notice else None}

    @classmethod
    def from_dict(cls, d: dict) -> "RenewalRule":
        return cls(kind=d["kind"], period=Duration.parse(d["period"]),
                   notice=Duration.parse(d["notice"]) if d.get("notice") else None)


@dataclass(frozen=True)
class Term:
    """A contract term. ``end`` and ``duration`` are mutually exclusive — a term
    declared both ways is a drafting conflict the type refuses to paper over.
    All fields optional: an unextracted term is honestly empty, not invented."""

    start: Optional[Date] = None
    end: Optional[Date] = None
    duration: Optional[Duration] = None
    renewal: Optional[RenewalRule] = None

    def __post_init__(self) -> None:
        if self.end is not None and self.duration is not None:
            raise TemporalError("term may declare end OR duration, not both")
        if self.start is not None and self.end is not None and self.end < self.start:
            raise TemporalError(f"term ends ({self.end.iso}) before it starts ({self.start.iso})")

    def end_date(self) -> Optional[Date]:
        """The resolved end: explicit end, or start + duration, else None."""
        if self.end is not None:
            return self.end
        if self.start is not None and self.duration is not None:
            return self.duration.add_to(self.start)
        return None

    def notice_deadline(self) -> Optional[Date]:
        """Last day to give renewal notice (auto-renewal terms), else None."""
        if self.renewal is None or self.renewal.notice is None:
            return None
        end = self.end_date()
        if end is None:
            return None
        return self.renewal.notice.add_to(end, sign=-1)

    def to_dict(self) -> dict:
        return {"start": self.start.iso if self.start else None,
                "end": self.end.iso if self.end else None,
                "duration": self.duration.iso if self.duration else None,
                "renewal": self.renewal.to_dict() if self.renewal else None}

    @classmethod
    def from_dict(cls, d: dict) -> "Term":
        return cls(start=Date(d["start"]) if d.get("start") else None,
                   end=Date(d["end"]) if d.get("end") else None,
                   duration=Duration.parse(d["duration"]) if d.get("duration") else None,
                   renewal=RenewalRule.from_dict(d["renewal"]) if d.get("renewal") else None)


# ── Money ─────────────────────────────────────────────────────────────────────

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
# Curated common set for an extra sanity check; format check is the gate, the
# set only warns via ``known`` so exotic-but-valid ISO 4217 codes still pass.
_KNOWN_CURRENCIES = frozenset({
    "EUR", "USD", "GBP", "CHF", "JPY", "CNY", "SEK", "NOK", "DKK", "PLN",
    "CZK", "HUF", "RON", "BGN", "HRK", "CAD", "AUD", "NZD", "SGD", "HKD",
    "INR", "BRL", "MXN", "ZAR", "KRW", "TRY", "ISK",
})


@dataclass(frozen=True)
class Money:
    """A Decimal amount in an ISO 4217 currency. Floats are rejected outright —
    a contract value that went through binary floating point is already wrong."""

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if isinstance(self.amount, float):
            raise TemporalError("Money amount must be Decimal or str, never float")
        if not isinstance(self.amount, Decimal):
            try:
                object.__setattr__(self, "amount", Decimal(str(self.amount)))
            except (InvalidOperation, ValueError) as exc:
                raise TemporalError(f"not a decimal amount: {self.amount!r}") from exc
        if not isinstance(self.currency, str) or not _CURRENCY_RE.match(self.currency):
            raise TemporalError(f"not an ISO 4217 currency code: {self.currency!r}")

    @property
    def known(self) -> bool:
        return self.currency in _KNOWN_CURRENCIES

    def to_dict(self) -> dict:
        return {"amount": str(self.amount), "currency": self.currency}

    @classmethod
    def from_dict(cls, d: dict) -> "Money":
        return cls(amount=Decimal(d["amount"]), currency=d["currency"])
