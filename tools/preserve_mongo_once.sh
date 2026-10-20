#!/usr/bin/env bash
# One operator-approved physical copy. Never deploys, restarts or deletes source data.
set -Eeuo pipefail
umask 077
DATA_PATH=/data/db
COORD=/tmp/ibiag-preserve-active
WORK=''
OWNED=0
DONE=0
PHASE=TARGET
LAST_STATUS=0

fail() { printf 'PRESERVATION_NOT_CONFIRMED phase=%s code=%s\n' "$PHASE" "$LAST_STATUS" >&2; exit 2; }
[[ ${1:-} == --approved-one-off ]] || fail
[[ ${RAILWAY_PROJECT_ID:-} == c1a9635c-789b-4e42-ac9b-cca4326fab9a && ${RAILWAY_ENVIRONMENT_ID:-} == fcab95f8-3e30-4da9-8e0b-d9b7f94747ce && ${RAILWAY_SERVICE_ID:-} == 9cc0395c-7601-451b-a6fa-1511ab168158 ]] || fail
PHASE=TOOLS
for tool in mongosh cp du tar gzip sha256sum timeout flock nohup mktemp df stat find; do command -v "$tool" >/dev/null || fail; done
PHASE=SOURCE
[[ -d $DATA_PATH && ! -L $DATA_PATH && -f $DATA_PATH/WiredTiger ]] || fail
[[ -z $(find "$DATA_PATH" -type l -print -quit) ]] || fail
# Bound source to 2GiB apparent bytes; reserve staging + archive + 512MiB.
# Host-wide free space is a capacity check, never the database size.
PHASE=SPACE
AVAILABLE=$(df -Pk /tmp | awk 'NR==2 {print $4}')
SOURCE_SIZE=$(du -sb "$DATA_PATH" | awk '{print $1}')
[[ $SOURCE_SIZE =~ ^[0-9]+$ && $SOURCE_SIZE -gt 0 && $SOURCE_SIZE -le 2147483648 ]] || fail
REQUIRED_KB=$(( (SOURCE_SIZE + 1023) / 1024 + 2097152 + 524288 ))
[[ $AVAILABLE =~ ^[0-9]+$ && $AVAILABLE -ge $REQUIRED_KB ]] || fail
export MONGOSH_DISABLE_TELEMETRY=1
mongo_check() { timeout --signal=TERM --kill-after=5s 20s mongosh --quiet --norc --eval "(async()=>{$1})().catch(()=>quit(2));" </dev/null 2>/dev/null; }
# Refuse sharding/replica sets, custom dbpaths, encryption and an existing fsync lock.
PREFLIGHT='const a=db.getSiblingDB("admin"); const h=await a.runCommand({hello:1}); const c=await a.runCommand({getCmdLineOpts:1}); const s=await a.runCommand({serverStatus:1}); const p=c.parsed||{}; const o=await a.runCommand({currentOp:1}); if(h.ok!==1||c.ok!==1||s.ok!==1||o.ok!==1||h.setName||h.msg==="isdbgrid"||!(await db.version()).startsWith("8.")||(p.storage?.dbPath&&p.storage.dbPath!=="/data/db")||p.security?.enableEncryption||p.security?.kmip||o.fsyncLock||s.storageEngine?.name!=="wiredTiger")quit(2); print("PREFLIGHT_OK");'
PHASE=PREFLIGHT
[[ $(mongo_check "$PREFLIGHT") == PREFLIGHT_OK ]] || fail
# Atomic marker prevents concurrent copies by this helper, including uncertain cleanup.
PHASE=COORDINATION
mkdir -m 700 "$COORD" 2>/dev/null || fail
OWNED=1
WORK=$(mktemp -d /tmp/ibiag-preserve-XXXXXXXX)
TOKEN=${WORK##*/}
printf '%s' "$TOKEN" > "$COORD/owner"
cat > "$COORD/release.sh" <<'RELEASE'
#!/usr/bin/env bash
set -u
umask 077
COORD=/tmp/ibiag-preserve-active
EXPECTED_TOKEN=${1:-}
[[ -n $EXPECTED_TOKEN && -f $COORD/owner && $(cat "$COORD/owner") == "$EXPECTED_TOKEN" ]] || exit 2
export MONGOSH_DISABLE_TELEMETRY=1
exec 9>"$COORD/release.mutex" || exit 2
flock -w 30 9 || exit 2
[[ -f $COORD/owner && $(cat "$COORD/owner") == "$EXPECTED_TOKEN" ]] || exit 2
[[ -f $COORD/armed ]] || exit 0
STATUS_JS='const s=await db.getSiblingDB("admin").runCommand({currentOp:1});if(s.ok!==1)quit(2);print(s.fsyncLock?"LOCK_STATUS_LOCKED":"LOCK_STATUS_UNLOCKED");'
# A confirmed owned lock MUST be decremented. Shell helper currentOp() results
# are not proof of release. Only the server fsyncUnlock response count0 is.
if [[ ! -f $COORD/lock-confirmed || -e $COORD/unlock-attempt ]]; then
 STATUS=$(timeout --signal=TERM --kill-after=5s 20s mongosh --quiet --norc --eval "(async()=>{$STATUS_JS})().catch(()=>quit(2));" </dev/null 2>/dev/null) || exit 2
 if [[ $STATUS == LOCK_STATUS_UNLOCKED ]]; then rm -f "$COORD/armed"; exit 0; fi
 [[ $STATUS == LOCK_STATUS_LOCKED ]] || exit 2
fi
[[ ! -e $COORD/unlock-attempt ]] || exit 2
# Never retry an uncertain decrement: that could release another operator's lock.
(set -C; : > "$COORD/unlock-attempt") || exit 2
JS='const a=db.getSiblingDB("admin");const r=await a.runCommand({fsyncUnlock:1});if(r.ok!==1||Number(r.lockCount)!==0)quit(2); print("UNLOCKED");'
RESULT=$(timeout --signal=TERM --kill-after=5s 20s mongosh --quiet --norc --eval "(async()=>{$JS})().catch(()=>quit(2));" </dev/null 2>/dev/null) || exit 2
[[ $RESULT == UNLOCKED ]] || exit 2
rm -f "$COORD/armed"
exit 0
RELEASE
chmod 600 "$COORD/release.sh"
cleanup() {
  local status=$?
  trap - EXIT INT TERM HUP
  if [[ $OWNED == 1 ]]; then
    if ! bash "$COORD/release.sh" "$TOKEN"; then
      printf '%s\n' 'MANUAL_UNLOCK_REQUIRED: run the reviewed release command before any other operation.' >&2
      exit 3
    fi
    rm -f "$COORD/release.sh" "$COORD/release.mutex" "$COORD/expired" "$COORD/owner" "$COORD/unlock-attempt" "$COORD/lock-confirmed"
    rmdir "$COORD" 2>/dev/null || true
  fi
  if [[ -n $WORK ]]; then rm -rf -- "$WORK/snapshot"; fi
  if [[ $DONE != 1 && -n $WORK ]]; then rm -f "$WORK/data.tar.gz.partial" "$WORK/data.tar.gz"; rmdir "$WORK" 2>/dev/null || true; fi
  if [[ $DONE != 1 ]]; then printf 'PRESERVATION_NOT_CONFIRMED phase=%s cleanup=returned\n' "$PHASE" >&2; fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 2' INT TERM HUP
# Detached deadline guard survives ordinary parent/SSH disconnection. Not a scheduler.
# Marker stays present on failed unlock, refusing a new copy and requiring operator recovery.
touch "$COORD/armed"
nohup bash -c 'sleep 150; d=/tmp/ibiag-preserve-active; if [[ -f $d/owner && $(cat "$d/owner") == "$1" && -f $d/armed ]]; then touch "$d/expired"; bash "$d/release.sh" "$1"; fi' ibiag-watchdog "$TOKEN" </dev/null >/dev/null 2>&1 &
LOCK='const a=db.getSiblingDB("admin");const s=await a.runCommand({currentOp:1});if(s.ok!==1)quit(2);if(s.fsyncLock){print("PREEXISTING_LOCK");quit(0);}const r=await a.runCommand({fsync:1,lock:true,fsyncLockAcquisitionTimeoutMillis:15000});if(r.ok!==1)quit(2);print("OWNED_LOCK_"+Number(r.lockCount));'
PHASE=LOCK
LOCK_RESULT=$(mongo_check "$LOCK") || fail
if [[ $LOCK_RESULT == PREEXISTING_LOCK ]]; then rm -f "$COORD/armed"; fail; fi
[[ $LOCK_RESULT =~ ^OWNED_LOCK_[1-9][0-9]*$ ]] || fail
touch "$COORD/lock-confirmed"
[[ $LOCK_RESULT == OWNED_LOCK_1 ]] || fail
# MongoDB documents cp under fsyncLock as safe despite physical journal/checkpoint
# changes. Stage all files while locked; tar reads only that static copy AFTER unlock.
PHASE=COPY
mkdir -m 700 "$WORK/snapshot"
(ulimit -f 2097152; timeout --signal=TERM --kill-after=5s 80s cp -a --reflink=never --sparse=always "$DATA_PATH/." "$WORK/snapshot/") </dev/null 2>/dev/null || { LAST_STATUS=$?; fail; }
[[ ! -e $COORD/expired ]] || fail
PHASE=UNLOCK
bash "$COORD/release.sh" "$TOKEN" || fail
PHASE=ARCHIVE
(ulimit -f 2097152; timeout --signal=TERM --kill-after=5s 110s tar -czf "$WORK/data.tar.gz.partial" -C "$WORK/snapshot" .) </dev/null 2>/dev/null || { LAST_STATUS=$?; fail; }
# Validate only after returning the database to writers. Never print archive contents.
PHASE=INTEGRITY
gzip -t "$WORK/data.tar.gz.partial" 2>/dev/null || fail
tar -tzf "$WORK/data.tar.gz.partial" >/dev/null 2>&1 || fail
PHASE=MANIFEST
SIZE=$(stat -c %s "$WORK/data.tar.gz.partial")
[[ $SIZE -gt 0 && $SIZE -le 2147483648 ]] || fail
DIGEST=$(sha256sum "$WORK/data.tar.gz.partial"); DIGEST=${DIGEST%% *}
mv "$WORK/data.tar.gz.partial" "$WORK/data.tar.gz"
chmod 600 "$WORK/data.tar.gz"
DONE=1
printf '{"copy_created":true,"writes_unlocked":true,"restoration_proven":false,"archive":"%s/data.tar.gz","bytes":%s,"sha256":"%s"}\n' "$WORK" "$SIZE" "$DIGEST"
# Windows PowerShell appends CRLF when piping a raw string. Exit before that
# trailing blank line can be interpreted by bash as a stray carriage-return.
exit 0
