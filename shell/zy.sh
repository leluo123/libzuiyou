#!/bin/sh
# ---------------------------------------------------------------------------
# zy.sh —— 在 shell 里调用 libzuiyou（通过 python3 ctypes，无第三方依赖）
#
# 准备:
#   export ZUIYOU_TOKEN='<your-token>'
#   export ZUIYOU_MID='123456789'
#
# 命令:
#   ---- 基础 ----
#   selftest                      库内自检（0=正常）
#   version                       版本
#
#   ---- 聊天 ----
#   sessions [count] [msgid_begin]        会话列表
#   messages <sid> [limit]                历史消息
#   say <sid> <to_mid> <text>             发消息
#   read <sid> <msgid>                    标记已读
#   recall <sid> <msgid>                  撤回
#   hide <sid> [last_msgid]               删除会话
#   top <sid> [on|off]                    置顶
#
#   ---- 内容 ----
#   post <pid>                    帖子详情+评论
#   reviews <pid> [offset]        评论列表
#   topic <tid>                   话题详情
#   topic-posts <tid> [offset]    话题帖子流
#   follow [offset]               关注流
#   video [offset]                短视频流
#   videofav                      视频收藏夹
#   share <text>                  解析分享口令
#   recommend [limit]             推荐流（已知不可用）
#
#   ---- 搜索 ----
#   search-post <q> [offset]
#   search-user <q> [offset]
#   search-video <q>
#
#   ---- 用户 ----
#   me                            本人资料
#   profile <mid>                 用户主页
#   profile2 <uid>                轻量主页
#   posts <mid>                   用户帖子
#
#   ---- 设备 / 授权 / 合规 ----
#   device                        本机设备指纹（拿这串去换授权码）
#   activate <code>               输入授权码解锁私信
#   guard                         环境检测（clean=未发现调试器）
#   check <text>                  内容合规检查（0=通过）
#   auth                          查看当前授权（本地缓存）
#   comment <pid> <text> [rid]    发评论 / 回复评论
#
#   ---- 表情包 ----
#   emoji-packages                表情包列表
#   emoji-list [package_id]       表情列表（不传取全部）
#   face <sid> <to_mid> <face_id> [fmt] [w] [h]   发表情/图片（mtype=2）
#
#   ---- 写操作（会改变状态）----
#   like <pid>                    点赞
#   unlike <pid>                  取消点赞
#   fav <pid> [fid]               收藏
#   follow-user <uid> [pid]       关注
#   unfollow-user <uid> [pid]     取关
#   review-like <pid> <rid> [0|1] 点赞评论
#
#   ---- 通用 ----
#   call <path> [json]            带 token/h_m 调任意接口
#   raw <path> [json]             原样发送
#   tour                          只读接口跑一遍
# ---------------------------------------------------------------------------
set -e

HERE=$(cd "$(dirname "$0")" && pwd)
PYDIR="$HERE/../python"
[ -f "$PYDIR/zuiyou.py" ] || PYDIR="$HERE"

exec env ZY_PYDIR="$PYDIR" python3 - "$@" <<'PYEOF'
import json, os, sys, ctypes

here = os.environ.get("ZY_PYDIR") or os.getcwd()
sys.path.insert(0, here)
try:
    from zuiyou import Zuiyou, ZuiyouError
except ImportError:
    sys.path.insert(0, os.path.join(here, "..", "python"))
    from zuiyou import Zuiyou, ZuiyouError

args = sys.argv[1:]
if not args:
    print(__doc__ or "用法: zy.sh <command> [...]")
    sys.exit(2)

cmd = args[0]
rest = args[1:]


def need_env():
    tok = os.environ.get("ZUIYOU_TOKEN")
    mid = os.environ.get("ZUIYOU_MID")
    if not tok or not mid:
        print("请先设置 ZUIYOU_TOKEN 和 ZUIYOU_MID", file=sys.stderr)
        sys.exit(3)
    return tok, int(mid)


def arg(i, default=None, cast=str):
    if i < len(rest) and rest[i] != "":
        return cast(rest[i])
    if default is None:
        print("参数不足", file=sys.stderr)
        sys.exit(2)
    return default


