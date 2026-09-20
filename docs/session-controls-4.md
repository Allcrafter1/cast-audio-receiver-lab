# Controls-4 deployment notes

The sender logs show both phone TCP connections closing at 19:43:35 while
session 715911fe continued issuing media loads at 19:45 and 19:48. No matching
player stop appeared. Existing cleanup tracked application subscriptions only.

Experimental policy: record the connection that issued LAUNCH as the session
owner. Closing this connection stops the session and clears ownership even if
other subscriptions remain. This intentionally makes the receiver stop when
its launching sender leaves; it is not a general multi-controller Cast policy.
LAUNCH already replaces existing sessions. Whether this resolves the second
phone's connection failure still requires a real two-phone test.

On Next, Lounge now announces BUFFERING at zero instead of copying the old
track's state. While awaiting the new player load, old position reports are
ignored. BUFFERING, ERROR or CANCELLED releases this gate so a failed load does
not leave the report gate stuck indefinitely.

Do not claim live success from the build alone. Verify a mid-track Next, switch
to This Device, then launch from a second phone. Check for a player stop and a
new session ID. Signed media URLs and authentication material are not included
in these notes.
