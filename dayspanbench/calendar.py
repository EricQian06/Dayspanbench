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
