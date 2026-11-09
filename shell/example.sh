#!/bin/sh
# ---------------------------------------------------------------------------
# example.sh —— libzuiyou 的 Shell 用法示例
#
# 覆盖 zy.sh 的主要命令。跑之前先设好 token：
#   export ZUIYOU_TOKEN='<your-token>'
#   export ZUIYOU_MID='123456789'
#   ./example.sh
# ---------------------------------------------------------------------------
set -e

HERE=$(cd "$(dirname "$0")" && pwd)
ZY="$HERE/zy.sh"

: "${ZUIYOU_TOKEN:?请先 export ZUIYOU_TOKEN}"
: "${ZUIYOU_MID:?请先 export ZUIYOU_MID}"

hr() { echo; echo "───── $* ─────"; }

# ---------------------------------------------------------------------------
hr "0. 自检与版本"
"$ZY" version
"$ZY" selftest

# ---------------------------------------------------------------------------
hr "1. 聊天"
# 会话列表，用 python 提取 sid / 昵称 / 最后一条
"$ZY" sessions 3 | python3 -c '
import json,sys
d=json.load(sys.stdin)
for s in (d.get("data") or {}).get("sessions", []):
    print("  sid=%-20s %-16s %s" % (
        s.get("session_id"),
        (s.get("name") or "")[:14],
        str((s.get("message") or {}).get("content"))[:28]))
'

SID=$("$ZY" sessions 1 | python3 -c '
import json,sys
d=json.load(sys.stdin)
ss=(d.get("data") or {}).get("sessions") or []
print(ss[0]["session_id"] if ss else "")
')

if [ -n "$SID" ]; then
    echo "  第一个会话 sid=$SID，拉 3 条历史："
    "$ZY" messages "$SID" 3 | python3 -c '
import json,sys
d=json.load(sys.stdin)
for m in (d.get("data") or {}).get("messages", []):
    print("    [%s] %s" % (m.get("mtype"), str(m.get("content"))[:50]))
'
fi

# ---------------------------------------------------------------------------
hr "3. 搜索 → 内容"
"$ZY" search-post 笑话 2>/dev/null | python3 -c '
import json,sys
d=json.load(sys.stdin)
lst=(d.get("data") or {}).get("list") or []
print("  搜到 %d 条帖子，前 3 条：" % len(lst))
for p in lst[:3]:
    print("    pid=%-12s tid=%-8s %s" % (p.get("id"), p.get("tid"),
          str(p.get("content"))[:36].replace("\n"," ")))
if lst:
    open("/tmp/_zy_pid","w").write(str(lst[0].get("id")))
    open("/tmp/_zy_tid","w").write(str(lst[0].get("tid") or ""))
'

PID=$(cat /tmp/_zy_pid 2>/dev/null || echo "")
TID=$(cat /tmp/_zy_tid 2>/dev/null || echo "")

if [ -n "$PID" ]; then
    hr "4. 帖子详情 pid=$PID"
    "$ZY" post "$PID" | python3 -c '
import json,sys
d=json.load(sys.stdin); dd=d.get("data") or {}
p=dd.get("post") or {}
print("  ret       =", d.get("ret"))
print("  正文      =", str(p.get("content"))[:60].replace("\n"," "))
print("  点赞/评论 =", p.get("likes"), "/", p.get("reviews"))
print("  热评      =", len(dd.get("hotreviews") or []), "条")
'
    echo "  评论列表（前 2 条）："
    "$ZY" reviews "$PID" | python3 -c '
import json,sys
d=json.load(sys.stdin)
for r in ((d.get("data") or {}).get("list") or [])[:2]:
    print("    rid=%-12s %s" % (r.get("id"), str(r.get("review"))[:40]))
'
fi

if [ -n "$TID" ]; then
    hr "5. 话题 tid=$TID"
    "$ZY" topic "$TID" | python3 -c '
import json,sys
d=json.load(sys.stdin); t=(d.get("data") or {}).get("topic") or {}
print("  话题 =", t.get("topic"))
print("  帖子 =", t.get("posts"), " 关注 =", t.get("atts"))
'
    "$ZY" topic-posts "$TID" | python3 -c '
import json,sys
d=json.load(sys.stdin)
print("  话题下帖子:", len((d.get("data") or {}).get("list") or []), "条")
'
fi

# ---------------------------------------------------------------------------
hr "6. 信息流"
for c in follow video videofav; do
    printf "  %-10s " "$c"
    "$ZY" "$c" | python3 -c '
import json,sys
d=json.load(sys.stdin); dd=d.get("data") or {}
n=len(dd.get("list") or [])
print("ret=%s items=%d" % (d.get("ret"), n))
'
    sleep 1
done

# ---------------------------------------------------------------------------
hr "7. 用户"
"$ZY" me | python3 -c '
import json,sys
d=json.load(sys.stdin); m=(d.get("data") or {}).get("member_info") or {}
print("  我: %s (mid=%s) 关注=%s 粉丝=%s" % (m.get("name"), m.get("id"), m.get("atts"), m.get("fans")))
'
sleep 1
"$ZY" posts "$ZUIYOU_MID" | python3 -c '
import json,sys
d=json.load(sys.stdin)
print("  我的帖子:", len((d.get("data") or {}).get("list") or []), "条")
'

# ---------------------------------------------------------------------------
hr "8. 搜索用户 / 视频"
"$ZY" search-user 小 | python3 -c '
import json,sys
d=json.load(sys.stdin)
for u in ((d.get("data") or {}).get("list") or [])[:3]:
    print("    mid=%-10s %s" % (u.get("id"), u.get("name")))
'
sleep 1
printf "  search-video: "
"$ZY" search-video 猫 | python3 -c '
import json,sys
d=json.load(sys.stdin)
print("ret=%s items=%d" % (d.get("ret"), len((d.get("data") or {}).get("list") or [])))
'

# ---------------------------------------------------------------------------
hr "9. 写操作（示例，默认注释）"
cat <<'TIP'
  这些会真的改变服务端状态，需要时手动取消注释：

    "$ZY" like   <pid>
    "$ZY" unlike <pid>
    "$ZY" fav    <pid>
    "$ZY" follow-user   <uid>
    "$ZY" unfollow-user <uid>
    "$ZY" review-like <pid> <rid> 1
    "$ZY" say <sid> <to_mid> "内容"
    "$ZY" recall <sid> <msgid>

  发帖/评论字段较多，可用通用调用自己拼 payload：
    "$ZY" call <path> '<json>'
  字段说明见 docs/API.md
TIP

# ---------------------------------------------------------------------------
hr "10. 一键跑遍只读接口"
"$ZY" tour

# ---------------------------------------------------------------------------
hr "完成"
rm -f /tmp/_zy_pid /tmp/_zy_tid
