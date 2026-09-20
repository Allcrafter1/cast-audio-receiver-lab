"""Small shared disk cache for processed covers; no persistent worker."""
import asyncio
import contextlib
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from .artwork import prepare_square_artwork


class ArtworkCache:
    def __init__(self, directory: Path, *, convert=prepare_square_artwork,
                 limit=32, ttl=3600, clock=time.monotonic):
        self.directory = directory
        self.convert = convert
        self.limit, self.ttl, self.clock = limit, ttl, clock
        self.entries = {}
        self.pending = {}
        self.worker = asyncio.Semaphore(1)

    def _expire(self):
        now = self.clock()
        for source, (ident, expires) in list(self.entries.items()):
            if expires <= now:
                self.entries.pop(source)
                (self.directory / f'{ident}.jpg').unlink(missing_ok=True)

    async def prepare(self, source):
        parsed = urlsplit(source)
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname
                or parsed.username or parsed.password or len(source) > 8192
                or any(ord(c) < 32 for c in source)):
            raise ValueError('invalid artwork URL')
        self._expire()
        if source in self.entries:
            ident, _ = self.entries[source]
            if (self.directory / f'{ident}.jpg').is_file():
                self.entries[source] = (ident, self.clock() + self.ttl)
                return ident
            self.entries.pop(source)
        if source not in self.pending:
            if len(self.pending) >= 4:
                return None
            self.pending[source] = asyncio.create_task(self._prepare(source))
        # Several speakers may request the same album. A departing sender must
        # not cancel conversion still needed by another speaker.
        return await asyncio.shield(self.pending[source])

    async def _prepare(self, source):
        ident = uuid.uuid4().hex
        path = self.directory / f'{ident}.jpg'
        try:
            async with self.worker:
                self.directory.mkdir(parents=True, exist_ok=True)
                if not await self.convert(source, path, 'ffmpeg'):
                    return None
                self._expire()
                while len(self.entries) >= self.limit:
                    oldest = min(self.entries, key=lambda key: self.entries[key][1])
                    old_id, _ = self.entries.pop(oldest)
                    (self.directory / f'{old_id}.jpg').unlink(missing_ok=True)
                self.entries[source] = (ident, self.clock() + self.ttl)
                return ident
        except (OSError, TimeoutError):
            # Also consume failures when the requesting track has already left.
            return None
        finally:
            self.pending.pop(source, None)
            if source not in self.entries:
                with contextlib.suppress(OSError):
                    path.unlink(missing_ok=True)

    def get(self, ident):
        self._expire()
        if not any(value[0] == ident for value in self.entries.values()):
            return None
        path = self.directory / f'{ident}.jpg'
        return path if path.is_file() else None

    async def close(self):
        tasks = list(self.pending.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
