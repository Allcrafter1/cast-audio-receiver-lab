import asyncio
from pathlib import Path
import tempfile
import unittest

from cast_audio_lab.artwork_cache import ArtworkCache


class CacheTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.calls = []
        self.now = 0
        async def convert(source, output, ffmpeg):
            self.calls.append(source)
            await asyncio.sleep(0)
            output.write_bytes(b'jpeg')
            return True
        self.cache = ArtworkCache(Path(self.temp.name), convert=convert, limit=2,
                                  ttl=10, clock=lambda: self.now)

    async def asyncTearDown(self):
        await self.cache.close()
        self.temp.cleanup()

    async def test_coalescing_expiry_and_eviction(self):
        a, b = await asyncio.gather(self.cache.prepare('https://example.test/a'),
                                    self.cache.prepare('https://example.test/a'))
        self.assertEqual(a, b)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.cache.get(a).read_bytes(), b'jpeg')
        self.now = 1
        await self.cache.prepare('https://example.test/b')
        self.now = 2
        await self.cache.prepare('https://example.test/c')
        self.assertIsNone(self.cache.get(a))
        self.assertEqual(len(list(Path(self.temp.name).glob('*.jpg'))), 2)
        self.now = 20
        self.assertIsNone(self.cache.get(b))
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    async def test_cancelled_waiter_does_not_cancel_shared_conversion(self):
        started, release = asyncio.Event(), asyncio.Event()
        async def convert(source, output, ffmpeg):
            started.set()
            await release.wait()
            output.write_bytes(b'jpeg')
            return True
        self.cache.convert = convert
        first = asyncio.create_task(self.cache.prepare('https://example.test/a'))
        await started.wait()
        first.cancel()
        await asyncio.gather(first, return_exceptions=True)
        second = asyncio.create_task(self.cache.prepare('https://example.test/a'))
        release.set()
        ident = await second
        self.assertIsNotNone(self.cache.get(ident))
        self.assertEqual(len(self.cache.entries), 1)

    async def test_bad_source_and_missing_image(self):
        for source in ['file:///etc/passwd', 'https://user:password@example.test/a', 'http://', 'pipe:0']:
            with self.assertRaises(ValueError):
                await self.cache.prepare(source)
        ident = await self.cache.prepare('https://example.test/a')
        self.cache.get(ident).unlink()
        replacement = await self.cache.prepare('https://example.test/a')
        self.assertNotEqual(ident, replacement)