def dump(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def brief(r, key):
    d = (r or {}).get("data") or {}
    lst = d.get(key) if isinstance(d, dict) else None
    return "ret=%s items=%s" % ((r or {}).get("ret"), len(lst) if isinstance(lst, list) else "-")


try:
    # ---------- 不需要登录 ----------
    if cmd == "version":
        from zuiyou import load_library
        print("libzuiyou", load_library().zy_version().decode())
        sys.exit(0)

    if cmd == "selftest":
        from zuiyou import load_library
        print("selftest =", load_library().zy_selftest(), "(0=通过)")
        sys.exit(0)

    # ---- 不需要登录的设备信息 ----
    if cmd == "device":
        from zuiyou import load_library
        lib = load_library()
        lib.zy_device_id.restype = ctypes.c_char_p
        print(lib.zy_device_id().decode())
        sys.exit(0)

    if cmd == "guard":
        from zuiyou import load_library
        lib = load_library()
        lib.zy_guard_status.restype = ctypes.c_char_p
        print(lib.zy_guard_status().decode())
        sys.exit(0)

    if cmd == "check":
        from zuiyou import load_library
        lib = load_library()
        lib.zy_content_check.argtypes = [ctypes.c_char_p]
        lib.zy_content_check.restype = ctypes.c_int
        lib.zy_content_reason.argtypes = [ctypes.c_int]
        lib.zy_content_reason.restype = ctypes.c_char_p
        code = lib.zy_content_check(arg(0, "").encode("utf-8"))
        print("code=%d reason=%s" % (code, lib.zy_content_reason(code).decode()))
        sys.exit(0)

    tok, mid = need_env()
    zy = Zuiyou(token=tok, mid=mid)

    # ---- 授权 ----
    if cmd == "activate":
        rc = zy.activate(arg(0, ""))
        print("activate = %d  %s" % (rc, "成功，已解锁私信" if rc == 0 else "授权码无效"))
        print("perms    = %d (1=评论 3=评论+私信)" % zy.auth_perms())
        sys.exit(0 if rc == 0 else 1)

    if cmd == "auth":
        if rest and rest[0] == "refresh":
            print("refresh =", zy.auth_refresh(), zy.auth_error())
        print("device  = %s" % zy.device_id())
        print("perms   = %d (1=评论 2=私信 3=都有)" % zy.auth_perms())
        print("chat    = %s  comment = %s" % (zy.can_chat(), zy.can_comment()))
        print("expire  = %s" % (zy.auth_expire() or "长期"))
        sys.exit(0)

    if cmd == "comment":
        dump(zy.comment_create(arg(0, cast=int), arg(1), arg(2, 0, int)))
        sys.exit(0)

    # ---- 表情包 ----
    if cmd == "emoji-packages":
        dump(zy.emoji_packages())
        sys.exit(0)

    if cmd == "emoji-list":
        dump(zy.emoji_list(arg(0, 0, int)))
        sys.exit(0)

    if cmd == "face":
        dump(zy.send_face(arg(0, cast=int), arg(1, cast=int), arg(2, cast=int),
                          arg(3, "gif"), arg(4, 200, int), arg(5, 200, int)))
        sys.exit(0)

    # ---------- 基础 ----------
    if cmd == "sign":
        print(zy.sign(arg(0, "")))
    elif cmd == "encrypt":
        print(zy.encrypt(arg(0), arg(1)))
    elif cmd == "decrypt":
        print(zy.decrypt(arg(0), arg(1)))
    elif cmd == "cat":
        print(zy.make_cat(rest[0] if rest else None))

    # ---------- 聊天 ----------
    elif cmd == "sessions":
        dump(zy.chat_sessions(msgid_begin=arg(1, 0, int), count=arg(0, 20, int)))
    elif cmd == "messages":
        dump(zy.chat_messages(arg(0, cast=int), limit=arg(1, 30, int)))
    elif cmd == "say":
        dump(zy.chat_say(arg(0, cast=int), arg(1, cast=int), arg(2), 1))
    elif cmd == "read":
        dump(zy.chat_read(arg(0, cast=int), arg(1, cast=int)))
    elif cmd == "recall":
        dump(zy.chat_recall(arg(0, cast=int), arg(1, cast=int)))
    elif cmd == "hide":
        dump(zy.chat_hide_session(arg(0, cast=int), arg(1, 0, int)))
    elif cmd == "top":
        dump(zy.chat_top_session(arg(0, cast=int), arg(1, "on") != "off"))

    # ---------- 内容 ----------
    elif cmd == "post":
        dump(zy.post_detail(arg(0, cast=int)))
    elif cmd == "reviews":
        dump(zy.post_reviews(arg(0, cast=int), arg(1, 0, int)))
    elif cmd == "topic":
        dump(zy.topic_detail(arg(0, cast=int)))
    elif cmd == "topic-posts":
        dump(zy.topic_posts(arg(0, cast=int), arg(1, 0, int)))
    elif cmd == "follow":
        dump(zy.follow_feed(arg(0, 0, int)))
    elif cmd == "video":
        dump(zy.video_feed(arg(0, 0, int)))
    elif cmd == "videofav":
        dump(zy.video_favor_folders())
    elif cmd == "share":
        dump(zy.parse_share_text(arg(0)))
    elif cmd == "recommend":
        dump(zy.feed_recommend(arg(0, 20, int)))

    # ---------- 搜索 ----------
    elif cmd == "search-post":
        dump(zy.search_post(arg(0), arg(1, 0, int)))
    elif cmd == "search-user":
        dump(zy.search_user(arg(0), arg(1, 0, int)))
    elif cmd == "search-video":
        dump(zy.search_video(arg(0)))

    # ---------- 用户 ----------
    elif cmd == "me":
        dump(zy.my_profile())
    elif cmd == "profile":
        dump(zy.user_profile(arg(0, mid, int)))
    elif cmd == "profile2":
        dump(zy.user_profile_v2(arg(0, mid, int)))
    elif cmd == "posts":
        dump(zy.user_posts(arg(0, mid, int)))

    # ---------- 写操作 ----------
    elif cmd == "like":
        dump(zy.post_like(arg(0, cast=int)))
    elif cmd == "unlike":
        dump(zy.post_unlike(arg(0, cast=int)))
    elif cmd == "fav":
        dump(zy.favorite(arg(0, cast=int), arg(1, 0, int)))
    elif cmd == "follow-user":
        dump(zy.attention(arg(0, cast=int), arg(1, 0, int), True))
    elif cmd == "unfollow-user":
        dump(zy.attention(arg(0, cast=int), arg(1, 0, int), False))
    elif cmd == "review-like":
        dump(zy.review_like(arg(0, cast=int), arg(1, cast=int), arg(2, 1, int)))

    # ---------- 通用 ----------
    elif cmd in ("call", "raw"):
        payload = json.loads(rest[1]) if len(rest) > 1 else {}
        if cmd == "call":
            dump(zy.call_auth(rest[0], **payload))
        else:
            dump(zy.call(rest[0], payload))

    elif cmd == "tour":
        steps = [
            ("sessions", lambda: zy.chat_sessions(count=3), "sessions"),
            ("my_profile", lambda: zy.my_profile(), None),
            ("user_profile", lambda: zy.user_profile(mid), None),
            ("user_profile_v2", lambda: zy.user_profile_v2(mid), None),
            ("user_posts", lambda: zy.user_posts(mid), "list"),
            ("follow_feed", lambda: zy.follow_feed(), "list"),
            ("video_feed", lambda: zy.video_feed(), "list"),
            ("video_favor_folders", lambda: zy.video_favor_folders(), "list"),
            ("search_post", lambda: zy.search_post("笑话"), "list"),
            ("search_user", lambda: zy.search_user("小"), "list"),
            ("search_video", lambda: zy.search_video("猫"), "list"),
            ("parse_share_text", lambda: zy.parse_share_text("test"), None),
        ]
        ok = 0
        pid = tid = None
        for name, fn, key in steps:
            try:
                r = fn()
                ret = r.get("ret")
                ok += 1 if ret == 1 else 0
                extra = ""
                d = r.get("data") or {}
                if key and isinstance(d.get(key), list):
                    extra = "items=%d" % len(d[key])
                print("  %-22s ret=%-4s %s" % (name, ret, extra))
                if name == "search_post" and isinstance(d.get("list"), list) and d["list"]:
                    pid = d["list"][0].get("id") or d["list"][0].get("_id")
                    tid = d["list"][0].get("tid")
            except ZuiyouError as e:
                print("  %-22s ERR %s" % (name, e))
            import time as _t; _t.sleep(0.9)

        if pid:
            for name, fn in [("post_detail", lambda: zy.post_detail(pid)),
                             ("post_reviews", lambda: zy.post_reviews(pid))]:
                try:
                    r = fn(); ok += 1 if r.get("ret") == 1 else 0
                    print("  %-22s ret=%s" % (name, r.get("ret")))
                except ZuiyouError as e:
                    print("  %-22s ERR %s" % (name, e))
                import time as _t; _t.sleep(0.9)
        if tid:
            for name, fn in [("topic_detail", lambda: zy.topic_detail(tid)),
                             ("topic_posts", lambda: zy.topic_posts(tid))]:
                try:
                    r = fn(); ok += 1 if r.get("ret") == 1 else 0
                    print("  %-22s ret=%s" % (name, r.get("ret")))
                except ZuiyouError as e:
                    print("  %-22s ERR %s" % (name, e))
                import time as _t; _t.sleep(0.9)

        total = len(steps) + (2 if pid else 0) + (2 if tid else 0)
        print("\n  tour: ret=1 %d/%d" % (ok, total))

    else:
        print("未知命令: %s" % cmd, file=sys.stderr)
        sys.exit(2)

    zy.close()
except ZuiyouError as e:
    print("ERROR: %s" % e, file=sys.stderr)
    sys.exit(1)
except IndexError:
    print("参数不足", file=sys.stderr)
    sys.exit(2)
PYEOF
