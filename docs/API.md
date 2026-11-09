# C ABI 参考

全部函数为 C 调用约定，可直接 `dlopen` + `dlsym`。
返回 `char *` 的函数返回堆内存 JSON 字符串，用完调用 `zy_free()`。

---

## 生命周期

```c
const char *zy_version(void);                 // 版本号
int         zy_selftest(void);                // 自检，0 = 通过
int         zy_init(const char *config_json); // {"token":"...","mid":123,"timeout":25}
void        zy_shutdown(void);
const char *zy_last_error(void);              // 最近一次错误描述
void        zy_free(void *p);                 // 释放返回值
```

---

## 通用调用

```c
char *zy_call(const char *path, const char *body);
char *zy_call_auth(const char *path, const char *body);     // 自动带鉴权
char *zy_call_ex(const char *path, const char *body, int flags);  // flags: 1=不取票据 2=不重试
```

`zy_call*` 用于调用 SDK 未封装的能力，`body` 为 JSON 对象字符串。

---

## 聊天

```c
char *zy_chat_sessions(long long msgid_begin, int count);
char *zy_chat_messages(long long session_id, long long msgid_end, int limit);
char *zy_chat_say(long long session_id, long long to_mid, const char *content, int mtype);
char *zy_chat_send_face(long long session_id, long long to_mid,
                        long long face_id, const char *fmt, int w, int h);
char *zy_chat_read(long long session_id, long long msgid);
char *zy_chat_recall(long long session_id, long long msgid);
char *zy_chat_hide_session(long long session_id, long long last_msgid);
char *zy_chat_top_session(long long session_id, int on);
```

- `chat_say` 需要 `CHAT` 权限，内容会先过敏感词检查
- `chat_send_face` 发送表情/图片，`fmt` 取 `gif`/`jpeg`/`png`，`w`/`h` 传 0 用 200×200
- `mtype` 一般传 1（文本）

---

## 社区内容

```c
char *zy_post_detail(long long pid);
char *zy_post_reviews(long long pid, int offset);
char *zy_topic_detail(long long tid);
char *zy_topic_posts(long long tid, int offset);
char *zy_topic_posts_list(long long tid, int hot_discuss);
char *zy_follow_feed(int offset);
char *zy_video_feed(int offset);
char *zy_video_favor_folders(void);
char *zy_parse_share_text(const char *text);
char *zy_feed_recommend(int limit);           // 当前不可用，用上面几个替代
```

---

## 搜索

```c
char *zy_search_post(const char *q, int offset);
char *zy_search_user(const char *q, int offset);
char *zy_search_video(const char *q);
```

---

## 用户

```c
char *zy_my_profile(void);
char *zy_account_info(void);
char *zy_user_profile(long long mid);
char *zy_user_profile_v2(long long uid);
char *zy_user_posts(long long mid);
```

---

## 表情包

```c
char *zy_emoji_packages(void);                // 表情包列表
char *zy_emoji_list(long long package_id);    // 表情列表，<=0 取全部
```

表情项含 `id` / `name` / `url`（图片直链）/ `packageid`，可直接下载使用。

---

## 写操作

```c
char *zy_post_like(long long pid, int like_type);
char *zy_post_unlike(long long pid);
char *zy_review_like(long long pid, long long rid, int status);
char *zy_favorite(long long pid, long long fid);
char *zy_attention(long long uid, long long pid, int follow);
char *zy_comment_create(long long pid, const char *content, long long rid);
```

`comment_create` 的 `rid=0` 为主评论，非 0 为回复；内容会先过敏感词检查。

---

## 内容安全

```c
int         zy_content_check(const char *text);   // 0=通过，非0=命中类型
const char *zy_content_reason(int code);          // 命中原因的文本描述
```

| 返回码 | 含义 |
|---|---|
| 0 | 通过 |
| 1 | 手机号 |
| 4 | 链接 |
| 6 | 联系方式（微信/QQ/私聊…） |
| 7 | 灰产词（代充/刷单/博彩…） |

---

## 设备与授权

```c
const char *zy_device_id(void);                   // 64 位 hex 设备指纹
int         zy_activate(const char *code);        // 输入授权码，0=成功
int         zy_auth_perms(void);                  // 1=评论 3=评论+私信
long long   zy_auth_expire(void);                 // 0=长期
const char *zy_auth_err(void);
int         zy_auth_refresh_now(void);            // 重读本地缓存
const char *zy_guard_status(void);                // "clean" 或命中原因
```

---

## 错误码

| `ret` | 含义 |
|---|---|
| `1` | 成功（业务层） |
| `-1` / `-11` | 业务错误，见 `msg` |
| `-2` | 网络失败 |
| `-5` | HTTP 非 2xx |
| `-6` | 协议失败 |
| `-7` | 未初始化 |
| `-8` | 数据过大 |
| `-1001` | 未授权（私信需激活） |
| `-1002` | 内容命中敏感词 |
| `-1003` | 检测到调试/篡改环境 |

`-10xx` 是 **SDK 本地拦截**，请求不会发出，返回体带 `"_local": true`。

---

## 线程安全

- `zy_init` / `zy_shutdown` 加全局锁
- 网络调用串行（内部同一把锁），并发安全但不并行
- 返回值是独立堆内存，可跨线程传递，用完各自 `zy_free`

---

## 版本兼容

`zy_version()` 返回语义化版本。新增函数只递增小版本号，已有签名不变。
