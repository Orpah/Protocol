# -*- coding: utf-8 -*-
"""check_docs.py — 本仓**文档一致性**检查（本仓只有文档 ⇒ 这是唯一能上机器守的一类闸门）。

守的是 `AGENTS.md` 已经写下的几条硬规则（每条都指到出处 ✓，不另立口径 ✗）：

  ① §1「改规范 = 改契约」：`docs/OrpahIDProtocol.md` 的**标题行版本号**必须等于
     文末**修订记录表最后一行**的版本号（两处必须同步 ✓）；
  ② §4「图文并茂」：`README.md` / `README_zh.md` 各自至少要引用 1 张本地图 ✓，
     且 **README / AGENTS / docs 里引用的本地图片必须真的存在** ✓（中英两份一起查 ✓）；
  ③ §5「文本一律 UTF-8 无 BOM」：`*.md` / `*.py` / `*.txt` 逐个解码 + 查 BOM ✓。

**不检查**什么 ✗：规范内容对不对（那只能由人审 ✓）；`.odg` 原图与 `docs/images/*.png` 是否
同源（二进制 ✗）；中英两份 README 的图片**数量**是否一致（AGENTS 没这条 ✗，别自创 ✗）。

判定口径（与兄弟仓一致 ✓）：**退出码 0 且输出里没有 `FAIL`** ✓。
用法：`python tools/check_docs.py`（在仓库根或任意目录都行 ✓ —— 路径按脚本自己位置算 ✓）。
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
SUM_EXT = (".md", ".py", ".txt", ".odg", ".gitignore", "")

RE_VERSION_TITLE = re.compile(r"^#\s+.*?v(\d+(?:\.\d+)+)")
RE_TABLE_VER = re.compile(r"^\|\s*\*{0,2}v?(\d+(?:\.\d+)+)\*{0,2}\s*\|")
RE_MD_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
# ★ 查引用前**必须去掉代码**（围栏块 + 行内 code span）：
#   本仓 AGENTS §4 里就有个示例 `[![说明](docs/images/x.png)](…)` —— 那是**讲怎么写的占位符** ✗，
#   不是真引用 ✓。第一版没去掉 ⇒ 当场误报 `x.png 不存在` ✗（**先问"是不是尺子错了"，再改仓库** ✓）。
RE_FENCE = re.compile(r"```.*?```", re.S)
RE_INLINE = re.compile(r"`[^`]*`")


def strip_code(text):
    """把代码块 / 行内 code 去掉 —— 只在"正文"里找引用 ✓。"""
    return RE_INLINE.sub("", RE_FENCE.sub("", text))


fails = []
infos = []


def fail(msg):
    fails.append(msg)
    print("  FAIL %s" % msg)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def md_files():
    """要查链接与编码的文本文件（不含 .git ✓）。"""
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


# ---------------------------------------------------------------- ① 版本一致性
def check_version():
    print("① 规范版本一致性（标题行 ↔ 修订记录表最后一行）")
    if not os.path.isfile(SPEC):
        fail("找不到 %s" % rel(SPEC))
        return
    with open(SPEC, encoding="utf-8") as f:
        lines = f.read().splitlines()

    title = None
    for ln in lines[:10]:
        m = RE_VERSION_TITLE.match(ln.strip())
        if m:
            title = m.group(1)
            break
    tbl = [RE_TABLE_VER.match(ln.strip()) for ln in lines]
    vers = [m.group(1) for m in tbl if m]
    if title is None:
        fail("%s 标题行没有 `vX.Y` 版本号（AGENTS §1 要求标题行带版本 ✓）" % rel(SPEC))
        return
    if not vers:
        fail("%s 找不到修订记录表（AGENTS §1 要求 §12 有修订记录表 ✓）" % rel(SPEC))
        return
    last = vers[-1]
    if title != last:
        fail("%s 版本不一致：标题行 `v%s` ≠ 修订记录表最后一行 `v%s`（AGENTS §1：改规范必须两处同步 ✗）"
             % (rel(SPEC), title, last))
    else:
        print("  PASS %s 标题行与修订表最后一行都是 `v%s`（共 %d 行记录 ✓）"
              % (rel(SPEC), title, len(vers)))

    # SPEC.md 的版本只在「状态」行里（没有修订表 ✓）⇒ 只当 info 报出来，不判 FAIL ✓
    if os.path.isfile(SPEC_ALT):
        with open(SPEC_ALT, encoding="utf-8") as f:
            head = f.read(2000)
        m = re.search(r"v(\d+(?:\.\d+)+)", head)
        infos.append("%s 的版本（状态行，无修订表 ⇒ 只报不判）：v%s"
                     % (rel(SPEC_ALT), m.group(1) if m else "?"))


# ---------------------------------------------------------------- ② 图片引用
def check_links():
    print("② README / AGENTS / docs 里引用的本地图片必须存在")
    checked = 0
    for p in md_files():
        if not p.endswith(".md"):
            continue
        text = strip_code(open(p, encoding="utf-8").read())
        for target in RE_MD_LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if not target.lower().endswith(IMG_EXT):
                continue
            checked += 1
            ok = os.path.exists(os.path.join(os.path.dirname(p), target))
            if not ok:
                fail("%s 引用的图片不存在：%s" % (rel(p), target))
    print("  PASS 共核对 %d 处本地图片引用 ✓" % checked)

    # AGENTS §4：两份顶层 README 各自正文里至少要嵌图 ✓
    for name in ("README.md", "README_zh.md"):
        p = os.path.join(ROOT, name)
        if not os.path.isfile(p):
            fail("缺少 %s（AGENTS §4：中英两份要成对 ✓）" % name)
            continue
        text = strip_code(open(p, encoding="utf-8").read())
        n = sum(1 for t in RE_MD_LINK.findall(text)
                if t.lower().endswith(IMG_EXT) and not t.startswith(("http", "#")))
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
            for t in RE_MD_LINK.findall(strip_code(open(p, encoding="utf-8").read())):
                used.add(os.path.basename(t))
        orphan = sorted(n for n in os.listdir(imgs_dir) if n not in used)
        if orphan:
            infos.append("docs/images/ 里未被任何文档引用：%s（只报不判 ✓）" % "、".join(orphan))


# ---------------------------------------------------------------- ③ 编码
def check_encoding():
    print("③ 文本一律 UTF-8 无 BOM（AGENTS §5）")
    n = 0
    for p in md_files():
        raw = read(p)
        n += 1
        if raw.startswith(b"\xef\xbb\xbf"):
            fail("%s 带 UTF-8 BOM（AGENTS §5：无 BOM ✗）" % rel(p))
            continue
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as e:
            fail("%s 不是合法 UTF-8：%s" % (rel(p), e))
    print("  PASS 共核对 %d 个文本文件 ✓" % n)


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                   # noqa: BLE001
            pass
    print("=" * 78)
    print("本仓文档一致性检查（AGENTS §1 / §4 / §5 —— 只守机械规则，不判规范内容 ✓）")
    print("=" * 78)
    check_version()
    check_links()
    check_encoding()
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
