/*
 * example.c —— 用 C 直接 dlopen 调 libzuiyou（覆盖全部能力类别）
 *
 * 编译（Linux）:
 *   gcc example.c -ldl -o example
 * 运行:
 *   ZUIYOU_LIB=../lib/linux-x86_64/libzuiyou.so \
 *   ZUIYOU_TOKEN='<your-token>' ZUIYOU_MID=123456789 ./example
 *
 * 编译（Android / NDK）:
 *   $CC example.c -o example
 *   adb push example /data/local/tmp/
 *   adb shell 'cd /data/local/tmp && LD_LIBRARY_PATH=. ./example'
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---------- 函数指针 ---------- */
typedef int   (*fn_int)(void);
typedef int   (*fn_init)(const char *);
typedef void  (*fn_void)(void);
typedef const char *(*fn_cstr)(void);
typedef void  (*fn_free)(char *);
typedef char *(*fn_str_str)(const char *);
typedef char *(*fn_str_str2)(const char *, const char *);

typedef char *(*fn_sessions)(long long, int);
typedef char *(*fn_messages)(long long, long long, int);
typedef char *(*fn_say)(long long, long long, const char *, int);
typedef char *(*fn_read)(long long, long long);

typedef char *(*fn_post_detail)(long long);
typedef char *(*fn_post_reviews)(long long, int);
typedef char *(*fn_topic)(long long);
typedef char *(*fn_topic_posts)(long long, int);
typedef char *(*fn_feed)(int);
typedef char *(*fn_search)(const char *, int);
typedef char *(*fn_user)(long long);
typedef char *(*fn_none)(void);

typedef char *(*fn_sign)(const unsigned char *, int);

static void *H;
static fn_free  do_free;

static void *need(const char *name)
{
    void *p = dlsym(H, name);
    if (!p) {
        fprintf(stderr, "缺少符号: %s（版本不匹配？）\n", name);
        exit(2);
    }
    return p;
}

/* 从 JSON 里取 "ret": N */
static int json_ret(const char *json)
{
    const char *p;
    if (!json) return -999;
    p = strstr(json, "\"ret\"");
    if (!p) return -998;
    p = strchr(p, ':');
    if (!p) return -997;
    while (*p && (*p == ':' || *p == ' ')) p++;
    return atoi(p);
}

/* 统计 JSON 里某个 key 后面数组的元素个数（粗略：数 ',' 不行，用 "key":[...] 的 '[' 后到 ']' 之间的对象数） */
static int json_count(const char *json, const char *key)
{
    char pat[64];
    const char *p, *q;
    int depth = 0, n = 0, in_str = 0, esc = 0;
    if (!json) return -1;
    snprintf(pat, sizeof(pat), "\"%s\"", key);
    p = strstr(json, pat);
    if (!p) return -1;
    p = strchr(p, '[');
    if (!p) return -1;
    p++;
    depth = 1;                     /* 已进入数组 */
    for (q = p; *q; q++) {
        if (in_str) {
            if (esc) esc = 0;
            else if (*q == '\\') esc = 1;
            else if (*q == '"') in_str = 0;
            continue;
        }
        if (*q == '"') { in_str = 1; continue; }
        if (*q == '{') {
            if (depth == 1) n++;          /* 数组顶层的对象 */
            depth++;
        } else if (*q == '[') {
            depth++;
        } else if (*q == ']' || *q == '}') {
            depth--;
            if (depth == 0) break;        /* 数组结束 */
        }
    }
    return n;
}

static void show(const char *tag, char *json, const char *count_key, size_t head)
{
    int ret = json_ret(json);
    int n = count_key ? json_count(json, count_key) : -1;
    if (!json) {
        printf("  %-20s <失败: %s>\n", tag, ((fn_cstr)need("zy_last_error"))());
        return;
    }
    printf("  %-20s ret=%-4d", tag, ret);
    if (n >= 0) printf(" %-8s=%d", count_key, n);
    printf("  %.60s%s\n", json, strlen(json) > 60 ? "…" : "");
    do_free(json);
}

