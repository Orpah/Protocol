# -*- coding: utf-8 -*-
"""check_docs.py — 本仓**文档一致性**检查（本仓只有文档 ⇒ 这是唯一能上机器守的一类闸门）。

守的是 `AGENTS.md` 已经写下的几条硬规则（每条都指到出处 ✓，不另立口径 ✗）：

  ① §1「改规范 = 改契约」：`docs/OrpahIDProtocol.md` 的**标题行版本号**必须等于
     文末**修订记录表最后一行**的版本号（两处必须同步 ✓）；
  ② §4「图文并茂」：`README.md` / `README_zh.md` 各自至少要引用 1 张本地图 ✓，
     且 **README / AGENTS / docs 里引用的本地图片必须真的存在** ✓（中英两份一起查 ✓）；
  ③ §5「文本一律 UTF-8 无 BOM」：`*.md` / `*.py` / `*.txt` 逐个解码 + 查 BOM ✓。

**不检查**什么 ✗：规范内容对不对（那只能由人审 ✓）；`.odg` 原图与 `docs/images/*.png` 是否
同源（二进制 ✗）；中英两份 README 的图片**数量**是否一致（AGENTS 没这条 ✗，别自创 ✗）；
**规范里任何 MUST 的语义实现** ✗（`CHECK` 只由 `ORG-UNIQUE` 算、签名预像 / JCS / `b64url`、
`xport` 不在预像内、不轮换 …… 由兄弟仓的交叉测试守 ✓ —— "不判规范内容对错"**不等于**
"协议不变量已被本脚本覆盖" ✗）。

判定口径（与兄弟仓一致 ✓）：**退出码 0 且输出里没有 `FAIL`** ✓。
用法：`python tools/check_docs.py`（在仓库根或任意目录都行 ✓ —— 路径按脚本自己位置算 ✓）。

★ 两条实现口径（2026-10-12 审查后加 ✓ —— 都是"尺子错了"那类，改脚本、不改仓库）：
  一、**读文本绝不抛异常**：坏编码 / BOM 一律由 `text_of()` 指名 `FAIL` 再返回空串 ✓ ——
     以前 ② 先 `open(..., "utf-8").read()`，碰到非 UTF-8 文件直接 traceback ⇒ ③ 根本没跑、
     输出里也没有 `FAIL` 行（判定口径退化成"看 traceback"）✗；
  二、「修订记录表最后一行」= **真表体里**的最后一行 ✓ —— 以前是全文件"最后一个匹配行"：
     表尾改成链接 / 加粗、后面再多一行说明，就静默回落到上一条，诊断还指错方向 ✗。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SPEC = os.path.join(ROOT, "docs", "OrpahIDProtocol.md")
SPEC_ALT = os.path.join(ROOT, "docs", "orpah-over-halow", "SPEC.md")
IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
TEXT_EXT = (".md", ".py", ".txt")

# 标题行只在这一窗口内找 ✓：规范标题必须是开头的大字标题，往下挪就是结构性坏了 ⇒ 宁可错报 ✓
TITLE_WINDOW = 10
BOM = b"\xef\xbb\xbf"

RE_VERSION_TITLE = re.compile(r"^#\s+.*?v(\d+(?:\.\d+)+)")
# 版本列允许 `1.22` / `v1.22` / `**1.22**` / `*1.22*` / `` `1.22` `` / `[1.22](url)` ✓
RE_TABLE_VER = re.compile(
    r"^\|\s*\**\s*\[?\s*\**\s*`?\s*v?(\d+(?:\.\d+)+)\s*`?\s*\**\s*\]?(?:\([^)]*\))?\s*\|")
RE_CELL = re.compile(r"(?<!\\)\|")          # 未转义的单元格分隔符 ✓
RE_SEP = re.compile(r"^:?-{3,}:?$")         # 表头分隔行 `|---|:--:|` ✓
RE_HEAD_KEYWORDS = (("版本", "version"), ("日期", "date"), ("变更", "change"))
RE_MD_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
RE_PCT_ESC = re.compile(r"%([0-9A-Fa-f]{2})")
# ★ 查引用前**必须去掉代码**（围栏块 + 行内 code span），且**先围栏、后行内** ✓：
#   围栏块里常含反引号，先剥行内 code 会把块边界吃掉 ⇒ 剩下的半截被当成正文 ✗。
#   本仓 AGENTS §4 里就有个示例 `[![说明](docs/images/x.png)](…)` —— 那是**讲怎么写的占位符** ✗，
#   不是真引用 ✓。第一版没去掉 ⇒ 当场误报 `x.png 不存在` ✗（**先问"是不是尺子错了"，再改仓库** ✓）。
RE_FENCE = re.compile(r"```.*?```", re.S)
RE_INLINE = re.compile(r"`[^`]*`")


def strip_code(text):
    """把代码块 / 行内 code 去掉 —— 只在"正文"里找引用 ✓（先围栏、后行内 ✓）。"""
    return RE_INLINE.sub("", RE_FENCE.sub("", text))


fails = []
infos = []
encoding_checked = set()    # ③ 已点名过的坏文件 ✓（避免 ① 再报一遍同样的错 ✗）


def fail(msg):
    fails.append(msg)
    print("  FAIL %s" % msg)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def decode(raw):
    """(text, err) —— 坏编码 / 带 BOM 都**不抛异常**，只把"为什么坏"交回调用方 ✓。"""
    bom = raw.startswith(BOM)
    if bom:
        raw = raw[len(BOM):]
    try:
        return raw.decode("utf-8"), ("带 UTF-8 BOM（AGENTS §5：无 BOM ✗）" if bom else None)
    except UnicodeDecodeError as e:
        return "", "不是合法 UTF-8：%s%s" % (e, "（且带 UTF-8 BOM）" if bom else "")


def text_of(path):
    """读文本给 ①② 用：**坏文件指名 FAIL 后返回空串** ✓ —— 既不许崩、也不许静默跳过 ✗。

    ③ 先跑并已经点名过的坏文件不再重复记（见 `encoding_checked`）✓ ——
    每个坏文件在输出里恰好只有一条 FAIL ✓。
    """
    text, err = decode(read(path))
    if err and path not in encoding_checked:
        fail("%s %s" % (rel(path), err))
    return text


def md_files():
    """要查链接与编码的文本文件（不含 .git ✓）。

    不做 SKIP_DIRS ✗：坏编码的文件必须变成一条**指名的 FAIL** ✓，
    而不是"因为它在 build/ 里，所以就没人检查了" ✗（那等于自己把闸门关掉）。
    """
    out = []
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", ".vscode", "__pycache__")]
        for n in names:
            p = os.path.join(base, n)
            if os.path.splitext(n)[1].lower() in TEXT_EXT:
                out.append(p)
    return sorted(out)


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def _ver_key(v):
    """版本排序键：按数字段比 ✓（字符串比会把 `1.9` 判成大于 `1.10` ✗）。"""
    return tuple(int(x) for x in v.split("."))


def _cells(line):
    r"""把表格行拆成单元格 ✓（去掉首尾的 `|`；`\|` 不算分隔 ✓）。"""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip() for c in RE_CELL.split(s)]


def _is_header(cells):
    """表头行：单元格里含「版本 / 日期 / 变更」（大小写不敏感 ✓）。"""
    low = [c.lower() for c in cells]
    return len(cells) >= 3 and all(any(k in c for k in ks) for c, ks in zip(low, RE_HEAD_KEYWORDS))


def _is_sep(cells):
    return bool(cells) and all(RE_SEP.match(c.replace(" ", "")) for c in cells)


def revision_table(lines):
    """定位**修订记录表**，返回其表体的行号列表；不是表就返回 None ⇒ 调用方显式 FAIL ✓。

    三条判据同时成立才是修订表：
      ① 表头行含「版本 / 日期 / 变更」；② 紧跟一行表头分隔行 `|---|---|`；
      ③ 其后**连续的** `|` 开头行即表体 —— 碰到空行 / 非表格行就结束 ✓。
    所以表尾之后再写一段说明、或另起一张表，都不会污染「最后一行」✗（旧实现正是在这里漏判）。
    """
    for i in range(len(lines) - 2):
        if not lines[i].lstrip().startswith("|"):
            continue
        head = _cells(lines[i])
        if not _is_header(head) or not _is_sep(_cells(lines[i + 1])):
            continue
        body = []
        j = i + 2
        while j < len(lines) and lines[j].lstrip().startswith("|"):
            body.append(j)
            j += 1
        if body:
            return body
    return None


# ---------------------------------------------------------------- ① 版本一致性
def check_version():
    print("① 规范版本一致性（标题行 ↔ 修订记录表最后一行）")
    if not os.path.isfile(SPEC):
        fail("找不到 %s" % rel(SPEC))
        return
    text = text_of(SPEC)            # 坏编码已在 text_of 里记过 FAIL ✓ 这里拿到空串
    lines = text.splitlines()

    title = None
    for ln in lines[:TITLE_WINDOW]:
        m = RE_VERSION_TITLE.match(ln.strip())
        if m:
            title = m.group(1)
            break

    body = revision_table(lines)
    vers = []
    if body is not None:
        for i in body:
            m = RE_TABLE_VER.match(lines[i].strip())
            if m:
                vers.append((m.group(1), i + 1))        # (版本, 行号) ✓

    if title is None:
        fail("%s 前 %d 行内没有 `# … vX.Y` 标题行（AGENTS §1 要求标题行带版本 ✓）"
             % (rel(SPEC), TITLE_WINDOW))
        return
    if not vers:
        fail("%s 找不到修订记录表（要 表头含「版本/日期/变更」+ 分隔行 `|---|---|`；"
             "AGENTS §1 要求 §12 有修订记录表 ✓）" % rel(SPEC))
        return

    last, lineno = vers[-1]
    if title != last:
        fail("%s 版本不一致：标题行 `v%s` ≠ 修订记录表最后一行（第 %d 行）`v%s`"
             "（AGENTS §1：改规范必须两处同步 ✗）" % (rel(SPEC), title, lineno, last))
    else:
        print("  PASS %s 标题行与修订表最后一行都是 `v%s`（共 %d 行记录 ✓）"
              % (rel(SPEC), title, len(vers)))

    # 版本必须单调递增（按数字段比：`1.9` < `1.10` ✓）—— 插错位置 / 抄了旧行最容易在这里露 ✓
    bad = [(a, b, ln) for (a, _), (b, ln) in zip(vers, vers[1:]) if _ver_key(b) <= _ver_key(a)]
    if bad:
        a, b, ln = bad[0]
        fail("%s 修订记录表版本没有递增：第 %d 行 `v%s` 之后是 `v%s`（按数字段比 ✗；"
             "是不是插错位置 / 抄了旧行？）" % (rel(SPEC), ln, a, b))
    else:
        print("  PASS 修订表 %d 行版本单调递增（v%s → v%s ✓）"
              % (len(vers), vers[0][0], vers[-1][0]))

    # SPEC.md 的版本只在「状态」行里（没有修订表 ✓）⇒ 只当 info 报出来，不判 FAIL ✓
    if os.path.isfile(SPEC_ALT):
        head = text_of(SPEC_ALT)[:2000]
        m = re.search(r"v(\d+(?:\.\d+)+)", head)
        infos.append("%s 的版本（状态行，无修订表 ⇒ 只报不判）：v%s"
                     % (rel(SPEC_ALT), m.group(1) if m else "?"))


# ---------------------------------------------------------------- ② 图片引用
def _pct_unquote(s):
    """还原 `%E7%BD%91` 这类百分号编码 ✓（`%XX` 逐字节拼成 UTF-8；非法就原样保留 ✓）。"""
    if "%" not in s:
        return s
    out = []
    i = 0
    while i < len(s):
        m = RE_PCT_ESC.match(s, i)
        if not m:
            out.append(s[i])
            i += 1
            continue
        buf = bytearray()
        j = i
        while j < len(s) and RE_PCT_ESC.match(s, j):
            buf.append(int(s[j + 1:j + 3], 16))
            j += 3
        try:
            out.append(buf.decode("utf-8"))
        except UnicodeDecodeError:
            out.append(s[i:j])                          # 不是合法 UTF-8 ⇒ 原样保留 ✓
        i = j
    return "".join(out)


def img_exists(base_dir, target):
    """图片引用是否存在 ✓。GitHub 上 `![x](a/网络 图.png)` 空格**可不编码** ⇒ 两种写法都试 ✓。"""
    for cand in (_pct_unquote(target), target):
        if os.path.exists(os.path.join(base_dir, cand)):
            return True
    return False


def local_imgs(text):
    """正文里的本地图片引用（排除 http / mailto / 页内锚点 ✓）。"""
    return [t for t in RE_MD_LINK.findall(text)
            if t.lower().endswith(IMG_EXT)
            and not t.startswith(("http://", "https://", "mailto:", "#"))]


def check_links():
    print("② README / AGENTS / docs 里引用的本地图片必须存在")
    checked = 0
    for p in md_files():
        if not p.endswith(".md"):
            continue
        text = strip_code(text_of(p))
        for target in local_imgs(text):
            checked += 1
            if not img_exists(os.path.dirname(p), target):
                fail("%s 引用的图片不存在：%s" % (rel(p), target))
    print("  PASS 共核对 %d 处本地图片引用 ✓" % checked)

    # AGENTS §4：两份顶层 README 各自正文里至少要嵌图 ✓
    for name in ("README.md", "README_zh.md"):
        p = os.path.join(ROOT, name)
        if not os.path.isfile(p):
            fail("缺少 %s（AGENTS §4：中英两份要成对 ✓）" % name)
            continue
        n = len(local_imgs(strip_code(text_of(p))))
        if n == 0:
            fail("%s 正文里一张图都没嵌（AGENTS §4：图对人的阅读吸引力更大 ✗）" % name)
        else:
            print("  PASS %s 正文嵌入 %d 张本地图 ✓" % (name, n))

    # 反向：docs/images 里有没有"谁都没引用"的图（只报 info ✓ 不判 FAIL ✓）
    imgs_dir = os.path.join(ROOT, "docs", "images")
    if os.path.isdir(imgs_dir):
        used = set()
        for p in md_files():
            if not p.endswith(".md"):
                continue
            for t in RE_MD_LINK.findall(strip_code(text_of(p))):
                used.add(os.path.basename(_pct_unquote(t)))
        orphan = sorted(n for n in os.listdir(imgs_dir) if n not in used)
        if orphan:
            infos.append("docs/images/ 里未被任何文档引用：%s（只报不判 ✓）" % "、".join(orphan))


# ---------------------------------------------------------------- ③ 编码
def check_encoding():
    print("③ 文本一律 UTF-8 无 BOM（AGENTS §5）")
    n = 0
    for p in md_files():
        n += 1
        _, err = decode(read(p))        # 与 ①② 共用同一把尺子 ✓（BOM/UTF-8 判定只写一处 ✓）
        if err:
            encoding_checked.add(p)     # 记住：① 拿到空串时不要再报一次同样的错 ✓
            fail("%s %s" % (rel(p), err))
    print("  PASS 共核对 %d 个文本文件 ✓" % n)


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                   # noqa: BLE001
            pass                                            # 老解释器 / 已重定向的流：忽略 ✓
    print("=" * 78)
    print("本仓文档一致性检查（AGENTS §1 / §4 / §5 —— 只守机械规则，不判规范内容 ✓）")
    print("=" * 78)
    # ③ 先跑：坏编码 / BOM 是最底层的"尺子"问题，先点名 ✓ 后面的 PASS 数字才可信 ✓
    check_encoding()
    check_version()
    check_links()
    print("-" * 78)
    for i in infos:
        print("  [info] %s" % i)
    if fails:
        print("FAIL：%d 项未过 -> %s" % (len(fails), "；".join(fails)))
        return 1
    print("PASS：3 类检查全过（版本一致 ✓ 图片引用齐 ✓ 编码干净 ✓）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
