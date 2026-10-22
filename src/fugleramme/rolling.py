"""The birds on the Rolling variety page, and how the page moves.

The page holds a band of species - the ones that joined, oldest first - between a
floor and a ceiling. Each tick fills up to the floor, then drifts inside the band,
and when it is at the ceiling it sheds the oldest; a bird is always drawn at
random from the pool and never one already on the page. So the page keeps showing
the station's variety, at a size that shifts, and the birds that leave are the
oldest.

State is persisted beside artwork.json, so a restart resumes the same page and
the choice is not re-rolled on every render. Only the service loop moves it: the
kiosk and the admin preview read the ring, never advance it.
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Iterable

FILENAME = "rolling.json"


class Rolling:
    """Species keys, in the order they joined the page."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._names = self._read() if self.path.exists() else []

    def _read(self) -> list[str]:
        try:
            raw = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return []
        return [str(name) for name in raw] if isinstance(raw, list) else []

    def names(self) -> list[str]:
        return list(self._names)

    def tick(self, pool: Iterable[str], low: int, high: int) -> bool:
        """Move the page one step: fill to `low`, then drift between `low` and
        `high`, shedding the oldest at the ceiling. Pinned (low == high) it trades
        the oldest for a new bird instead, so the size does not flicker. A name
        that has left `pool` - no longer drawable, or out of the region - is
        forgotten. True when the page changed."""
        if high <= 0:
            return False
        low = max(1, min(low, high))
        pool = list(dict.fromkeys(pool))
        in_pool = set(pool)
        kept = [name for name in self._names if name in in_pool]
        changed = kept != self._names
        self._names = kept
        candidates = [name for name in pool if name not in self._names]

        def join() -> bool:
            if not candidates:
                return False
            self._names.append(random.choice(candidates))
            return True

        count = len(self._names)
        if low == high:
            if count > high:
                self._names.pop(0)  # the oldest drops off
                changed = True
            elif count < high:
                changed = join() or changed
            elif candidates:  # full: trade the oldest for a new bird
                self._names.pop(0)
                self._names.append(random.choice(candidates))
                changed = True
        elif count < low:
            changed = join() or changed
        elif count > high:
            self._names.pop(0)
            changed = True
        elif candidates and count < high and random.random() < 0.5:
            changed = join() or changed
        elif count > low:
            self._names.pop(0)
            changed = True
        elif candidates:
            changed = join() or changed

        if changed:
            self._write()
        return changed

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(self._names, indent=2) + "\n")
        os.replace(tmp, self.path)
