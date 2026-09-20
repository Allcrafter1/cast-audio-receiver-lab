#!/system/bin/sh
# Independent emergency restore, using monotonic uptime rather than altered wall time.
# Arguments: initial epoch, initial uptime seconds, original auto_time, timeout.
clock_epoch="$1"
clock_uptime="$2"
clock_auto="$3"
clock_timeout="$4"
sleep "$clock_timeout"
clock_now_uptime=$(cut -d. -f1 /proc/uptime)
clock_restored=$((clock_epoch + clock_now_uptime - clock_uptime))
date -u "@$clock_restored"
settings put global auto_time "$clock_auto"
if [ "$6" = "1" ]; then svc wifi enable; elif [ "$6" = "0" ]; then svc wifi disable; fi
if [ "$7" = "1" ]; then svc data enable; elif [ "$7" = "0" ]; then svc data disable; fi
if [ -n "$5" ] && [ -f "$5" ]; then
  am force-stop com.softmedia.receiver
  if [ -f /data/user/0/com.softmedia.receiver/app_cast/config.json ]; then
    mv /data/user/0/com.softmedia.receiver/app_cast/config.json "$5.generated"
  fi
  mv "$5" /data/user/0/com.softmedia.receiver/app_cast/config.json
fi
if [ -n "$8" ] && [ -f "$8" ]; then
  am force-stop com.softmedia.receiver
  mv /data/user/0/com.softmedia.receiver/shared_prefs/SoftMediaPairedData.xml "$8.generated"
  mv "$8" /data/user/0/com.softmedia.receiver/shared_prefs/SoftMediaPairedData.xml
fi
