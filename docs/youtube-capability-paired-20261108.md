# Paired-app observations on one lab receiver per run

Run labels A, B, … are anonymous report labels. Actual order is the measurement order within the indicated round; planned order is used only for missing-row placement.
Round 1 is the first app-order sequence on that run's receiver. Round 2 repeats the sequence on that same receiver/data directory; it has no fresh receiver queue. Fresh app-process reselection is not a verified disconnect/reconnect or an audible playback test.
Pair identity refers to the driver's stable pointer/UUID/process/label checks plus matching measurement markers. Clicked route extras were not verified. possibleDifferentIcon is calculated only for two observed, known icons on the verified same instance in the same round. Presence includes selectable picker rows and an already-connected controller. A UUID-matched visual/XML review can correct a missed controller or classify a picker icon whose crop is unsuitable for hash matching; raw listed is retained. The comparison includes greyed rows and connected controllers and is an observation flag, never a working-hybrid claim. Unknown/missing icons produce —.

| Run | Profile | Round / actual order | App | Presence / context | Icon / contrast | Selected | LAUNCH IDs | LOAD | Pair identity | Teardown / error stage | possibleDifferentIcon |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- |
| A | video-info-only | 1 / 1 | music | yes / picker-row (visual/XML review; raw listed=yes) | speaker / 208 | yes | 2DB7CC49 | 1 | yes | yes / — | yes |
| A | video-info-only | 1 / 2 | youtube | yes / picker-row (visual/XML review; raw listed=yes) | tv / 240 | yes | 233637DE | 1 | yes | yes / — | yes |
| A | video-info-only | 2 / 1 | music | yes / connected-controller (visual/XML review; raw listed=yes) | tv / 208 | no | — | — | yes | yes / — | no |
| A | video-info-only | 2 / 2 | youtube | yes / picker-row (visual/XML review; raw listed=yes) | tv / 240 | yes | none | 1 | yes | yes / — | no |
| B | speaker | 1 / 1 | youtube | no / not-present | not_listed / — | no | — | — | yes | yes / — | — |
| B | speaker | 1 / 2 | music | yes / picker-row | speaker / 208 | yes | 2DB7CC49 | 1 | yes | yes / — | — |
| B | speaker | 2 / 1 | youtube | no / not-present | not_listed / — | no | — | — | yes | yes / — | — |
| B | speaker | 2 / 2 | music | no / not-present | not_listed / — | no | — | — | yes | yes / — | — |
| C | video-eureka-on-api-on | 1 / 1 | youtube | yes / picker-row | tv / 240 | yes | 233637DE | 1 | yes | yes / — | no |
| C | video-eureka-on-api-on | 1 / 2 | music | yes / picker-row | tv / 208 | yes | 2DB7CC49 | 1 | yes | yes / — | no |
| C | video-eureka-on-api-on | 2 / 1 | youtube | yes / picker-row | tv / 240 | yes | 233637DE | 1 | yes | yes / — | — |
| C | video-eureka-on-api-on | 2 / 2 | music | no / not-present | not_listed / — | no | — | — | yes | yes / — | — |
| D | video-info-only | 1 / 1 | youtube | yes / picker-row | speaker / 240 | yes | none | 0 | yes | yes / — | yes |
| D | video-info-only | 1 / 2 | music | yes / picker-row | tv / 208 | yes | 2DB7CC49 | 1 | yes | yes / — | yes |
| D | video-info-only | 2 / 1 | youtube | yes / picker-row | speaker / 240 | yes | none | 0 | yes | yes / — | no |
| D | video-info-only | 2 / 2 | music | yes / connected-controller (visual/XML review; raw listed=no) | speaker / — | no | — | — | yes | yes / — | no |

Selected is derived from selected_at and means a tap was attempted. LAUNCH IDs are restricted to the two known YouTube/Music app IDs. LOAD is nullable: greyed or absent rows were not selected, and missing LOAD alone assigns no capability-failure cause. An already-connected controller is observed without a new selection; its LAUNCH and LOAD remain unmeasured. A silent bridge LOAD confirms neither media fetch/decoding nor sound. No paired success is claimed.
