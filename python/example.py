# -*- coding: utf-8 -*-
"""
example.py —— libzuiyou 全功能示例

把 SDK 目前实现的**每一个**能力都跑一遍，并打印结果摘要。
默认只跑只读接口；写操作（点赞/收藏/关注）需要显式设置环境变量才会执行。

运行:
    export ZUIYOU_TOKEN='<your-token>'
    export ZUIYOU_MID='123456789'
    python3 example.py

    # 想试写操作（会真的点赞/收藏，慎用）:
    ZUIYOU_ALLOW_WRITE=1 python3 example.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zuiyou import Zuiyou, ZuiyouError

ALLOW_WRITE = os.environ.get("ZUIYOU_ALLOW_WRITE") == "1"
SLEEP = 0.9          # 服务端限流，建议 ≥0.9s
STATS = []


def load_token():
    tok = os.environ.get("ZUIYOU_TOKEN")
    mid = os.environ.get("ZUIYOU_MID")
    if tok and mid:
        return tok, int(mid)
    # 也可以放在 ~/.zuiyou_token，格式：token=xxx / mid=yyy
    p = os.path.expanduser("~/.zuiyou_token")
    if os.path.exists(p):
        txt = open(p, encoding="utf-8").read()
        if "token=" in txt:
            t = txt.split("token=")[1].split()[0]
            m = txt.split("mid=")[1].split()[0] if "mid=" in txt else "0"
            return t, int(m)
        return txt.strip(), int(os.environ.get("ZUIYOU_MID", "0"))
    return None, None


def section(title):
    print("\n" + "=" * 62)
    print(" " + title)
    print("=" * 62)


def call(name, fn, show=None, expect_ok=True):
    """执行一次调用并打印摘要。show(json) 返回要额外打印的字符串。"""
    t0 = time.time()
    try:
        r = fn()
    except ZuiyouError as e:
        print("  %-22s ERROR %s" % (name, e))
        STATS.append((name, "ERR", 0))
        return None
    dt = time.time() - t0
    ret = r.get("ret")
    ok = (ret == 1)
    STATS.append((name, ret, dt))
    mark = "OK " if ok else ".. "
    line = "  %s%-22s ret=%-5s %.2fs" % (mark, name, ret, dt)
    if show:
        try:
            extra = show(r)
            if extra:
                line += "  " + extra
        except Exception:
            pass
    if not ok and r.get("msg"):
        line += "  msg=" + str(r["msg"])[:40]
    print(line)
    time.sleep(SLEEP)
    return r


def data_of(r):
    return (r or {}).get("data") or {}


def main():
    token, mid = load_token()
    if not token or not mid:
        print("请先设置 ZUIYOU_TOKEN 和 ZUIYOU_MID")
        return 2

    # ------------------------------------------------------------------
    section("0. 初始化")
    zy = Zuiyou(token=token, mid=mid)
    print("  libzuiyou %s" % zy.version)
    print("  selftest = %d  (0 = 内置密码学自检通过)" % zy.selftest())
    print("  token = %s… (%d chars), mid = %d" % (token[:12], len(token), mid))

    # ------------------------------------------------------------------
    section("1. 聊天")

    sessions = call("chat_sessions", lambda: zy.chat_sessions(count=5),
                    lambda r: "会话 %d 个" % len(data_of(r).get("sessions") or []))

    ss = data_of(sessions).get("sessions") or []
    sid = ss[0]["session_id"] if ss else 0
    peer = ss[0].get("mid", 0) if ss else 0

    if sid:
        print("      ↳ 取第一个会话 sid=%s  peer=%s  %s" % (
            sid, peer, (ss[0].get("name") or "")[:20]))

        msgs = call("chat_messages", lambda: zy.chat_messages(sid, limit=5),
                    lambda r: "消息 %d 条" % len(data_of(r).get("messages") or []))

        # 拿到 msgid 才能演示已读
        ml = data_of(msgs).get("messages") or []
        if ml:
            last = ml[-1]
            call("chat_read", lambda: zy.chat_read(sid, last["msgid"]),
                 lambda r: "msgid=%s" % last["msgid"])

        # 下面几个会改变状态，默认不跑
        if ALLOW_WRITE:
            sr = call("chat_say", lambda: zy.chat_say(sid, peer, "SDK 示例消息", 1),
                      lambda r: "msgid=%s" % data_of(r).get("msgid"))
            new_msgid = data_of(sr).get("msgid")
            if new_msgid:
                call("chat_recall", lambda: zy.chat_recall(sid, new_msgid))
            call("chat_top_session", lambda: zy.chat_top_session(sid, True))
            call("chat_top_session(off)", lambda: zy.chat_top_session(sid, False))
        else:
            print("  -- chat_say / chat_recall / chat_hide_session / chat_top_session"
                  "  需要 ZUIYOU_ALLOW_WRITE=1")

    # ------------------------------------------------------------------
    section("2. 内容")

    sp = call("search_post", lambda: zy.search_post("笑话"),
              lambda r: "帖子 %d 条" % len(data_of(r).get("list") or []))
    plist = data_of(sp).get("list") or []
    pid = (plist[0].get("id") or plist[0].get("_id")) if plist else 0
    tid = plist[0].get("tid") if plist else 0

    if pid:
        print("      ↳ 取第一条 pid=%s tid=%s" % (pid, tid))
        call("post_detail", lambda: zy.post_detail(pid),
             lambda r: "正文 %d 字 / 热评 %d 条" % (
                 len(str(data_of(r).get("post", {}).get("content") or "")),
                 len(data_of(r).get("hotreviews") or [])))
        call("post_reviews", lambda: zy.post_reviews(pid),
             lambda r: "评论 %d 条" % len(data_of(r).get("list") or []))

    if tid:
        call("topic_detail", lambda: zy.topic_detail(tid),
             lambda r: "话题: %s" % str(data_of(r).get("topic", {}).get("topic") or "")[:20])
        call("topic_posts", lambda: zy.topic_posts(tid),
             lambda r: "帖子 %d 条" % len(data_of(r).get("list") or []))

    call("follow_feed", lambda: zy.follow_feed(),
         lambda r: "关注流 %d 条" % len(data_of(r).get("list") or []))
    call("video_feed", lambda: zy.video_feed(),
         lambda r: "视频 %d 条" % len(data_of(r).get("list") or []))
    call("video_favor_folders", lambda: zy.video_favor_folders(),
         lambda r: "收藏夹 %d 个" % len(data_of(r).get("list") or []))
    call("parse_share_text", lambda: zy.parse_share_text("https://share.izuiyou.com/test"),
         lambda r: "keys=%s" % list(data_of(r).keys())[:4])
    call("feed_recommend", lambda: zy.feed_recommend(5),
         lambda r: "（该接口已知不可用，见 README）")

    # ------------------------------------------------------------------
    section("3. 搜索")

    call("search_user", lambda: zy.search_user("小"),
         lambda r: "用户 %d 个" % len(data_of(r).get("list") or []))
    call("search_video", lambda: zy.search_video("猫"),
         lambda r: "视频 %d 条" % len(data_of(r).get("list") or []))

    # ------------------------------------------------------------------
    section("4. 用户")

    call("my_profile", lambda: zy.my_profile(),
         lambda r: "昵称: %s" % str(data_of(r).get("member_info", {}).get("name") or "")[:16])
    call("user_profile", lambda: zy.user_profile(mid),
         lambda r: "粉丝 %s" % data_of(r).get("member_info", {}).get("fans"))
    call("user_profile_v2", lambda: zy.user_profile_v2(mid),
         lambda r: "keys=%s" % list(data_of(r).keys())[:3])
    call("user_posts", lambda: zy.user_posts(mid),
         lambda r: "帖子 %d 条" % len(data_of(r).get("list") or []))

    # ------------------------------------------------------------------
    section("5. 写操作（参数已确认，默认不执行）")

    if ALLOW_WRITE and pid:
        print("  ZUIYOU_ALLOW_WRITE=1，开始执行写操作（会留痕）")
        call("post_like", lambda: zy.post_like(pid))
        call("post_unlike", lambda: zy.post_unlike(pid))
        call("favorite", lambda: zy.favorite(pid))
        call("attention", lambda: zy.attention(mid, pid, True))
        call("attention(off)", lambda: zy.attention(mid, pid, False))
    else:
        for name, sig, note in [
            ("post_like", "zy.post_like(pid, like_type=1)", "点赞"),
            ("post_unlike", "zy.post_unlike(pid)", "取消点赞"),
            ("review_like", "zy.review_like(pid, rid, status=1)", "评论点赞"),
            ("favorite", "zy.favorite(pid, fid=0)", "收藏"),
            ("attention", "zy.attention(uid, pid, follow=True)", "关注/取关"),
        ]:
            print("  -- %-12s %-38s %s" % (name, sig, note))
        print("     设 ZUIYOU_ALLOW_WRITE=1 可真的执行")

    # ------------------------------------------------------------------
    section("6. 通用调用")

    # 通用调用：自己拼 payload 调未封装的接口
    print("  call(path,json) / call_ex(path,json,flags) / call_auth(path,**fields)")
    print("  path 传目标路径、payload 传 JSON；用法见 docs/API.md")

    # ------------------------------------------------------------------
    section("7. 汇总")
    ok = sum(1 for _, r, _ in STATS if r == 1)
    bad = [(n, r) for n, r, _ in STATS if r != 1]
    total_t = sum(t for _, _, t in STATS)
    print("  调用 %d 次，ret=1 共 %d 次，总耗时 %.1fs" % (len(STATS), ok, total_t))
    if bad:
        print("  非 1 的:")
        for n, r in bad:
            print("    %-22s ret=%s" % (n, r))

    zy.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
