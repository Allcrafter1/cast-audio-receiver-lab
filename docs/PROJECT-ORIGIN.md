# Project origin, experimental status and contributions

This project began with a practical goal: receive YouTube Music casting on Linux
and forward audio to independently chosen outputs, initially AirPlay receivers.

The initiator had practically no prior programming experience. Much of the
development was carried out collaboratively with AI coding assistants, including
GPT/Astra. Requirements, architecture and observed behavior were discussed
together; implementation was iterated through automated tests and extensive
hands-on playback tests on the initiator's devices.

That process is not a substitute for an independent code or security review.
Successful tests on a few devices do not establish compatibility with all Cast
senders, AirPlay receivers or future service versions. Please treat this as
experimental software: try it, inspect it, report reproducible problems and keep
a way to return to a known-working release. Some upstream service/authentication
changes may require substantial rework or make a mechanism unusable.

Contributions and experienced reviews are explicitly welcome, especially around
protocol correctness, safe lifecycle handling, reproducible builds, packaging,
network security, device compatibility and resource use. Please do not include
private authentication material, account tokens or signed media URLs in issues,
logs, pull requests or test fixtures.

We intend to publish as open source with the applicable license notices. This
document is a publication draft, not an announcement that a public repository or
reviewed release already exists. Third-party code retains its own licenses.

## Relationship to Music Assistant

Music Assistant's AirPlay sender is an important upstream component. This project
is not an official Music Assistant integration or an endorsed project. We do not
intend to merge this experimental receiver directly into Music Assistant.
Experienced developers are welcome to review, improve or adapt the work into a
suitable integration, subject to the applicable licenses.

Any community announcement will wait until a usable, documented public repository
exists. No announcement should imply support or endorsement from upstream teams.

## Attribution gate before publication

Prepare a verified attribution inventory from the sources actually used: Vibecast,
Shanocast, Music Assistant airplay-cli and its incorporated libraries, FFmpeg,
mpv, yt-dlp and its extraction dependencies, and the Python libraries we ship.
Document AirReceiver's role as the reference implementation used in device tests.
Include individual researchers and research articles only where the development
record establishes their contribution to this work; verify names and links.

Credit is not permission to redistribute third-party private material. Complete
the dependency/license and repository-history audit before publishing code or
artifacts. Preserve copyright/license notices and distinguish implementation reuse,
research inspiration and comparison testing.
