# SPDX-License-Identifier: MPL-2.0
import asyncio
import math
import unittest
from unittest.mock import AsyncMock, Mock
from cast_audio_lab.mpv_backend import MpvAudioBackend


class MpvEventTests(unittest.IsolatedAsyncioTestCase):
    async def test_malformed_ipc_object_is_contained_as_decoder_error(self):
        b = MpvAudioBackend()
        reader = asyncio.StreamReader()
        reader.feed_data(b'[]\n')
        reader.feed_eof()
        await b._read(reader)
        self.assertEqual(b.status().idle_reason, 'ERROR')
        self.assertIsNone(b._writer)

    async def test_malformed_property_values_cannot_poison_wire_state(self):
        b = MpvAudioBackend()
        b._status.state = 'PLAYING'
        b._set_position(7)
        b._status.volume = .4
        for value in (float('nan'), float('inf'), '-inf', 'not numeric', [], True):
            await b._event({'event': 'property-change', 'name': 'time-pos', 'data': value})
            await b._event({'event': 'property-change', 'name': 'volume', 'data': value})
            self.assertTrue(math.isfinite(b.status().current_time))
            self.assertEqual(b.status().current_time, 7)
            self.assertEqual(b.status().volume, .4)
        await b._event({'event': 'property-change', 'name': 'mute', 'data': 'false'})
        await b._event({'event': 'property-change', 'name': 'pause', 'data': 'false'})
        self.assertFalse(b.status().muted)
        self.assertEqual(b.status().state, 'PLAYING')

    async def test_replaced_entry_error_cannot_poison_new_load(self):
        b = MpvAudioBackend()
        b._start = AsyncMock()
        b._command = AsyncMock()
        b._loading = True
        await b._event({"event": "start-file", "playlist_entry_id": 1})
        await b._event({"event": "file-loaded"})
        await b.load("https://example.test/new", "audio/mp4", False, 17)
        await b._event({"event": "end-file", "reason": "error", "playlist_entry_id": 1})
        self.assertTrue(b._loading)
        self.assertEqual(b.status().state, "BUFFERING")
        self.assertIsNone(b.status().idle_reason)
        await b._event({"event": "playback-restart"})
        self.assertEqual(b.status().state, "BUFFERING")
        await b._event({"event": "start-file", "playlist_entry_id": 2})
        await b._event({"event": "file-loaded"})
        for reason in ("eof", "error"):
            await b._event({"event": "end-file", "reason": reason, "playlist_entry_id": 1})
        self.assertEqual(b.status().state, "PAUSED")
        self.assertIsNone(b.status().idle_reason)
        await b._event({"event": "end-file", "reason": "error", "playlist_entry_id": 2})
        self.assertEqual(b.status().idle_reason, "ERROR")

    async def test_late_file_loaded_after_stop_cannot_resurrect_playback(self):
        b = MpvAudioBackend()
        b._command = AsyncMock()
        await b.stop()
        await b._event({"event": "file-loaded"})
        self.assertEqual(b.status().state, "IDLE")
        self.assertEqual(b.status().idle_reason, "CANCELLED")

    async def test_current_entry_eof_while_loading_is_not_discarded(self):
        b = MpvAudioBackend()
        b._loading = True
        b._status.state = "BUFFERING"
        await b._event({"event": "start-file", "playlist_entry_id": 2})
        await b._event({"event": "end-file", "reason": "eof", "playlist_entry_id": 2})
        self.assertFalse(b._loading)
        self.assertEqual(b.status().idle_reason, "FINISHED")

    async def test_load_after_reader_eof_preserves_new_selection_state(self):
        b = MpvAudioBackend()
        reader = asyncio.StreamReader()
        reader.feed_eof()
        b._reader_task = asyncio.create_task(b._read(reader))
        b._spawn = AsyncMock()
        b._command = AsyncMock()
        b._emit_status = Mock()
        await b.load("https://example.test/new", "audio/mp4", False, 17)
        b._emit_status.assert_not_called()
        self.assertEqual(b.status().state, "BUFFERING")
        self.assertIsNone(b.status().idle_reason)
        self.assertTrue(b._loading)
        self.assertEqual(b.status().current_time, 17)
        await b._event({"event": "file-loaded"})
        self.assertEqual(b.status().state, "PAUSED")
        self.assertIsNone(b.status().idle_reason)

    async def test_cleanup_kills_process_that_does_not_terminate(self):
        b = MpvAudioBackend()
        process = Mock(wait=AsyncMock(side_effect=[TimeoutError(), 0]))
        b._process = process
        await b.shutdown()
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertEqual(process.wait.await_count, 2)

    async def test_broken_command_pipe_disposes_decoder_and_reports_error(self):
        b = MpvAudioBackend()
        b._status.state = "PLAYING"
        b._writer = Mock(wait_closed=AsyncMock())
        b._writer.write.side_effect = BrokenPipeError()
        with self.assertRaises(BrokenPipeError):
            await b._command("pause")
        self.assertEqual(b.status().idle_reason, "ERROR")
        self.assertFalse(b._pending)
        self.assertIsNone(b._writer)

    async def test_restart_waits_for_previous_process_cleanup(self):
        b = MpvAudioBackend()
        reaping = asyncio.Event()
        release = asyncio.Event()
        async def wait():
            reaping.set()
            await release.wait()
        b._process = Mock(wait=wait)
        b._spawn = AsyncMock()
        cleanup = asyncio.create_task(b.shutdown())
        await reaping.wait()
        restart = asyncio.create_task(b._start())
        await asyncio.sleep(0)
        b._spawn.assert_not_awaited()
        release.set()
        await asyncio.gather(cleanup, restart)
        b._spawn.assert_awaited_once()

    async def test_ipc_eof_fails_pending_command_and_allows_restart(self):
        b = MpvAudioBackend()
        b._status.state = "PLAYING"
        b._writer = Mock(drain=AsyncMock(), wait_closed=AsyncMock())
        process = Mock(wait=AsyncMock(return_value=0))
        b._process = process
        reader = asyncio.StreamReader()
        b._reader_task = asyncio.create_task(b._read(reader))
        reader_task = b._reader_task
        command = asyncio.create_task(b._command("get_property", "time-pos"))
        await asyncio.sleep(0)
        reader.feed_eof()
        with self.assertRaises(OSError):
            await asyncio.wait_for(command, 1)
        await reader_task
        self.assertEqual(b.status().idle_reason, "ERROR")
        self.assertIsNone(b._writer)
        self.assertIsNone(b._process)
        process.terminate.assert_called_once()
        b._spawn = AsyncMock()
        await b._start()
        b._spawn.assert_awaited_once()

    async def test_failed_start_reaps_process_and_clears_resources(self):
        b = MpvAudioBackend()
        process = Mock(wait=AsyncMock(return_value=0))
        async def failed_spawn():
            b._process = process
            raise OSError("IPC unavailable")
        b._spawn = failed_spawn
        with self.assertRaises(OSError):
            await b.load("https://example.test/audio", "audio/mp4", True, 0)
        self.assertEqual(b.status().idle_reason, "ERROR")
        self.assertIsNone(b._process)
        process.terminate.assert_called_once()

    async def test_stop_with_broken_ipc_still_clears_playback(self):
        b = MpvAudioBackend()
        b._status.state = "PLAYING"
        b._writer = Mock(wait_closed=AsyncMock())
        b._command = AsyncMock(side_effect=BrokenPipeError())
        await b.stop()
        self.assertEqual(b.status().idle_reason, "CANCELLED")
        self.assertIsNone(b._writer)

    async def test_shutdown_reaps_already_exited_process(self):
        b = MpvAudioBackend()
        process = Mock(wait=AsyncMock(return_value=1))
        process.terminate.side_effect = ProcessLookupError()
        b._process = process
        await b.shutdown()
        process.wait.assert_awaited_once()
        self.assertIsNone(b._process)

    async def test_seek_timeout_restores_position_and_accepts_feedback(self):
        b = MpvAudioBackend()
        b._status.state = "PLAYING"
        b._set_position(10)
        b._command = AsyncMock(side_effect=TimeoutError())
        with self.assertRaises(TimeoutError):
            await b.seek(42)
        self.assertFalse(b._seeking)
        self.assertEqual(b.status().current_time, 10)
        await b._event({"event": "property-change", "name": "time-pos", "data": 11})
        self.assertEqual(b.status().current_time, 11)

    async def test_local_cache_limits_readahead_without_affecting_other_sources(self):
        b = MpvAudioBackend()
        b._start = AsyncMock()
        b._command = AsyncMock()
        await b.load("http://127.0.0.1:8010/manifest/session/cache-title", "audio/mp4", True, 0)
        options = b._command.await_args_list[-1].args[-1]
        self.assertEqual(options["cache-secs"], "30")
        self.assertEqual(options["demuxer-max-bytes"], "512KiB")
        await b.load("https://example.invalid/audio", "audio/mp4", True, 0)
        self.assertEqual(b._command.await_args_list[-1].args[-1], {"start": "0"})

    async def test_play_after_stop_cannot_start_empty_decoder(self):
        b = MpvAudioBackend()
        b._command = AsyncMock()
        await b.stop()
        await b.play()
        await b.pause()
        self.assertEqual(b.status().state, "IDLE")
        self.assertEqual(b.status().idle_reason, "CANCELLED")
        b._command.assert_not_awaited()

    async def test_play_after_failed_load_does_not_claim_playback(self):
        b = MpvAudioBackend()
        b._command = AsyncMock()
        await b._event({"event": "end-file", "reason": "error"})
        await b.play()
        await b.pause()
        self.assertEqual(b.status().state, "IDLE")
        self.assertEqual(b.status().idle_reason, "ERROR")
        b._command.assert_not_awaited()

    async def test_older_mpv_loadfile_retains_start_and_pause(self):
        b = MpvAudioBackend()
        b._start = AsyncMock()
        b._command = AsyncMock(side_effect=[None, ValueError(
            "mpv command failed: invalid parameter"), None])
        await b.load("https://example.invalid/audio", "audio/wav", False, 42)
        self.assertEqual(b._command.await_args_list[-1].args,
                         ("loadfile", "https://example.invalid/audio", "replace", {"start": "42"}))
        self.assertFalse(b._autoplay)
        self.assertEqual(b.status().current_time, 42)

    async def test_load_does_not_retry_unrelated_failure(self):
        b = MpvAudioBackend()
        b._start = AsyncMock()
        b._command = AsyncMock(side_effect=[None, ValueError("media failed")])
        with self.assertRaisesRegex(ValueError, "media failed"):
            await b.load("https://example.invalid/audio", "audio/wav", True, 0)
        self.assertEqual(b._command.await_count, 2)
        self.assertFalse(b._loading)
        self.assertEqual(b.status().idle_reason, "ERROR")

    async def test_rejected_legacy_fallback_does_not_leave_buffering(self):
        b = MpvAudioBackend()
        b._start = AsyncMock()
        b._command = AsyncMock(side_effect=[None, ValueError(
            "mpv command failed: invalid parameter"), ValueError("load failed")])
        with self.assertRaisesRegex(ValueError, "load failed"):
            await b.load("https://example.invalid/audio", "audio/wav", True, 0)
        self.assertFalse(b._loading)
        self.assertEqual(b.status().state, "IDLE")

    async def test_failed_load_releases_feedback_gates(self):
        b = MpvAudioBackend()
        b._loading = True
        b._seeking = True
        await b._event({"event": "end-file", "reason": "error", "file_error": "loading failed"})
        self.assertFalse(b._loading)
        self.assertFalse(b._seeking)
        self.assertEqual(b.status().idle_reason, "ERROR")

    async def test_old_position_during_load_is_ignored(self):
        b = MpvAudioBackend()
        b._loading = True
        b._status.state = "BUFFERING"
        await b._event({"event": "property-change", "name": "time-pos", "data": 213})
        self.assertEqual(b.status().current_time, 0)

    async def test_pause_survives_cache_feedback(self):
        b = MpvAudioBackend()
        b._status.state = "PLAYING"
        b._command = AsyncMock()
        await b.pause()
        await b._event({"event": "property-change", "name": "paused-for-cache", "data": False})
        self.assertEqual(b.status().state, "PAUSED")
        self.assertFalse(b._autoplay)

    async def test_rejected_seek_reopens_paused_media(self):
        b = MpvAudioBackend()
        b._status.url = "https://example.invalid/audio"
        b._status.content_type = "audio/webm"
        b._status.state = "PAUSED"
        b._command = AsyncMock(side_effect=ValueError("not seekable"))
        b.load = AsyncMock()
        await b.seek(42)
        b.load.assert_awaited_once_with(b._status.url, "audio/webm", False, 42)

    async def test_eof_and_failure_differ(self):
        b = MpvAudioBackend()
        await b._event({"event": "end-file", "reason": "error"})
        self.assertEqual(b.status().idle_reason, "ERROR")
        await b._event({"event": "end-file", "reason": "eof"})
        self.assertEqual(b.status().idle_reason, "FINISHED")

    async def test_replace_stop_does_not_finish_new_load(self):
        b = MpvAudioBackend()
        b._status.state = "BUFFERING"
        await b._event({"event": "end-file", "reason": "stop"})
        self.assertEqual(b.status().state, "BUFFERING")
        self.assertIsNone(b.status().idle_reason)

    async def test_feedback_uses_decoder_position_and_volume(self):
        b = MpvAudioBackend()
        for name, data in [("time-pos", 63.25), ("volume", 42), ("mute", True)]:
            await b._event({"event": "property-change", "name": name, "data": data})
        s = b.status()
        self.assertEqual(s.current_time, 63.25)
        self.assertEqual(s.volume, .42)
        self.assertTrue(s.muted)
