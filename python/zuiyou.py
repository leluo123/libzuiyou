# -*- coding: utf-8 -*-
"""
libzuiyou 的 Python 封装（ctypes，零第三方依赖）

用法:
    from zuiyou import Zuiyou
    zy = Zuiyou(token="...", mid=123456789)
    print(zy.chat_sessions(count=5))
    print(zy.chat_say(session_id=0, to_mid=12345, content="hi"))

.so 位置:
    默认在同级 ../lib/<平台>/libzuiyou.so，可用 lib_path= 或环境变量 ZUIYOU_LIB 覆盖。

内存: 所有返回的字符串由 .so malloc，封装层读取后立即 zy_free。
"""

import ctypes
import json
import os
import platform
import sys

__all__ = ["Zuiyou", "ZuiyouError", "load_library"]


class ZuiyouError(Exception):
    """协议/网络/业务层失败。"""


def _default_lib_path():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    machine = platform.machine().lower()
    system = platform.system().lower()

    if "android" in sys.platform or os.environ.get("PREFIX", "").find("com.termux") >= 0:
        cand = [os.path.join(root, "lib", "android-arm64", "libzuiyou.so")]
    elif system == "linux":
        if machine in ("aarch64", "arm64"):
            cand = [os.path.join(root, "lib", "linux-aarch64", "libzuiyou.so")]
        else:
            cand = [os.path.join(root, "lib", "linux-x86_64", "libzuiyou.so")]
    elif system == "darwin":
        cand = [os.path.join(root, "lib", "macos-arm64", "libzuiyou.dylib"),
                os.path.join(root, "lib", "macos-x86_64", "libzuiyou.dylib")]
    elif system == "windows":
        cand = [os.path.join(root, "lib", "windows-x86_64", "libzuiyou.dll")]
    else:
        cand = []

    cand.append(os.path.join(root, "lib", "libzuiyou.so"))
    for p in cand:
        if os.path.exists(p):
            return p
    return cand[0] if cand else "libzuiyou.so"


