# Capability matrix: compact v3 observations

25 profiles; 50/50 app/profile observations completed in this source snapshot.
Each app/profile used a fresh UUID/name suffix and separate receiver data directory. The two app columns do not share one receiver identity. Previously paired/shared-identity behavior remains a separate test.
API config/source is configuration plus shared-client source evidence, not a TLS wire capture. Selected means a row tap was attempted. LAUNCH and silent LOAD do not verify audible playback. — means unmeasured; greyed/unselectable rows are not capability failures. UNKNOWN icons need visual review. No hybrid conclusion is inferred.

| Profile | mDNS ca | DEVICE_INFO ca | Eureka display | API display (config/source) | YouTube: icon; selected; LAUNCH; LOAD | Music: icon; selected; LAUNCH; LOAD |
| --- | ---: | ---: | --- | --- | --- | --- |
| speaker | 199428 | 199428 | false | false | not seen; selected no; LAUNCH —; LOAD — | Speaker; selected yes; LAUNCH 2DB7CC49; LOAD 1 |
| video-eureka-off | 199429 | 199429 | false | false | TV; selected yes; LAUNCH 233637DE; LOAD 1 | TV; selected yes; LAUNCH 2DB7CC49; LOAD 1 |
| video-eureka-on | 199429 | 199429 | true | false | TV; selected yes; LAUNCH 233637DE; LOAD 1 | TV; selected yes; LAUNCH 2DB7CC49; LOAD 1 |
| video-mdns-only | 199429 | 199428 | false | false | not seen; selected no; LAUNCH —; LOAD — | TV; greyed/unselectable; selected no; LAUNCH —; LOAD — |
| video-info-only | 199428 | 199429 | false | false | TV; selected yes; LAUNCH 233637DE; LOAD 1 | Speaker; selected yes; LAUNCH 2DB7CC49; LOAD 1 |
| speaker-eureka-on | 199428 | 199428 | true | false | not seen; selected no; LAUNCH —; LOAD — | Speaker; selected yes; LAUNCH 2DB7CC49; LOAD 1 |
| speaker-nest-model | 199428 | 199428 | false | false | not seen; selected no; LAUNCH —; LOAD — | Speaker; greyed/unselectable; selected no; LAUNCH —; LOAD — |
| video-nest-model | 199429 | 199429 | false | false | TV; selected yes; LAUNCH 233637DE; LOAD 1 | TV; greyed/unselectable; selected no; LAUNCH —; LOAD — |
| video-dynamic-group | 199493 | 199493 | false | false | Generic Cast; selected yes; LAUNCH 233637DE; LOAD 1 | Generic Cast; selected yes; LAUNCH 2DB7CC49; LOAD 1 |
| video-speaker-pair | 199557 | 199557 | false | false | TV; selected yes; LAUNCH 233637DE; LOAD 1 | TV; selected yes; LAUNCH 2DB7CC49; LOAD 1 |
| minimal-speaker | 4 | 4 | false | false | not seen; selected no; LAUNCH —; LOAD — | Speaker; greyed/unselectable; selected no; LAUNCH —; LOAD — |
| minimal-video-audio | 5 | 5 | false | false | TV; greyed/unselectable; selected no; LAUNCH —; LOAD — | TV; greyed/unselectable; selected no; LAUNCH —; LOAD — |
| no-output-diagnostic | 199424 | 199424 | false | false | Generic Cast; selected yes; LAUNCH 233637DE; LOAD 1 | Generic Cast; selected yes; LAUNCH 2DB7CC49; LOAD 1 |
| video-static-group | 199461 | 199461 | false | false | Generic Cast; selected yes; LAUNCH 233637DE; LOAD 1 | Generic Cast; selected yes; LAUNCH 2DB7CC49; LOAD 1 |
| video-no-audio | 199425 | 199425 | false | false | Generic Cast; selected yes; LAUNCH 233637DE; LOAD 1 | Generic Cast; selected yes; LAUNCH 2DB7CC49; LOAD 1 |
| video-mdns-only-eureka-on | 199429 | 199428 | true | false | TV; selected yes; LAUNCH 233637DE; LOAD 1 | TV; selected yes; LAUNCH 2DB7CC49; LOAD 1 |
| video-info-only-eureka-on | 199428 | 199429 | true | false | Speaker; selected yes; LAUNCH none; LOAD 0 | Speaker; selected yes; LAUNCH 2DB7CC49; LOAD 1 |
| speaker-api-on | 199428 | 199428 | false | true | not seen; selected no; LAUNCH —; LOAD — | Speaker; greyed/unselectable; selected no; LAUNCH —; LOAD — |
| video-eureka-off-api-on | 199429 | 199429 | false | true | TV; selected yes; LAUNCH 233637DE; LOAD 1 | TV; greyed/unselectable; selected no; LAUNCH —; LOAD — |
| video-eureka-on-api-on | 199429 | 199429 | true | true | TV; selected yes; LAUNCH 233637DE; LOAD 1 | TV; greyed/unselectable; selected no; LAUNCH —; LOAD — |
| video-mdns-only-api-on | 199429 | 199428 | false | true | TV; selected yes; LAUNCH 233637DE; LOAD 1 | TV; selected yes; LAUNCH 2DB7CC49; LOAD 1 |
| video-info-only-api-on | 199428 | 199429 | false | true | Speaker; selected yes; LAUNCH none; LOAD 0 | TV; selected yes; LAUNCH 2DB7CC49; LOAD 1 |
| speaker-eureka-on-api-on | 199428 | 199428 | true | true | not seen; selected no; LAUNCH —; LOAD — | Speaker; greyed/unselectable; selected no; LAUNCH —; LOAD — |
| video-mdns-only-eureka-on-api-on | 199429 | 199428 | true | true | TV; selected yes; LAUNCH 233637DE; LOAD 1 | TV; greyed/unselectable; selected no; LAUNCH —; LOAD — |
| video-info-only-eureka-on-api-on | 199428 | 199429 | true | true | Speaker; selected yes; LAUNCH none; LOAD 0 | Speaker; greyed/unselectable; selected no; LAUNCH —; LOAD — |

LOAD is a command received by the silent bridge. Fresh receiver queues, Music MAIN and paused YouTube mean missing LOAD alone assigns no failure cause. All planned app/profile observations are complete.
