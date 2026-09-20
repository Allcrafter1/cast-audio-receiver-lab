# Historical Python receiver

This directory preserves the first standalone Python Cast and YouTube DIAL /
Lounge receiver experiments.  They are useful protocol research and could be a
fallback starting point if the current Vibecast frontend becomes unusable, but
they are **not** part of the supported runtime and are deliberately excluded
from the normal wheel.

The current product path is:

```text
Vibecast/Rust frontend -> versioned player bridge -> Python output adapter
```

The historical code can still be tested from a source checkout:

```bash
PYTHONPATH=src:. python -m unittest \
  tests.test_auth tests.test_lounge tests.test_mdns tests.test_protocol \
  tests.test_server tests.test_youtube_dial
```

Running it manually requires explicitly opting into the research package:

```bash
PYTHONPATH=src:. python -m \
  research.legacy_python_receiver.legacy_cast_receiver.server --help
```

It has no compatibility or security-support promise.  In particular, the
prototype's authentication extension points do not make it a stock-compatible
Cast receiver by themselves.