def load_library(path=None):
    """加载 .so 并声明所有函数签名。"""
    path = path or os.environ.get("ZUIYOU_LIB") or _default_lib_path()
    if not os.path.exists(path):
        raise ZuiyouError(
            "找不到 libzuiyou: %s\n"
            "请设置 ZUIYOU_LIB 或把 .so 放到 lib/<平台>/ 下。\n"
            "当前平台: %s %s" % (path, platform.system(), platform.machine())
        )
    lib = ctypes.CDLL(path)

    c_char_p = ctypes.c_char_p
    c_int = ctypes.c_int
    c_longlong = ctypes.c_longlong
    c_void_p = ctypes.c_void_p

    sigs = {
        "zy_version": (c_char_p, []),
        "zy_selftest": (ctypes.c_int, []),
        "zy_init": (c_int, [c_char_p]),
        "zy_shutdown": (None, []),
        "zy_last_error": (c_char_p, []),
        "zy_free": (None, [c_void_p]),
        "zy_call": (c_void_p, [c_char_p, c_char_p]),
        "zy_call_ex": (c_void_p, [c_char_p, c_char_p, c_int]),
        "zy_call_auth": (c_void_p, [c_char_p, c_char_p]),
        "zy_sign": (c_void_p, [c_char_p, c_int]),
        "zy_encrypt": (c_void_p, [c_char_p, c_char_p]),
        "zy_decrypt": (c_void_p, [c_char_p, c_char_p]),
        "zy_make_cat": (c_void_p, [c_char_p]),
        "zy_chat_sessions": (c_void_p, [c_longlong, c_int]),
        "zy_chat_messages": (c_void_p, [c_longlong, c_longlong, c_int]),
        "zy_chat_say": (c_void_p, [c_longlong, c_longlong, c_char_p, c_int]),
        "zy_chat_send_face": (c_void_p, [c_longlong, c_longlong, c_longlong, c_char_p, c_int, c_int]),
        "zy_chat_read": (c_void_p, [c_longlong, c_longlong]),
        "zy_chat_recall": (c_void_p, [c_longlong, c_longlong]),
        "zy_chat_hide_session": (c_void_p, [c_longlong, c_longlong]),
        "zy_chat_top_session": (c_void_p, [c_longlong, c_int]),
        "zy_account_info": (c_void_p, []),
        "zy_user_profile": (c_void_p, [c_longlong]),
        "zy_feed_recommend": (c_void_p, [c_int]),
        "zy_post_detail": (c_void_p, [c_longlong]),
        "zy_post_reviews": (c_void_p, [c_longlong, c_int]),
        "zy_topic_detail": (c_void_p, [c_longlong]),
        "zy_topic_posts": (c_void_p, [c_longlong, c_int]),
        "zy_search_post": (c_void_p, [c_char_p, c_int]),
        "zy_search_user": (c_void_p, [c_char_p, c_int]),
        "zy_user_posts": (c_void_p, [c_longlong]),
        "zy_my_profile": (c_void_p, []),
        "zy_follow_feed": (c_void_p, [c_int]),
        "zy_video_feed": (c_void_p, [c_int]),
        "zy_parse_share_text": (c_void_p, [c_char_p]),
        "zy_topic_posts_list": (c_void_p, [c_longlong, c_int]),
        "zy_user_profile_v2": (c_void_p, [c_longlong]),
        "zy_search_video": (c_void_p, [c_char_p]),
        "zy_video_favor_folders": (c_void_p, []),
        "zy_post_like": (c_void_p, [c_longlong, c_int]),
        "zy_post_unlike": (c_void_p, [c_longlong]),
        "zy_review_like": (c_void_p, [c_longlong, c_longlong, c_int]),
        "zy_favorite": (c_void_p, [c_longlong, c_longlong]),
        "zy_attention": (c_void_p, [c_longlong, c_longlong, c_int]),
        # ---- 设备 / 授权 / 合规 ----
        "zy_device_id": (c_char_p, []),
        "zy_activate": (c_int, [c_char_p]),
        "zy_auth_refresh_now": (c_int, []),
        "zy_auth_perms": (c_int, []),
        "zy_auth_expire": (c_longlong, []),
        "zy_auth_err": (c_char_p, []),
        "zy_guard_status": (c_char_p, []),
        "zy_content_check": (c_int, [c_char_p]),
        "zy_content_reason": (c_char_p, [c_int]),
        "zy_comment_create": (c_void_p, [c_longlong, c_char_p, c_longlong]),
        # ---- 表情包 ----
        "zy_emoji_packages": (c_void_p, []),
        "zy_emoji_list": (c_void_p, [c_longlong]),
    }
    for name, (restype, argtypes) in sigs.items():
        fn = getattr(lib, name, None)
        if fn is None:
            raise ZuiyouError("库缺少符号 %s（版本不匹配？）" % name)
        fn.restype = restype
        fn.argtypes = argtypes
    return lib


