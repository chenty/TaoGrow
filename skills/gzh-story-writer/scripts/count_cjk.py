#!/usr/bin/env python3
"""中文字数实测脚本（公众号文章专用）—— count_cjk.js 的 Python 等价实现

两个口径（公众号场景都要看）：
  - 纯汉字数   cjk_only  ：只数中日韩统一表意文字，不含标点/数字/字母
  - 含标点数   with_punct：去掉所有空白字符后的字符数（含标点、数字、字母）

用法：
  python3 count_cjk.py article.md
  python3 count_cjk.py article.md --body-start 9 --body-end 57
  python3 count_cjk.py article.md --body-start 9 --body-end 57 --exclude 19,20
  python3 count_cjk.py article.md --json

退出码：0 正常；1 参数错误；2 行号越界。
"""

import argparse
import json
import re
import sys

# 中日韩表意文字（含扩展 A、兼容区），与 JS 版一致
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def strip_markdown_noise(text: str) -> str:
    """去掉 Markdown 语法符号，避免把 ** > # - 等计入字数。"""
    t = text
    t = re.sub(r"\*\*([\s\S]+?)\*\*", r"\1", t)                 # 粗体 **x**
    t = re.sub(r"(^|[^*])\*(?!\*)([\s\S]+?)(?<!\*)\*(?!\*)", r"\1\2", t)  # 斜体 *x*
    t = re.sub(r"^[ \t]*>+[ \t]?", "", t, flags=re.M)           # 引用 >
    t = re.sub(r"^[ \t]*[-*+][ \t]+", "", t, flags=re.M)        # 无序列表
    t = re.sub(r"^[ \t]*\d+\.[ \t]+", "", t, flags=re.M)        # 有序列表
    t = re.sub(r"^[ \t]*#{1,6}[ \t]+", "", t, flags=re.M)       # 标题 #
    t = re.sub(r"^[ \t]*-{3,}[ \t]*$", "", t, flags=re.M)       # 分隔线 ---
    t = re.sub(r"\[([\s\S]+?)\]\(([\s\S]+?)\)", r"\1", t)       # 链接
    t = t.replace("`", "")                                      # 行内代码
    return t


def count(text: str) -> dict:
    cleaned = strip_markdown_noise(text)
    cjk = len(CJK_RE.findall(cleaned))
    no_ws = re.sub(r"\s", "", cleaned)
    return {
        "cjk_only": cjk,                       # 纯汉字
        "with_punct": len(no_ws),              # 含标点（去空白）
        "punctuation_only": len(no_ws) - cjk,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("file", nargs="?")
    ap.add_argument("--body-start", type=int, default=None)
    ap.add_argument("--body-end", type=int, default=None)
    ap.add_argument("--exclude", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("-h", "--help", action="store_true")
    args = ap.parse_args(argv)

    if args.help or not args.file:
        sys.stderr.write(
            "用法：python3 count_cjk.py <文件> [--body-start N] [--body-end N] "
            "[--exclude 行,行] [--json]\n"
        )
        return 1

    try:
        with open(args.file, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        sys.stderr.write(f"[错误] 文件不存在：{args.file}\n")
        return 1

    lines = raw.split("\n")
    total = len(lines)

    start = args.body_start or 1
    end = args.body_end or total
    if start < 1 or end > total or start > end:
        sys.stderr.write(
            f"[错误] 行号越界：文件共 {total} 行，收到 start={start} end={end}\n"
        )
        return 2

    excludes = set()
    if args.exclude.strip():
        for piece in args.exclude.split(","):
            p = piece.strip()
            if not p:
                continue
            if not p.lstrip("-").isdigit():
                sys.stderr.write(f"[错误] --exclude 含非数字项：{p}\n")
                return 1
            excludes.add(int(p))

    seg = [lines[i - 1] for i in range(start, end + 1) if i not in excludes]
    result = count("\n".join(seg))

    if args.json:
        out = dict(result)
        out.update({
            "file": args.file,
            "body_start": start,
            "body_end": end,
            "excluded_lines": sorted(excludes),
            "total_lines": total,
        })
        sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
        return 0

    ex_str = f"，已排除行 {','.join(map(str, sorted(excludes)))}" if excludes else ""
    w = sys.stdout.write
    w(f"文件：{args.file}\n")
    w(f"统计范围：第 {start}–{end} 行（共 {total} 行）{ex_str}\n")
    w("-" * 44 + "\n")
    w(f"纯汉字数（不含标点）：{result['cjk_only']}\n")
    w(f"含标点数（去空白）  ：{result['with_punct']}\n")
    w(f"其中标点等非汉字    ：{result['punctuation_only']}\n")
    w("-" * 44 + "\n")
    w("提示：用户给定字数区间时，两个口径都应落在区间内才算达标。\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
