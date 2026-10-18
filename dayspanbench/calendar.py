"""Deterministic calendars. Intervals are half-open; business minutes pause at closure."""

from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo


def parse(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp must include a UTC offset")
    return result.astimezone(timezone.utc)


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


class Calendar:
    def __init__(self, spec: dict):
        self.spec = spec
        self.zone = ZoneInfo(spec["timezone"])

    def intervals(self, day):
        if day.isoformat() in self.spec.get("closed_dates", []):
            return []
        windows = self.spec.get("overrides", {}).get(day.isoformat())
        if windows is None:
            if day.weekday() not in self.spec["weekdays"]:
                return []
            windows = self.spec["hours"]
        return [
            (datetime.combine(day, time.fromisoformat(a), self.zone).astimezone(timezone.utc),
             datetime.combine(day, time.fromisoformat(b), self.zone).astimezone(timezone.utc))
            for a, b in windows
        ]

    def is_open(self, now: datetime) -> bool:
        day = now.astimezone(self.zone).date()
        return any(a <= now < b for a, b in self.intervals(day))

    def next_open(self, now: datetime) -> datetime:
        day = now.astimezone(self.zone).date()
        for _ in range(370):
            for start, end in self.intervals(day):
                if now < end:
                    return max(now, start)
            day += timedelta(days=1)
        raise ValueError("No opening in the next 370 days")

    def add_business(self, now: datetime, minutes: int) -> datetime:
        if minutes < 0:
            raise ValueError("Negative duration")
        current = self.next_open(now)
        remaining = timedelta(minutes=minutes)
        if remaining == timedelta():
            return current
        for _ in range(10000):
            for start, end in self.intervals(current.astimezone(self.zone).date()):
                if start <= current < end:
                    available = end - current
                    if remaining <= available:
                        return current + remaining
                    remaining -= available
                    current = end
                    break
            current = self.next_open(current)
        raise ValueError("Business duration exceeds simulation horizon")

    def next_slot(self, now: datetime, weekday: int, clock: str) -> datetime:
        day = now.astimezone(self.zone).date()
        for _ in range(370):
            candidate = datetime.combine(day, time.fromisoformat(clock), self.zone).astimezone(timezone.utc)
            if day.weekday() == weekday and candidate >= now:
                if any(a <= candidate < b for a, b in self.intervals(day)):
                    return candidate
            day += timedelta(days=1)
        raise ValueError("No valid weekly slot")

    def schedule(self, now: datetime, delay: dict, resource_free: datetime):
        mode = delay.get("mode", "business")
        anchor = max(now, parse(delay["not_before"])) if delay.get("not_before") else now
        if mode == "elapsed":
            # Waiting for an external event does not reserve a worker.
            due = anchor + timedelta(minutes=delay.get("minutes", 0))
            return anchor, due, resource_free
        anchor = max(anchor, resource_free)
        if mode == "weekly":
            anchor = self.next_slot(anchor, delay["weekday"], delay["time"])
        elif mode != "business":
            raise ValueError(f"Unknown delay mode: {mode}")
        start = self.next_open(anchor)
        end = self.add_business(start, delay.get("minutes", 0))
        return start, end, end

    def reserve(self, now, delay, reservations):
        """Allocate working intervals, leaving gaps before future bookings usable.

        Reservations are half-open UTC intervals. Existing work keeps priority;
        ordinary business work can pause at closures or reserved intervals.
        A weekly batch must fit its fixed slot without overlapping other work.
        The caller owns the list; ETA projections pass a copy.
        """
        mode = delay.get("mode", "business")
        anchor = max(now, parse(delay["not_before"])) if delay.get("not_before") else now
        minutes = delay.get("minutes", 0)
        if minutes < 0:
            raise ValueError("Negative duration")
        if mode == "elapsed":
            return anchor, anchor + timedelta(minutes=minutes)
        if mode not in {"business", "weekly"}:
            raise ValueError(f"Unknown delay mode: {mode}")
        occupied = sorted((a, b) for a, b in reservations if b > anchor)
        if mode == "weekly":
            for _ in range(53):
                start = self.next_slot(anchor, delay["weekday"], delay["time"])
                end = self.add_business(start, minutes)
                conflicts = [(a, b) for a, b in occupied if a < end and b > start]
                if not conflicts:
                    break
                anchor = max(start + timedelta(microseconds=1), max(b for _, b in conflicts))
            else:
                raise ValueError("No free weekly slot")
        else:
            start = self.next_open(anchor)
            end = None
        remaining = timedelta(minutes=minutes)
        current, segments = start, []
        for _ in range(20000):
            current = self.next_open(current)
            clash = next(((a, b) for a, b in occupied if a <= current < b), None)
            if clash:
                current = clash[1]
                continue
            if not segments:
                start = current
            if remaining == timedelta():
                return start, current
            close = next(b for a, b in self.intervals(current.astimezone(self.zone).date())
                         if a <= current < b)
            next_booking = min((a for a, b in occupied if a > current), default=close)
            stop = min(close, next_booking, current + remaining)
            segments.append((current, stop))
            remaining -= stop - current
            current = stop
            if remaining == timedelta():
                reservations.extend(segments)
                reservations.sort()
                return start, current
        raise ValueError("Reservation exceeds simulation horizon")
