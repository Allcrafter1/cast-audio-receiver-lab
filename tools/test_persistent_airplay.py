"""Opt-in physical test: emits quiet tones to the explicitly configured target."""
import argparse
import asyncio
import logging
import tempfile
from pathlib import Path

from cast_audio_lab.airplay import AirPlayAudioBackend, load_airplay_target
from cast_audio_lab.backend import MediaMetadata


async def run(args):
    backend = AirPlayAudioBackend(load_airplay_target(args.config), cliairplay=args.cliairplay)
    events = []
    backend.event_handler = lambda event: events.append(event.name)
    async def wait_for(predicate, label, timeout=15):
        deadline = asyncio.get_running_loop().time() + timeout
        while not predicate():
            if backend.status().idle_reason == 'ERROR':
                raise RuntimeError('backend error during ' + label)
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError(label)
            await asyncio.sleep(0.05)
    with tempfile.TemporaryDirectory(prefix='airplay-warm-test-') as directory:
        tone = Path(directory) / 'tone.wav'
        child = await asyncio.create_subprocess_exec(
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi',
            '-i', 'sine=frequency=660:duration=4', '-af', 'volume=0.08',
            '-ac', '2', '-ar', '44100', str(tone))
        assert await child.wait() == 0
        try:
            await backend.set_volume(0.3, False)
            await backend.set_metadata(MediaMetadata(title='Persistent AirPlay test', duration=4))
            await backend.load(str(tone), 'audio/wav', True, 0)
            await wait_for(lambda: backend.status().state == 'PLAYING', 'initial start')
            pid = backend._cli.pid
            await asyncio.sleep(0.8)
            await backend.pause()
            await asyncio.sleep(0.5)
            assert backend.status().state == 'PAUSED'
            await backend.seek(1)
            await wait_for(lambda: backend._track_started, 'paused seek START')
            assert backend._cli.pid == pid and backend.status().state == 'PAUSED'
            await backend.play()
            await asyncio.sleep(0.5)
            await backend.load(str(tone), 'audio/wav', True, 0)
            await wait_for(lambda: backend.status().idle_reason == 'FINISHED', 'natural end')
            assert backend._cli.pid == pid
            await backend.load(str(tone), 'audio/wav', True, 3)
            await wait_for(lambda: backend.status().idle_reason == 'FINISHED', 'short remainder end')
            assert backend._cli.pid == pid
            print('PASS: pause, paused seek, next, natural end, short remainder; same CLI PID', pid)
            print('connections=', events.count('connected'), 'flushes=', events.count('flushed'))
            # Terminate only the helper owned by this test. A lost transport
            # must recover on the next load instead of reusing a dead pipe.
            backend._cli.kill()
            await backend._cli.wait()
            await backend.load(str(tone), 'audio/wav', True, 3)
            await wait_for(lambda: backend.status().idle_reason == 'FINISHED', 'dead transport recovery')
            assert backend._cli.pid != pid
            print('PASS: dead transport replaced; new CLI PID', backend._cli.pid)
        finally:
            await backend.shutdown()
        assert backend._cli is None and backend._decoder is None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--cliairplay', required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    asyncio.run(run(args))