int main(void)
{
    const char *lib, *token, *mid_s;
    char cfg[2048];
    long long mid;
    long long sid = 0, pid = 0, tid = 0;
    char *r;

    lib = getenv("ZUIYOU_LIB");
    if (!lib) lib = "../lib/linux-x86_64/libzuiyou.so";
    token = getenv("ZUIYOU_TOKEN");
    mid_s = getenv("ZUIYOU_MID");
    if (!token || !mid_s) {
        fprintf(stderr, "请设置 ZUIYOU_TOKEN 和 ZUIYOU_MID\n");
        return 2;
    }
    mid = atoll(mid_s);

    H = dlopen(lib, RTLD_NOW);
    if (!H) { fprintf(stderr, "dlopen 失败: %s\n", dlerror()); return 2; }
    do_free = (fn_free)need("zy_free");

    /* ================= 0. 自检 ================= */
    printf("\n=== 0. 初始化 ===\n");
    printf("  libzuiyou %s\n", ((fn_cstr)need("zy_version"))());
    printf("  selftest = %d (0=通过)\n", ((fn_int)need("zy_selftest"))());

    snprintf(cfg, sizeof(cfg), "{\"token\":\"%s\",\"mid\":%lld}", token, mid);
    if (((fn_init)need("zy_init"))(cfg) != 0) {
        fprintf(stderr, "  init 失败: %s\n", ((fn_cstr)need("zy_last_error"))());
        return 2;
    }
    printf("  init OK\n");

    /* ================= 1. 聊天 ================= */
    printf("\n=== 1. 聊天 ===\n");
    r = ((fn_sessions)need("zy_chat_sessions"))(0, 3);
    if (r && json_ret(r) == 1) {
        /* 从响应里抠第一个 session_id（简单找 "session_id": ） */
        const char *p = strstr(r, "\"session_id\":");
        if (p) sid = atoll(p + 13);
    }
    show("chat_sessions", r, "sessions", 0);   /* show 内部会 free */

    if (sid) {
        printf("      ↳ sid = %lld\n", sid);
        {
            char *m = ((fn_messages)need("zy_chat_messages"))(sid, 0, 3);
            long long msgid = 0;
            if (m) {
                const char *p = strstr(m, "\"msgid\":");
                if (p) msgid = atoll(p + 8);
            }
            show("chat_messages", m, "messages", 0);
            if (msgid) {
                show("chat_read", ((fn_read)need("zy_chat_read"))(sid, msgid), NULL, 0);
            }
        }
        /* 发消息/撤回/删除/置顶会改变状态，示例里不调用 */
        printf("  (chat_say / chat_recall / chat_hide_session / chat_top_session 未调用)\n");
    }

    /* ================= 3. 搜索 ================= */
    printf("\n=== 3. 搜索 ===\n");
    r = ((fn_search)need("zy_search_post"))("笑话", 0);
    if (r && json_ret(r) == 1) {
        const char *p = strstr(r, "\"id\":");
        if (p) pid = atoll(p + 5);
        p = strstr(r, "\"tid\":");
        if (p) tid = atoll(p + 6);
    }
    show("search_post", r, "list", 0);   /* show 内部会 free */
    show("search_user", ((fn_search)need("zy_search_user"))("小", 0), "list", 0);
    {
        char *v = ((fn_str_str)need("zy_search_video"))("猫");
        show("search_video", v, "list", 0);
    }

    /* ================= 4. 内容 ================= */
    printf("\n=== 4. 内容 ===\n");
    if (pid) {
        printf("      ↳ pid = %lld  tid = %lld\n", pid, tid);
        show("post_detail", ((fn_post_detail)need("zy_post_detail"))(pid), "hotreviews", 0);
        show("post_reviews", ((fn_post_reviews)need("zy_post_reviews"))(pid, 0), "list", 0);
    }
    if (tid) {
        show("topic_detail", ((fn_topic)need("zy_topic_detail"))(tid), NULL, 0);
        show("topic_posts", ((fn_topic_posts)need("zy_topic_posts"))(tid, 0), "list", 0);
    }
    show("follow_feed", ((fn_feed)need("zy_follow_feed"))(0), "list", 0);
    show("video_feed", ((fn_feed)need("zy_video_feed"))(0), "list", 0);
    show("video_favor_folders", ((fn_none)need("zy_video_favor_folders"))(), "list", 0);
    {
        char *s = ((fn_str_str)need("zy_parse_share_text"))("https://share.izuiyou.com/test");
        show("parse_share_text", s, NULL, 0);
    }

    /* ================= 5. 用户 ================= */
    printf("\n=== 5. 用户 ===\n");
    show("my_profile", ((fn_none)need("zy_my_profile"))(), NULL, 0);
    show("user_profile", ((fn_user)need("zy_user_profile"))(mid), NULL, 0);
    show("user_profile_v2", ((fn_user)need("zy_user_profile_v2"))(mid), NULL, 0);
    show("user_posts", ((fn_user)need("zy_user_posts"))(mid), "list", 0);

    /* ================= 6. 通用调用 ================= */
    printf("\n=== 6. 通用调用 ===\n");
    printf("  zy_call(path, json)         原样发送\n");
    printf("  zy_call_auth(path, json)    自动补鉴权字段\n");
    printf("  path 传目标路径、payload 传 JSON 字符串；用法见 docs/API.md\n");

    /* ================= 7. 写操作 ================= */
    printf("\n=== 7. 写操作（示例，未调用） ===\n");
    printf("  zy_post_like(pid, 1)         点赞\n");
    printf("  zy_post_unlike(pid)          取消点赞\n");
    printf("  zy_review_like(pid, rid, 1)  评论点赞\n");
    printf("  zy_favorite(pid, 0)          收藏\n");
    printf("  zy_attention(uid, pid, 1)    关注\n");

    ((fn_void)need("zy_shutdown"))();
    dlclose(H);
    printf("\n完成\n");
    return 0;
}