class Zuiyou(object):
    """最右 API 客户端。"""

    #: 通用调用标志
    NO_TICKET = 1
    NO_RETRY = 2

    def __init__(self, token=None, mid=None, lib_path=None, host=None,
                 did=None, timeout=25, auto_init=True):
        self.lib = load_library(lib_path)
        self.token = token
        self.mid = mid
        self.host = host
        self.did = did
        self.timeout = timeout
        if auto_init and token and mid:
            self.init()

    # ---------- 生命周期 ----------
    def init(self):
        cfg = {"token": self.token, "mid": int(self.mid), "timeout": self.timeout}
        if self.host:
            cfg["host"] = self.host
        if self.did:
            cfg["did"] = self.did
        rc = self.lib.zy_init(json.dumps(cfg).encode("utf-8"))
        if rc != 0:
            raise ZuiyouError("初始化失败 (%d): %s" % (rc, self.last_error()))
        return self

    def close(self):
        self.lib.zy_shutdown()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @property
    def version(self):
        v = self.lib.zy_version()
        return v.decode("utf-8") if v else "?"

    def selftest(self):
        """库内自检，返回 0 表示通过。"""
        return self.lib.zy_selftest()

    def last_error(self):
        e = self.lib.zy_last_error()
        return e.decode("utf-8", "replace") if e else ""

    # ---------- 内部：指针 -> str ----------
    def _take(self, ptr):
        if not ptr:
            err = self.last_error()
            raise ZuiyouError(err or "调用失败（无错误信息）")
        try:
            raw = ctypes.string_at(ptr)
        finally:
            self.lib.zy_free(ptr)
        return raw.decode("utf-8", "replace")

    def _json(self, ptr):
        text = self._take(ptr)
        try:
            return json.loads(text)
        except ValueError:
            return {"_raw": text}

    # ---------- 设备 / 授权 / 合规 ----------

    def device_id(self):
        """本机设备指纹（32 hex），授权时把这串交给管理员。"""
        v = self.lib.zy_device_id()
        return v.decode("utf-8") if v else ""

    def activate(self, code):
        """输入授权码（XXXX-XXXX-XXXX-XXXX）解锁私信。返回 0 成功。"""
        return self.lib.zy_activate(code.encode("utf-8"))

    def auth_refresh(self):
        """重新读一次本地授权缓存（不联网），返回 0。"""
        return self.lib.zy_auth_refresh_now()

    def auth_perms(self):
        """当前权限位：1=仅评论，2=私信，3=都有。"""
        return self.lib.zy_auth_perms()

    def auth_expire(self):
        """授权过期时间戳，0 表示长期。"""
        return self.lib.zy_auth_expire()

    def auth_error(self):
        e = self.lib.zy_auth_err()
        return e.decode("utf-8", "replace") if e else ""

    def can_chat(self):
        return bool(self.auth_perms() & 2)

    def can_comment(self):
        return bool(self.auth_perms() & 1)

    def guard_status(self):
        """环境检测：'clean' 表示未发现调试器。"""
        v = self.lib.zy_guard_status()
        return v.decode("utf-8", "replace") if v else ""

    def content_check(self, text):
        """内容合规检查，返回 0 表示通过。"""
        return self.lib.zy_content_check(text.encode("utf-8"))

    def content_reason(self, code):
        v = self.lib.zy_content_reason(int(code))
        return v.decode("utf-8", "replace") if v else ""

    def comment_create(self, pid, content, rid=0):
        """发评论 / 回复评论。rid=0 是主评论。"""
        return self._json(self.lib.zy_comment_create(int(pid), content.encode("utf-8"), int(rid)))

    # ---------- 表情包 ----------

    def emoji_packages(self):
        """表情包列表（id / name / icon）。"""
        return self._json(self.lib.zy_emoji_packages())

    def emoji_list(self, package_id=0):
        """表情列表；package_id<=0 时取全部。"""
        return self._json(self.lib.zy_emoji_list(int(package_id)))

    def send_face(self, session_id, to_mid, face_id, fmt="gif", w=200, h=200):
        """发表情/图片（mtype=2）。face_id 是图片 ID（custom_face.face_id）。

        需要 CHAT 权限（未激活返回 ret=-1001）。
        """
        return self._json(self.lib.zy_chat_send_face(
            int(session_id), int(to_mid), int(face_id),
            fmt.encode("utf-8"), int(w), int(h)))

    # ---------- 通用 ----------
    def call(self, path, payload=None, flags=0):
        """调任意接口。payload 可为 dict / JSON 字符串 / None。"""
        if payload is None:
            body = b"{}"
        elif isinstance(payload, (dict, list)):
            body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        elif isinstance(payload, bytes):
            body = payload
        else:
            body = str(payload).encode("utf-8")
        if flags:
            ptr = self.lib.zy_call_ex(path.encode("utf-8"), body, flags)
        else:
            ptr = self.lib.zy_call(path.encode("utf-8"), body)
        return self._json(ptr)

    def call_auth(self, path, **fields):
        """带 token/h_m 地调任意接口，fields 是额外顶层字段。"""
        # C 端期望的是「字段片段」（不带外层大括号）
        extra = json.dumps(fields, separators=(",", ":"), ensure_ascii=False)[1:-1] if fields else ""
        ptr = self.lib.zy_call_auth(path.encode("utf-8"), extra.encode("utf-8"))
        return self._json(ptr)

    def sign(self, body):
        if isinstance(body, str):
            body = body.encode("utf-8")
        return self._take(self.lib.zy_sign(body, len(body)))

    def encrypt(self, plain, key_hex):
        if isinstance(plain, str):
            plain = plain.encode("utf-8")
        return self._take(self.lib.zy_encrypt(plain, key_hex.encode()))

    def decrypt(self, cipher_hex, key_hex):
        return self._take(self.lib.zy_decrypt(cipher_hex.encode(), key_hex.encode()))

    def make_cat(self, key_hex=None):
        return self._take(self.lib.zy_make_cat(key_hex.encode() if key_hex else None))

    # ---------- 聊天 ----------
    def chat_sessions(self, msgid_begin=0, count=20):
        return self._json(self.lib.zy_chat_sessions(int(msgid_begin), int(count)))

    def chat_messages(self, session_id, id_end=0, limit=30):
        return self._json(self.lib.zy_chat_messages(int(session_id), int(id_end), int(limit)))

    def chat_say(self, session_id, to_mid, content, mtype=1):
        if isinstance(content, str):
            content = content.encode("utf-8")
        return self._json(self.lib.zy_chat_say(int(session_id), int(to_mid), content, int(mtype)))

    def chat_read(self, session_id, msgid):
        return self._json(self.lib.zy_chat_read(int(session_id), int(msgid)))

    def chat_recall(self, session_id, msgid):
        return self._json(self.lib.zy_chat_recall(int(session_id), int(msgid)))

    def chat_hide_session(self, session_id, last_msgid=0):
        return self._json(self.lib.zy_chat_hide_session(int(session_id), int(last_msgid)))

    def chat_top_session(self, session_id, on=True):
        return self._json(self.lib.zy_chat_top_session(int(session_id), 1 if on else 0))

    # ---------- 账号 ----------
    def account_info(self):
        return self._json(self.lib.zy_account_info())

    def user_profile(self, mid):
        return self._json(self.lib.zy_user_profile(int(mid)))

    def feed_recommend(self, limit=20):
        return self._json(self.lib.zy_feed_recommend(int(limit)))

    # ---------- 社区内容 ----------
    def post_detail(self, pid):
        """帖子正文 + 评论（一次拿全）。"""
        return self._json(self.lib.zy_post_detail(int(pid)))

    def post_reviews(self, pid, offset=0):
        """主评论列表，offset 翻页。"""
        return self._json(self.lib.zy_post_reviews(int(pid), int(offset)))

    def topic_detail(self, tid):
        return self._json(self.lib.zy_topic_detail(int(tid)))

    def topic_posts(self, tid, offset=0):
        """话题下的帖子流。"""
        return self._json(self.lib.zy_topic_posts(int(tid), int(offset)))

    def search_post(self, q, offset=0):
        return self._json(self.lib.zy_search_post(q.encode("utf-8"), int(offset)))

    def search_user(self, q, offset=0):
        return self._json(self.lib.zy_search_user(q.encode("utf-8"), int(offset)))

    def user_posts(self, mid):
        return self._json(self.lib.zy_user_posts(int(mid)))

    def my_profile(self):
        return self._json(self.lib.zy_my_profile())

    def follow_feed(self, offset=0):
        return self._json(self.lib.zy_follow_feed(int(offset)))

    def video_feed(self, offset=0):
        return self._json(self.lib.zy_video_feed(int(offset)))

    def parse_share_text(self, text):
        """解析分享口令/链接（7.5.3 新增）。"""
        return self._json(self.lib.zy_parse_share_text(text.encode("utf-8")))

    def topic_posts_list(self, tid, hot_discuss=0):
        """⚠️ 参数未校准，当前会返回 ret=-1；请改用 topic_posts()。"""
        return self._json(self.lib.zy_topic_posts_list(int(tid), int(hot_discuss)))

    def user_profile_v2(self, uid):
        return self._json(self.lib.zy_user_profile_v2(int(uid)))

    def search_video(self, q):
        return self._json(self.lib.zy_search_video(q.encode("utf-8")))

    def video_favor_folders(self):
        return self._json(self.lib.zy_video_favor_folders())

    # ---------- 写操作（参数已按公开接口校准；会改变服务端状态） ----------
    def post_like(self, pid, like_type=1):
        """点赞帖子。⚠️ 未实测。"""
        return self._json(self.lib.zy_post_like(int(pid), int(like_type)))

    def post_unlike(self, pid):
        """取消点赞。⚠️ 未实测。"""
        return self._json(self.lib.zy_post_unlike(int(pid)))

    def review_like(self, pid, rid, status=1):
        """点赞评论（status=1 点赞，0 取消）。⚠️ 未实测。"""
        return self._json(self.lib.zy_review_like(int(pid), int(rid), int(status)))

    def favorite(self, pid, fid=0):
        """收藏帖子。⚠️ 未实测。"""
        return self._json(self.lib.zy_favorite(int(pid), int(fid)))

    def attention(self, uid, pid=0, follow=True):
        """关注/取关。⚠️ 未实测。"""
        return self._json(self.lib.zy_attention(int(uid), int(pid), 1 if follow else 0))


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # 自检：只打印版本和库路径
    print("libzuiyou", load_library().zy_version().decode())
    print("lib path:", os.environ.get("ZUIYOU_LIB") or _default_lib_path())
