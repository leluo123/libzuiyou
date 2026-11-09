# -*- coding: utf-8 -*-
"""全量回归：把 SDK 封装的每个函数真实调一遍，输出 ret 汇总。"""
import os, sys, json, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zuiyou import Zuiyou

TOK = os.environ.get("ZUIYOU_TOKEN")
if not TOK:
    p = os.path.expanduser("~/.zuiyou_token")
    if os.path.exists(p):
        txt = open(p, encoding="utf-8").read()
        TOK = txt.split("token=")[1].split()[0] if "token=" in txt else txt.strip()
MID = int(os.environ.get("ZUIYOU_MID") or 0)

zy = Zuiyou(token=TOK, mid=MID)
rows = []

def run(name, fn):
    t0 = time.time()
    try:
        r = fn()
        ret = r.get("ret") if isinstance(r, dict) else None
        d = r.get("data") if isinstance(r, dict) else None
        n = None
        if isinstance(d, dict):
            for k in ("sessions", "messages", "list", "posts", "topics", "hotreviews", "reviews"):
                if isinstance(d.get(k), list):
                    n = len(d[k]); break
        rows.append((name, ret, n, "%.2fs" % (time.time() - t0)))
        return r
    except Exception as e:
        rows.append((name, "EXC", str(e)[:40], "%.2fs" % (time.time() - t0)))
        return None

# 聊天
s = run("chat_sessions", lambda: zy.chat_sessions(count=5))
sid = None
if s and (s.get("data") or {}).get("sessions"):
    sid = s["data"]["sessions"][0]["session_id"]
if sid:
    run("chat_messages", lambda: zy.chat_messages(sid, limit=5))

# 账号 / 用户
run("my_profile", lambda: zy.my_profile())
run("user_profile", lambda: zy.user_profile(MID))
run("user_posts", lambda: zy.user_posts(MID))
run("search_user", lambda: zy.search_user("小"))

# 内容
sp = run("search_post", lambda: zy.search_post("笑话"))
pid = None
if sp and (sp.get("data") or {}).get("list"):
    pid = sp["data"]["list"][0].get("id") or sp["data"]["list"][0].get("_id")
if pid:
    print("  -> pid =", pid)
    run("post_detail", lambda: zy.post_detail(pid))
    run("post_reviews", lambda: zy.post_reviews(pid))

run("follow_feed", lambda: zy.follow_feed())
run("video_feed", lambda: zy.video_feed())
run("search_video", lambda: zy.search_video("猫"))
run("video_favor_folders", lambda: zy.video_favor_folders())
run("user_profile_v2", lambda: zy.user_profile_v2(MID))
run("parse_share_text", lambda: zy.parse_share_text("https://share.izuiyou.com/test"))

print("\n%-16s %-6s %-8s %s" % ("function", "ret", "items", "time"))
print("-" * 44)
ok = 0
for name, ret, n, t in rows:
    print("%-16s %-6s %-8s %s" % (name, ret, n if n is not None else "-", t))
    if ret == 1:
        ok += 1
print("-" * 44)
print("ret=1: %d / %d" % (ok, len(rows)))
zy.close()
