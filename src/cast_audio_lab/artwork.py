"""Shared image conversion policy for every output protocol.

The public helper deliberately does not know about AirPlay, Cast or Home
Assistant.  It turns a local file or an HTTP(S) image into one bounded,
center-cropped square JPEG.  A lossless PNG intermediate is used so that the
optional embedded-letterbox pass does not quantise an already-compressed JPEG
again.  This keeps the policy reusable when the Cast/HA image endpoint is
added, while the current AirPlay adapter can use exactly the same bytes.
"""

import asyncio
import contextlib
from pathlib import Path


MAX_ARTWORK_SIDE = 512
MAX_ARTWORK_BYTES = 1_048_576
WORKING_IMAGE_MAX_BYTES = 4 * 1_048_576
ARTWORK_FETCH_TIMEOUT = 8

# Landscape: retain full height and cut equal strips from left/right.
# Portrait: retain full width and cut equal strips from top/bottom.
# Keep small covers at native resolution; normalize sample aspect ratio.
SQUARE_COVER_FILTER = (
    "crop='min(iw,ih)':'min(iw,ih)',"
    f"scale='min({MAX_ARTWORK_SIDE},iw)':'min({MAX_ARTWORK_SIDE},ih)':flags=lanczos,setsar=1"
)
# FFmpeg's default JPEG quantizer is small-file oriented. Artwork is already
# bounded to 512px/1MiB, so prefer a visually lossless quantizer.
JPEG_QUALITY_ARGS = ("-q:v", "2")


def embedded_bar_inset(gray: bytes, side: int = 64) -> int:
    """Find only symmetric, full-width black edge bands in a square preview.

    Reject nearly black images, asymmetric edges and isolated dark pixels.
    This is deliberately not general-purpose content-aware cropping.
    """
    if len(gray) != side * side or side < 8:
        return 0
    rows = [max(gray[y*side:(y+1)*side]) <= 12 for y in range(side)]
    top = next((i for i, dark in enumerate(rows) if not dark), side)
    bottom = next((i for i, dark in enumerate(reversed(rows)) if not dark), side)
    if min(top, bottom) < 2 or max(top, bottom) > side//4 or abs(top-bottom) > 1:
        return 0
    return min(top, bottom)


async def remove_embedded_bars(
    path: Path, ffmpeg: str, *, output_path: Path | None = None
) -> bool:
    """Refine an already bounded square image; preserve it on optional failure.

    ``output_path`` is useful to callers that keep a lossless source image and
    want to write the refined JPEG separately.  The historical default still
    replaces ``path`` in place, so existing adapter/test callers retain their
    behaviour.
    """
    return await _remove_embedded_bars(path, ffmpeg, output_path=output_path)


async def _remove_embedded_bars(
    path: Path, ffmpeg: str, *, output_path: Path | None = None
) -> bool:
    """Implementation shared by the compatibility wrapper and full converter."""
    process = None
    destination = output_path or path
    candidate = destination.with_name(f".{destination.stem}.refined.jpg")
    try:
        async with asyncio.timeout(4):
            process = await asyncio.create_subprocess_exec(
                ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
                "-i", str(path), "-vf", "scale=64:64:flags=area", "-frames:v", "1",
                "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            preview, _ = await process.communicate()
            if process.returncode != 0:
                return False
            inset = embedded_bar_inset(preview)
            if not inset:
                return False
            # Both dimensions shrink equally: removing horizontal black bands
            # also removes the colored side padding around a square album image.
            scale = (64 - 2*inset) / 64
            process = await asyncio.create_subprocess_exec(
                ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
                "-i", str(path), "-vf", f"crop=iw*{scale}:ih*{scale},setsar=1",
                "-frames:v", "1", *JPEG_QUALITY_ARGS, "-fs", "1048576",
                "-update", "1", "-y", str(candidate),
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            if await process.wait() != 0 or not candidate.is_file():
                return False
            if not 0 < candidate.stat().st_size <= MAX_ARTWORK_BYTES:
                return False
            candidate.replace(destination)
            return True
    except (OSError, TimeoutError):
        return False
    finally:
        if process and process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                process.kill()
            await process.wait()
        with contextlib.suppress(OSError):
            candidate.unlink(missing_ok=True)


async def prepare_square_artwork(
    source: str | Path,
    output: Path,
    ffmpeg: str,
) -> bool:
    """Create one high-quality, bounded 1:1 JPEG from ``source``.

    ``source`` may be a local path or a URL understood by FFmpeg.  The first
    conversion is lossless PNG; only the final output is JPEG-encoded.  This
    avoids the old two-JPEG pipeline (initial conversion, then border refine),
    which was the main avoidable source of soft artwork.  Any optional
    detection/conversion failure leaves an existing output untouched and
    returns ``False``.
    """
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    work = output.with_name(f".{output.stem}.source.png")
    refined = output.with_name(f".{output.stem}.refined.jpg")
    process: asyncio.subprocess.Process | None = None

    async def run(argv: list[str], timeout: float) -> int:
        nonlocal process
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            return await asyncio.wait_for(process.wait(), timeout)
        finally:
            if process.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    process.kill()
                await process.wait()
            process = None

    try:
        # Keep the network timeout explicit and make the work file lossless.
        code = await run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
            "-rw_timeout", "5000000", "-i", str(source), "-an",
            "-frames:v", "1", "-vf", SQUARE_COVER_FILTER,
            "-f", "image2", "-y", str(work),
        ], ARTWORK_FETCH_TIMEOUT)
        if code != 0 or not work.is_file() or not 0 < work.stat().st_size <= WORKING_IMAGE_MAX_BYTES:
            return False

        # Refined writes a JPEG directly from the lossless source.  If the
        # conservative bar heuristic does not match, make the ordinary JPEG
        # once below.
        if await _remove_embedded_bars(work, ffmpeg, output_path=refined):
            refined.replace(output)
            return True

        code = await run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
            "-i", str(work), "-frames:v", "1", *JPEG_QUALITY_ARGS,
            "-fs", str(MAX_ARTWORK_BYTES), "-update", "1", "-y", str(refined),
        ], 5)
        if code != 0 or not refined.is_file() or not 0 < refined.stat().st_size <= MAX_ARTWORK_BYTES:
            return False
        refined.replace(output)
        return True
    except (OSError, TimeoutError):
        return False
    finally:
        if process and process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                process.kill()
            await process.wait()
        for temporary in (work, refined):
            with contextlib.suppress(OSError):
                temporary.unlink(missing_ok=True)
