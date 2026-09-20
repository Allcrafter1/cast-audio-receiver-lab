# HA status and speaker UI — 0.6.0.dev3

## Evidence and scope

The correct live frontend log is `.state/airreceiver-a50/linux-receiver.log`.
At 2026-09-13 17:28:44 UTC it records LAUNCH `CC1AD845` followed by
`app_key=default_media`. This confirms an actual DMR session in the user's HA
test period. Earlier inspection of `.state/vibecast-live.log` was insufficient.
It does not establish that every subsequent radio/file request used that app.

User clarification: stale HA PLAYING was observed mainly after ending YouTube
Music casting. SWR3 and a local file are the metadata/control test cases; their
end-status behavior has not been confirmed faulty.

## Terminal state correction

DeviceHub.stop_session removed the session and its subscriptions without a final
MEDIA_STATUS. Any later player IDLE report was ignored because the session no
longer existed. A monitoring client could retain the preceding PLAYING status.
The shared teardown now publishes IDLE/CANCELLED before removing subscriptions.
Actual connection loss also broadcasts the refreshed receiver application list.
This applies to app teardown, including YouTube; ordinary media EOF is separate.

New in-memory Cast regression starts app-driven playback, sends receiver STOP,
and checks terminal MEDIA_STATUS followed by the empty receiver app list and a
player Stop command. It fails on the previous source (RECEIVER_STATUS arrives
first without terminal media) and passes after the fix. All26 core tests pass.
Real HA/YouTube acceptance remains a user test after deployment.

LOAD diagnostics record only field presence, image count, stream type, session ID
and presence of duration; no source URL, title text, token or artwork URL is logged.
These will distinguish missing sender metadata from dropped receiver data for
SWR3/local files. Shared metadata currently lacks artist/album fields; no schema
or radio-pause behavior change is claimed in this iteration.

Artwork inspection: YouTube resolver selects the thumbnail with maximum width.
AirPlay uses `scale=512:512:force_original_aspect_ratio=decrease` without padding;
that conversion does not add bars. Borders may already be in source thumbnails
or be added by the destination UI. Do not blindly crop legitimate cover content;
inspect representative source images before choosing normalization semantics.

## UI

DELETE removes a route after stopping its owned task and deletes only the matching
generated target JSON. Other speakers remain intact. Historical private logs and
backups are retained. The UI asks for confirmation before deletion.
New duplicate local mpv routes are rejected by both HTTP creation and CLI import.
Existing configurations still load, allowing earlier duplicates to be deleted
deliberately rather than silently removing user state.
Add-local is disabled when a local route already exists. Added an SVG favicon;
configuration changes from other browsers are refreshed when no route is being
edited. Authentication remains absent; LAN address and port are unchanged.

121 Python tests pass, including deletion/persistence/private target cleanup and
local duplicate/recreate behavior. Live Chromium verifies all existing routes,
delete buttons, disabled local-add, API duplicate rejection, favicon and reload.
It does not delete any user's live route.

## Source and rollback

Rust candidate built in `.state/dmr-1/clean-source`, based on reconstructed0.5.0
plus the already-tested first-start installation-ID fix. The dev3 snapshot patch
is cumulative ONLY for core hub.rs/tests.rs against upstream; it is not a complete
build source and must not be stacked blindly on the complete0.5.0 patch.
Python deployment is `.state/manager-dev3-src`; prior dev2 tree retained.
Manager config backup: `.state/speaker-manager/routes.before-dev3.json`.
