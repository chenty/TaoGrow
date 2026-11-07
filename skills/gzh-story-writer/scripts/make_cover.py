#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""封面两件套生成器 —— 公众号封面（2.35:1 大图 + 1:1 缩略图 + 横排合并）

用途
    给一张「无字」的水彩/插画底图，套上统一的封面版式，一次产出三张：
      1. 大图   2.35:1   用于公众号文章页顶部满宽显示
      2. 缩略图 1:1      用于分享卡片、对话列表（圆形裁切后主标题仍完整）
      3. 合并图 横排      两张并排，用于人工检查版式是否统一

    核心是**二分字号校验**：用像素扫描求出底图上「画面真正的上沿」，
    再二分搜索主标题的最大可用字号，保证文字块底边绝不压到画面。
    这样换标题、换底图都不用再手工试字号。

用法
    python3 scripts/make_cover.py \
        --art cover-art.png \
        --column "热闹翻过去" \
        --title "写谁的名字" \
        --subtitle "给女儿出首付那天，她把这句话咽了回去" \
        --outdir out/

    # 常见变体
    --overlay                 叠字遮罩模式：裁满幅→顶部半透明纸面遮罩→文字压图
                              （适合画面顶到边、没有整条留白带的底图；
                              配套 --mask-height/--mask-alpha/--mask-curve/
                              --title-size/--thumb-center-x/--overlay-crop-top）
    --merged-gap 0 --merged-pad 0   合并图无间隔满幅（默认 52/44 有留白）
    --no-thumbnail            只出大图
    --no-merged               不出合并图
    --title-w 900             大图标题最大宽度（默认 900）
    --font-serif              改用宋体（默认龙藏体；--font-sans 改黑体）
    --font <路径>             指定字体文件（优先级最高，覆盖默认与家族选项）
    --check-font              只报告默认龙藏体的解析结果，不出图

产物
    01-封面大图-2.35x1.png
    02-封面缩略图-1x1.png
    03-合并-横排.png
    并打印一张「安全区报告」，列出字体、字号、文字底边与画面边界的关系。

依赖
    仅 Pillow 与 numpy。默认字体统一为龙藏体 Long Cang（连笔松弛手写风，
    SIL OFL 1.1，可免费商用）：按 --font > 环境变量 TAOZI_FONT_LONGCANG >
    系统/用户字体目录顺序查找；未安装时明确警告并回退系统 CJK（宋体→黑体），
    再不行才回退 DejaVu（无中文字形）。安装见 scripts/setup.sh。

版式（与账号视觉体系一致）
    栏目名（不带编号）→ 主标题 → 一道强调色短线 → 副标题
    三段左对齐、竖排、同一 x 起点；两张图用同一套逻辑，因此并排看是一套。
"""

import argparse
import glob
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("❌ 需要 Pillow：pip install Pillow")

try:
    import numpy as np
except ImportError:
    sys.exit("❌ 需要 numpy：pip install numpy")


# ---------------------------------------------------------------- 字体
#
# 仓库默认字体（2026-10-28 统一）：龙藏体 Long Cang —— 连笔、松弛舒展的
# 手写风，SIL OFL 1.1 开源可商用（Google Fonts 收录）。它只有一个字重
# （Regular 400），故栏目名/主标题/副标题共用同一文件，层级靠字号与墨色
# 区分；其笔画偏细，未显式传 --col-size/--sub-size 时次级文字自动放大一档
# （32/34 px，印刷体仍为 26/28 px）以保住小字可读性。
# 优先级：--font 指定文件 > 环境变量 TAOZI_FONT_LONGCANG > 字体目录查找。
# 账号/用户显式指定其他字体时，用 --font-serif / --font-sans / --font 覆盖。

DEFAULT_FONT_FAMILY = "Long Cang"
LONGCANG_DOWNLOAD = ("https://raw.githubusercontent.com/google/fonts/"
                     "main/ofl/longcang/LongCang-Regular.ttf")
LONGCANG_HINT = (
    "安装龙藏体：从 Google Fonts 下载 LongCang-Regular.ttf\n"
    f"  {LONGCANG_DOWNLOAD}\n"
    "  放到 ~/.local/share/fonts/（Linux）/ ~/Library/Fonts/（macOS）/\n"
    "  C:/Windows/Fonts/（Windows），或用 --font <路径> / 环境变量\n"
    "  TAOZI_FONT_LONGCANG=<路径> 指定；也可跑 scripts/setup.sh --install-font。"
)
LONGCANG_FILENAMES = ("LongCang-Regular.ttf", "LongCang.ttf",
                      "Long Cang-Regular.ttf", "Long Cang.ttf", "龙藏体.ttf")
FONT_DIRS = [
    "~/.local/share/fonts", "~/.fonts",
    "/usr/local/share/fonts", "/usr/share/fonts",
    "~/Library/Fonts", "/Library/Fonts", "/System/Library/Fonts",
    "C:/Windows/Fonts", "~/AppData/Local/Microsoft/Windows/Fonts",
]
SERIF_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/System/Library/Fonts/Songti.ttc",
    "C:/Windows/Fonts/simsun.ttc",
]
SANS_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "C:/Windows/Fonts/msyh.ttc",
]
# 未显式指定字号时的次级文字默认字号：(栏目名, 副标题)
SECONDARY_SIZES = {"Long Cang": (32, 34), "other": (26, 28)}


def _expand(path):
    return os.path.expanduser(os.path.expandvars(path))


def _first_existing(candidates):
    for p in candidates:
        p = _expand(p)
        if os.path.exists(p):
            return p
    return None


def find_longcang():
    """定位龙藏体文件；找不到返回 None。"""
    env = os.environ.get("TAOZI_FONT_LONGCANG") or os.environ.get("LONGCANG_FONT")
    if env:
        p = _expand(env)
        if os.path.exists(p):
            return p
        sys.stderr.write(f"⚠️ 环境变量指定的龙藏体不存在：{p}，改走目录查找\n")
    hit = _first_existing([os.path.join(d, n)
                           for d in FONT_DIRS for n in LONGCANG_FILENAMES])
    if hit:
        return hit
    # 目录内任意层级、任意命名变体（发行包常装在子目录里）
    for d in FONT_DIRS:
        d = _expand(d)
        if not os.path.isdir(d):
            continue
        for pat in ("**/*LongCang*.ttf", "**/*LongCang*.ttc", "**/*LongCang*.otf",
                    "**/*Long Cang*.ttf", "**/*Long Cang*.otf",
                    "**/*龙藏*.ttf", "**/*龙藏*.otf"):
            hits = sorted(glob.glob(os.path.join(d, pat), recursive=True))
            # 大小写变体在大小写敏感文件系统上需另扫一遍
            hits += sorted(glob.glob(os.path.join(
                d, pat.replace("LongCang", "longcang")), recursive=True))
            if hits:
                return hits[0]
    return None


def _pair_from(candidates):
    found = [p for p in (_expand(c) for c in candidates) if os.path.exists(p)]
    if len(found) >= 2:
        return found[0], found[1]
    if len(found) == 1:
        return found[0], found[0]
    return None


def _dejavu():
    return _first_existing(("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))


def resolve_fonts(family=DEFAULT_FONT_FAMILY, font_path=None):
    """返回 (标题字体, 常规字体, 说明, 实际家族)。

    龙藏体只有一个字重，两项为同一文件。找不到目标家族时逐级回退
    （龙藏体→宋体→黑体→DejaVu），每次回退都写明原因进 stderr 并体现在
    「说明」里——绝不静默换字体，安全区报告会把实际字体打出来供复核。
    """
    if font_path:
        p = _expand(font_path)
        if not os.path.exists(p):
            sys.exit(f"❌ --font 指定的字体文件不存在：{p}")
        base = os.path.basename(p).lower().replace(" ", "")
        is_lc = "longcang" in base or "龙藏" in os.path.basename(p)
        return p, p, f"自定义字体 {p}", ("Long Cang" if is_lc else "other")

    chain = {"Long Cang": ["Long Cang", "serif", "sans"],
             "serif": ["serif", "sans"],
             "sans": ["sans", "serif"]}[family]
    labels = {"Long Cang": "龙藏体 Long Cang", "serif": "宋体", "sans": "黑体"}
    for fam in chain:
        if fam == "Long Cang":
            p = find_longcang()
            if p:
                note = "龙藏体 Long Cang（仓库默认）" if family == "Long Cang" else labels[fam]
                return p, p, f"{note} {p}", "Long Cang"
        else:
            pair = _pair_from(SERIF_CANDIDATES if fam == "serif" else SANS_CANDIDATES)
            if pair:
                if fam != family:
                    sys.stderr.write(
                        f"⚠️ 未找到{labels[family]}，回退{labels[fam]}。\n")
                    if family == "Long Cang":
                        sys.stderr.write(LONGCANG_HINT + "\n")
                return pair[0], pair[1], f"{labels[fam]} {pair[0]}", "other"
    p = _dejavu()
    if p:
        # 回退：DejaVu 不含中文字形，会渲染成方块，但至少不中断
        sys.stderr.write("⚠️ 未找到任何 CJK 字体，中文将无法正确显示。\n"
                         + LONGCANG_HINT + "\n")
        return p, p, f"DejaVu（无中文字形，仅兜底） {p}", "other"
    sys.exit("❌ 未找到任何可用字体。\n" + LONGCANG_HINT)


def pick_font(sans=False):
    """兼容旧接口：返回 (标题字体, 常规字体)。默认已改为龙藏体。"""
    font_b, font_r, _label, _fam = resolve_fonts("sans" if sans else "Long Cang")
    return font_b, font_r


def missing_glyphs(text, font_path, size=36):
    """检出字体里没有字形、会渲染成空白的字符（如龙藏体缺 `·` U+00B7）。

    龙藏体仅约 GB2312 字量，缺字时不是方框而是空白占位，目视容易漏检，
    故逐字试绘：整幅无墨迹即判缺字（空白字符除外）。
    """
    try:
        font = ImageFont.truetype(font_path, size)
    except Exception:
        return []
    out = []
    for ch in dict.fromkeys(text or ""):
        if ch.isspace():
            continue
        tile = Image.new("L", (size * 2, size * 2), 0)
        ImageDraw.Draw(tile).text((size // 2, size // 2), ch, font=font, fill=255)
        if tile.getbbox() is None:
            out.append(ch)
    return out


# ---------------------------------------------------------------- 画布工具

def paper_color(art):
    """取底图四角的平均色，作为补画布与渐隐的纸面底色。"""
    a = np.asarray(art.convert("RGB"), dtype=float)
    h, w, _ = a.shape
    k = max(4, min(h, w) // 20)
    corners = [a[:k, :k], a[:k, -k:], a[-k:, :k], a[-k:, -k:]]
    mean = np.mean([c.reshape(-1, 3).mean(axis=0) for c in corners], axis=0)
    return tuple(int(round(v)) for v in mean)


def right_fade(img, cream, fade_w=200):
    """右边缘渐隐到纸面色，避免补出来的画布出现生硬接缝。"""
    w, h = img.size
    fade_w = min(fade_w, w // 3)
    a = np.asarray(img, dtype=float)
    mask = np.ones(w)
    for i in range(fade_w):
        mask[w - fade_w + i] = (1 - (i + 1) / fade_w) ** 1.6
    bg = np.array(cream, dtype=float)
    for c in range(3):
        a[:, :, c] = a[:, :, c] * mask[None, :] + bg[c] * (1 - mask[None, :])
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def find_art_top(art, x0_ratio=0.08, x1_ratio=0.72, threshold=215,
                 run=20, edge_skip_ratio=0.03):
    """像素扫描：找出「左侧文字区」里画面真正的上沿 y。

    只扫文字会落在的横向区间，避开右上的装饰元素（如挂盆绿植）。

    两个防误判处理：
      1. 跳过顶部 edge_skip 行——水彩纸常有撕边/描边，单像素级暗线不是画面；
      2. 要求「连续 run 行里至少七成有内容」才算画面起点，孤立的暗线会被忽略。

    返回 (art_top, blank)。blank=True 表示扫不出画面（整片空白）。
    """
    a = np.asarray(art.convert("L"), dtype=float)
    h, w = a.shape
    x0, x1 = int(w * x0_ratio), int(w * x1_ratio)
    start = max(1, int(h * edge_skip_ratio))
    has_content = (a[:, x0:x1].min(axis=1) < threshold).astype(int)

    need = int(run * 0.7)
    for y in range(start, h - run):
        if has_content[y:y + run].sum() >= need:
            return y, False
    # 兜底：整条都找不���连续带，退回到第一处单行内容
    for y in range(start, h):
        if has_content[y]:
            return y, False
    return None, True


# ---------------------------------------------------------------- 版式求解

STACK_GAPS = dict(gap=16, bar_gap=18, sub_gap=16, bar_len=96)


def stack_bottom(probe, x, y_top, sizes, gaps, column, title, subtitle):
    """返回 (文字块底边 y, 主标题宽度 px)。纯计算，不落笔。"""
    f_col = ImageFont.truetype(sizes["font_b"], sizes["col"])
    f_big = ImageFont.truetype(sizes["font_b"], sizes["big"])
    f_sub = ImageFont.truetype(sizes["font_r"], sizes["sub"])
    cb = probe.textbbox((x, y_top), column, font=f_col)
    ty = cb[3] + gaps["gap"]
    bb = probe.textbbox((x, ty), title, font=f_big)
    ly = bb[3] + gaps["bar_gap"]
    sy = ly + gaps["sub_gap"]
    sb = probe.textbbox((x, sy), subtitle, font=f_sub) if subtitle else (0, 0, 0, ly)
    return sb[3], bb[2] - bb[0]


def fit_title_size(probe, x, y_top, limit_y, max_w, base_sizes, gaps,
                   column, title, subtitle, lo=30, hi=280):
    """二分搜索主标题的最大可用字号。

    约束两条：① 文字块底边 < limit_y（不越过画面）
              ② 主标题宽度 < max_w（不越出安全区）
    找不到可用字号时返回 lo（并由调用方断言校验）。
    """
    # 先确认最小字号都放得下，否则二分会在 lo 上「侥幸通过」
    smallest = dict(base_sizes, big=lo)
    b_min, w_min = stack_bottom(probe, x, y_top, smallest, gaps, column, title, subtitle)
    if b_min >= limit_y or w_min >= max_w:
        raise SystemExit(
            f"❌ 连最小字号 {lo}px 都放不下：文字底边 {b_min} / 上限 {limit_y}，"
            f"标题宽 {w_min} / 上限 {max_w}。\n"
            f"   请缩小 --col-size 或 --sub-size、上移 --y-top，"
            f"或减小 --min-gap。")

    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        sizes = dict(base_sizes, big=mid)
        bottom, width = stack_bottom(probe, x, y_top, sizes, gaps, column, title, subtitle)
        if bottom < limit_y and width < max_w:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def draw_stack(d, x, y_top, sizes, gaps, column, title, subtitle, colors):
    """按求得的字号把三段文字画上去。"""
    f_col = ImageFont.truetype(sizes["font_b"], sizes["col"])
    f_big = ImageFont.truetype(sizes["font_b"], sizes["big"])
    f_sub = ImageFont.truetype(sizes["font_r"], sizes["sub"])

    cb = d.textbbox((x, y_top), column, font=f_col)
    d.text((x, y_top), column, font=f_col, fill=colors["muted"])

    ty = cb[3] + gaps["gap"]
    d.text((x, ty), title, font=f_big, fill=colors["ink"])
    bb = d.textbbox((x, ty), title, font=f_big)

    ly = bb[3] + gaps["bar_gap"]
    d.line([(x + 3, ly), (x + 3 + gaps["bar_len"], ly)],
           fill=colors["accent"], width=max(3, sizes["big"] // 30))

    sy = ly + gaps["sub_gap"]
    if subtitle:
        d.text((x, sy), subtitle, font=f_sub, fill=colors["muted"])


# ---------------------------------------------------------------- 两张图

def build_main(art, cream, args, fonts, colors):
    target_ratio = args.ratio
    h = args.height
    w = int(round(h * target_ratio))
    canvas = Image.new("RGB", (w, h), cream)
    canvas.paste(right_fade(art, cream, args.fade), (0, 0))

    art_top, blank = find_art_top(art, args.scan_x0, args.scan_x1,
                                  args.scan_threshold, args.scan_run)
    if blank or art_top is None:
        art_top = int(h * args.fallback_art_top)
        note = "未检出画面边界，按 fallback 处理"
    else:
        note = "像素扫描测得"

    limit_y = art_top - args.min_gap
    base = dict(font_b=fonts[0], font_r=fonts[1], col=args.col_size, sub=args.sub_size)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    big = fit_title_size(probe, args.x, args.y_top, limit_y,
                         min(args.title_w, w - args.x - 40),
                         base, STACK_GAPS, args.column, args.title, args.subtitle)
    sizes = dict(base, big=big)
    bottom, width = stack_bottom(probe, args.x, args.y_top, sizes, STACK_GAPS,
                                 args.column, args.title, args.subtitle)

    d = ImageDraw.Draw(canvas)
    draw_stack(d, args.x, args.y_top, sizes, STACK_GAPS,
               args.column, args.title, args.subtitle, colors)

    report = dict(part="大图", size=f"{w}x{h}", ratio=f"{w/h:.2f}:1",
                  title_px=big, title_w=width, bottom=bottom,
                  art_top=art_top, gap=art_top - bottom, source=note)
    if bottom >= art_top:
        raise SystemExit(f"❌ 大图文字压图：底边 {bottom} >= 画面上沿 {art_top}；"
                         f"请调小 --col-size / --sub-size，或加大 --y-top 之外的余量")
    return canvas, report


def build_thumb(art, cream, args, fonts, colors):
    side = args.thumb_size
    art_h = int(side * args.thumb_art_ratio)
    aw = max(1, int(art_h * art.size[0] / art.size[1]))
    scaled = art.resize((aw, art_h), Image.LANCZOS)
    if aw >= side:
        # 水平裁切起点：0=最左, 1=最右。默认 0（保留左侧留白）。
        # 需要把右侧人物/主体纳入缩略图时可调大。
        xoff = int((aw - side) * max(0.0, min(1.0, args.thumb_crop_x)))
        crop = scaled.crop((xoff, 0, xoff + side, art_h))
    else:
        crop = scaled

    canvas = Image.new("RGB", (side, side), cream)
    canvas.paste(right_fade(crop, cream, args.fade // 2), (0, side - art_h))

    top_edge = side - art_h
    limit_y = top_edge - args.min_gap
    base = dict(font_b=fonts[0], font_r=fonts[1], col=args.col_size, sub=args.sub_size)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    big = fit_title_size(probe, args.thumb_x, args.thumb_y, limit_y,
                         side - args.thumb_x - 40,
                         base, STACK_GAPS, args.column, args.title, args.subtitle)
    sizes = dict(base, big=big)
    bottom, width = stack_bottom(probe, args.thumb_x, args.thumb_y, sizes, STACK_GAPS,
                                 args.column, args.title, args.subtitle)

    d = ImageDraw.Draw(canvas)
    draw_stack(d, args.thumb_x, args.thumb_y, sizes, STACK_GAPS,
               args.column, args.title, args.subtitle, colors)

    report = dict(part="缩略图", size=f"{side}x{side}", ratio="1.00:1",
                  title_px=big, title_w=width, bottom=bottom,
                  art_top=top_edge, gap=top_edge - bottom,
                  source=f"画面占下 {int(args.thumb_art_ratio*100)}%")
    if bottom >= top_edge:
        raise SystemExit(f"❌ 缩略图文字压图：底边 {bottom} >= 画面起点 {top_edge}")
    return canvas, report


# ---------------------------------------------------------------- 叠字遮罩模式

def apply_top_mask(img, cream, mask_height=0.55, max_alpha=235, curve=1.25):
    """在图上半部叠加渐隐纸面遮罩，供文字直接压在画面上。

    alpha 从顶部 max_alpha 按幂曲线（指数 curve，>1 时顶部更实、过渡更缓）
    渐隐到 mask_height 比例处归零——遮罩是「纸面纱」而不是死色块，
    水彩纸纹仍隐约透出。返回新图。
    """
    a = np.asarray(img, dtype=float).copy()
    h, _, _ = a.shape
    fade_h = max(1, int(h * mask_height))
    alpha = np.zeros(h)
    ys = np.arange(fade_h)
    alpha[:fade_h] = max_alpha * (1.0 - (ys / fade_h) ** curve)
    bg = np.array(cream, dtype=float)
    for c in range(3):
        a[:, :, c] = a[:, :, c] * (1 - alpha[:, None] / 255) + bg[c] * (alpha[:, None] / 255)
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def crop_to_ratio(art, ratio, anchor_y=0.5, crop_y_from_top=0):
    """把底图按目标比例裁成满幅（图片上叠字模式用，不再补画布留白）。

    anchor_y：裁切窗口垂直锚点（0=顶对齐 0.5=居中 1=底对齐）。
    crop_y_from_top：先从底部最多裁掉这么多像素之外的顶部余量——
    即优先保画面下部（人物主体常在下部）。
    """
    w, h = art.size
    target_h = int(round(w / ratio))
    if target_h <= h:
        # 竖向裁：默认底对齐（人物在下部），crop_y_from_top 限制顶部最多裁掉多少
        top = h - target_h
        top = min(top, crop_y_from_top) if crop_y_from_top else top
        top = max(0, min(top, h - target_h))
        return art.crop((0, top, w, top + target_h))
    # 横向裁（底图比目标更"扁"）：水平居中
    target_w = int(round(h * ratio))
    x0 = max(0, (w - target_w) // 2)
    return art.crop((x0, 0, x0 + target_w, h))


def draw_text_on_image(img, fonts, colors, column, title, subtitle,
                       x, y_top, title_size, col_size, sub_size,
                       bar_len=96, bar_gap=18, gap=16, sub_gap=16):
    """把文字栈直接画在图上（叠字模式），返回 (新图, 文字底边 y)。"""
    img = img.copy()
    d = ImageDraw.Draw(img)
    sizes = dict(font_b=fonts[0], font_r=fonts[1],
                 col=col_size, sub=sub_size, big=title_size)
    draw_stack(d, x, y_top, sizes,
               dict(gap=gap, bar_gap=bar_gap, sub_gap=sub_gap, bar_len=bar_len),
               column, title, subtitle, colors)
    bottom, _ = stack_bottom(ImageDraw.Draw(Image.new("RGB", (10, 10))),
                             x, y_top, sizes,
                             dict(gap=gap, bar_gap=bar_gap, sub_gap=sub_gap,
                                  bar_len=bar_len),
                             column, title, subtitle)
    return img, bottom


def build_main_overlay(art, cream, args, fonts, colors):
    """叠字模式大图：裁满幅 → 顶部遮罩 → 文字直接压图。

    字号策略：标题宽度受 --title-w 约束做二分上限，但不再有"画面上沿"
    概念（遮罩保证可读），故以宽度为唯一硬约束、--title-size 可显式钉死。
    """
    crop = crop_to_ratio(art, args.ratio,
                         anchor_y=0.5, crop_y_from_top=args.overlay_crop_top)
    cream = paper_color(crop)          # 裁切后纸面色可能与原图略异，取裁后为准
    canvas = apply_top_mask(crop, cream,
                            mask_height=args.mask_height,
                            max_alpha=args.mask_alpha,
                            curve=args.mask_curve)
    w, h = canvas.size
    max_w = min(args.title_w, w - args.x - 40)
    if args.title_size:
        big = args.title_size
    else:
        # 按宽度上限二分：字号越大标题越宽，找不超宽的最大字号
        probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        lo, hi = 60, 260
        best = lo
        f = lambda s: ImageFont.truetype(fonts[0], s)
        while lo <= hi:
            mid = (lo + hi) // 2
            bb = probe.textbbox((0, 0), args.title, font=f(mid))
            if bb[2] - bb[0] < max_w:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        big = best
    canvas, bottom = draw_text_on_image(
        canvas, fonts, colors, args.column, args.title, args.subtitle,
        args.x, args.y_top, big, args.col_size, args.sub_size,
        bar_len=args.bar_len)
    if bottom > h * 0.6 and not args.title_size:
        sys.stderr.write(f"⚠️ 文字底边 {bottom} 超过画面高度 60%，"
                         f"遮罩可能盖不住，建议加 --mask-height 或减字号\n")
    report = dict(part="大图", size=f"{w}x{h}", ratio=f"{w/h:.2f}:1",
                  title_px=big, title_w=0, bottom=bottom, art_top=0,
                  gap=h - bottom, source=f"叠字遮罩模式（遮罩高 {int(args.mask_height*100)}%）")
    return canvas, report


def build_thumb_overlay(art, cream, args, fonts, colors):
    """叠字模式缩略图：以主体为中心方裁 → 遮罩 → 叠字。"""
    w, h = art.size
    win = min(w, h)
    cx = int(w * args.thumb_center_x)
    x0 = max(0, min(cx - win // 2, w - win))
    y0 = max(0, min(h - win, int(h * args.thumb_center_y - win // 2)))
    sq = art.crop((x0, y0, x0 + win, y0 + win)).resize(
        (args.thumb_size, args.thumb_size), Image.LANCZOS)
    cream = paper_color(sq)
    canvas = apply_top_mask(sq, cream,
                            mask_height=args.mask_height,
                            max_alpha=args.mask_alpha,
                            curve=args.mask_curve)
    canvas, bottom = draw_text_on_image(
        canvas, fonts, colors, args.column, args.title, args.subtitle,
        args.thumb_x, args.thumb_y, args.thumb_title_size, 26, 25,
        bar_len=72, bar_gap=14, gap=14, sub_gap=12)
    report = dict(part="缩略图", size=f"{args.thumb_size}x{args.thumb_size}",
                  ratio="1.00:1", title_px=args.thumb_title_size,
                  title_w=0, bottom=bottom, art_top=0,
                  gap=args.thumb_size - bottom,
                  source=f"叠字遮罩模式（中心 x={args.thumb_center_x}）")
    return canvas, report


def build_merged(main, thumb, cream, gap=52, pad=44):
    w = pad * 2 + main.size[0] + gap + thumb.size[0]
    h = pad * 2 + max(main.size[1], thumb.size[1])
    canvas = Image.new("RGB", (w, h), cream)
    canvas.paste(main, (pad, pad + (h - pad * 2 - main.size[1]) // 2))
    canvas.paste(thumb, (pad + main.size[0] + gap,
                         pad + (h - pad * 2 - thumb.size[1]) // 2))
    return canvas


# ---------------------------------------------------------------- 入口

def main():
    # --check-font 只报字体解析结果，不要求 --art 等出图参数，故先行处理
    if "--check-font" in sys.argv:
        explicit = None
        if "--font" in sys.argv:
            i = sys.argv.index("--font")
            explicit = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
        _b, _r, label, _fam = resolve_fonts(DEFAULT_FONT_FAMILY, explicit)
        print(f"默认字体解析：{label}")
        return

    ap = argparse.ArgumentParser(description="公众号封面两件套生成器（含二分字号校验）")
    ap.add_argument("--art", required=True, help="无字底图路径")
    ap.add_argument("--column", required=True, help="栏目名（不要带编号）")
    ap.add_argument("--title", required=True, help="主标题，建议 4-6 字")
    ap.add_argument("--subtitle", default="", help="副标题，点出处境")
    ap.add_argument("--outdir", default=".", help="输出目录")

    ap.add_argument("--ratio", type=float, default=2.35, help="大图长宽比（默认 2.35）")
    ap.add_argument("--height", type=int, default=768, help="大图高度（默认 768）")
    ap.add_argument("--thumb-size", type=int, default=768, help="缩略图边长（默认 768）")
    ap.add_argument("--thumb-crop-x", type=float, default=0.0,
                    help="缩略图水平裁切起点比例 0=最左 1=最右（默认 0）")
    ap.add_argument("--thumb-art-ratio", type=float, default=0.60,
                    help="缩略图中画面所占高度比例（默认 0.60）")

    ap.add_argument("--col-size", type=int, default=None,
                    help="栏目名字号（默认：龙藏体 32 / 印刷体 26）")
    ap.add_argument("--sub-size", type=int, default=None,
                    help="副标题字号（默认：龙藏体 34 / 印刷体 28）")
    ap.add_argument("--x", type=int, default=112, help="大图文字左边距（默认 112）")
    ap.add_argument("--y-top", type=int, default=24, help="大图文字起始 y（默认 24）")
    ap.add_argument("--thumb-x", type=int, default=64, help="缩略图文字左边距（默认 64）")
    ap.add_argument("--thumb-y", type=int, default=46, help="缩略图文字起始 y（默认 46）")
    ap.add_argument("--title-w", type=int, default=900, help="大图标题最大宽度（默认 900）")
    ap.add_argument("--min-gap", type=int, default=24, help="文字底边与画面的最小间隙（默认 24）")
    ap.add_argument("--fade", type=int, default=200, help="右边缘渐隐宽度（默认 200）")

    ap.add_argument("--scan-x0", type=float, default=0.08, help="扫描画面边界：左比例")
    ap.add_argument("--scan-x1", type=float, default=0.72, help="扫描画面边界：右比例")
    ap.add_argument("--scan-threshold", type=int, default=215,
                    help="判定「有画面」的灰度阈值（默认 215）")
    ap.add_argument("--scan-run", type=int, default=20,
                    help="判定画面起点所需的连续行数（默认 20）")
    ap.add_argument("--fallback-art-top", type=float, default=0.42,
                    help="扫描失败时画面顶边的估计比例（默认 0.42）")

    ap.add_argument("--ink", default="58,50,38", help="主标题墨色 RGB")
    ap.add_argument("--muted", default="146,126,104", help="次要文字 RGB")
    ap.add_argument("--accent", default="201,106,61", help="强调色 RGB（短线）")
    font_group = ap.add_mutually_exclusive_group()
    font_group.add_argument("--font-family",
                            choices=["Long Cang", "serif", "sans"], default="Long Cang",
                            help="字体家族：Long Cang=龙藏体（默认）/ serif=宋体 / sans=黑体")
    font_group.add_argument("--font-serif", action="store_const",
                            const="serif", dest="font_family", help="改用宋体")
    font_group.add_argument("--font-sans", action="store_const",
                            const="sans", dest="font_family", help="改用黑体")
    ap.add_argument("--font", dest="font_path", default=None,
                    help="指定字体文件路径（优先级最高，覆盖 --font-family）")
    ap.add_argument("--check-font", action="store_true",
                    help="只报告默认字体（龙藏体）的解析结果，不出图")

    ap.add_argument("--no-thumbnail", action="store_true", help="只出大图")
    ap.add_argument("--no-merged", action="store_true", help="不出合并图")

    # ---- 叠字遮罩模式（--overlay）----
    ap.add_argument("--overlay", action="store_true",
                    help="叠字模式：裁满幅→顶部半透明纸面遮罩→文字压图（画面利用率最高，"
                         "适合画面顶到边、没有整条留白带的底图）")
    ap.add_argument("--mask-height", type=float, default=0.55,
                    help="遮罩渐隐完成高度占图比例（叠字模式，默认 0.55）")
    ap.add_argument("--mask-alpha", type=int, default=235,
                    help="遮罩顶部不透明度 0-255（叠字模式，默认 235）")
    ap.add_argument("--mask-curve", type=float, default=1.25,
                    help="遮罩渐隐幂曲线指数，>1 顶部更实（叠字模式，默认 1.25）")
    ap.add_argument("--title-size", type=int, default=None,
                    help="叠字模式主标题字号（默认按 --title-w 宽度二分自动）")
    ap.add_argument("--thumb-title-size", type=int, default=84,
                    help="叠字模式缩略图标题字号（默认 84）")
    ap.add_argument("--thumb-center-x", type=float, default=0.5,
                    help="叠字模式缩略图方裁中心 x 比例 0-1（默认 0.5）")
    ap.add_argument("--thumb-center-y", type=float, default=0.5,
                    help="叠字模式缩略图方裁中心 y 比例 0-1（默认 0.5）")
    ap.add_argument("--overlay-crop-top", type=int, default=0,
                    help="叠字模式大图竖向裁切时最多从顶部裁掉的像素（默认 0=底对齐裁切）")
    ap.add_argument("--bar-len", type=int, default=96,
                    help="强调色短线长度（默认 96）")
    ap.add_argument("--merged-gap", type=int, default=52,
                    help="合并图两图间隔（默认 52；0=无间隔紧贴）")
    ap.add_argument("--merged-pad", type=int, default=44,
                    help="合并图外边距（默认 44；0=满幅）")
    args = ap.parse_args()

    if not os.path.exists(args.art):
        sys.exit(f"❌ 底图不存在：{args.art}")
    if len(args.title) > 8:
        sys.stderr.write(f"⚠️ 主标题 {len(args.title)} 字，超过 8 字建议缩短"
                         f"（封面大字应一眼读完）\n")

    os.makedirs(args.outdir, exist_ok=True)
    art = Image.open(args.art).convert("RGB")
    cream = paper_color(art)
    fonts = resolve_fonts(args.font_family, args.font_path)
    font_label, actual_family = fonts[2], fonts[3]
    # 次级字号：未显式指定时按实际字体补默认（龙藏体笔画细，放一档）
    sec_col, sec_sub = SECONDARY_SIZES[
        "Long Cang" if actual_family == "Long Cang" else "other"]
    if args.col_size is None:
        args.col_size = sec_col
    if args.sub_size is None:
        args.sub_size = sec_sub
    # 缺字检查：缺字会渲染成空白而非方框，必须在出图前报出来
    missing_chars = list(dict.fromkeys(
        missing_glyphs(args.column + args.title, fonts[0])
        + missing_glyphs(args.subtitle, fonts[1])))
    if missing_chars:
        shown = "、".join(f"{c}(U+{ord(c):04X})" for c in missing_chars)
        sys.stderr.write(
            f"⚠️ 当前字体缺以下字符，成图中将显示为空白：{shown}\n"
            "   请换用等价标点（如 `·` 改 `•`）、改字，"
            "或用 --font-serif / --font-sans / --font 换字体后重出。\n")
    colors = dict(
        ink=tuple(int(v) for v in args.ink.split(",")),
        muted=tuple(int(v) for v in args.muted.split(",")),
        accent=tuple(int(v) for v in args.accent.split(",")),
    )

    print(f"底图 {art.size[0]}x{art.size[1]}（{art.size[0]/art.size[1]:.2f}:1）"
          f"　纸面色 RGB{cream}")
    print(f"字体 {font_label}　栏目 {args.col_size}px / 副标题 {args.sub_size}px"
          + ("　[叠字遮罩模式]" if args.overlay else ""))

    if args.overlay:
        main_img, r1 = build_main_overlay(art, cream, args, fonts, colors)
    else:
        main_img, r1 = build_main(art, cream, args, fonts, colors)
    p1 = os.path.join(args.outdir, "01-封面大图-2.35x1.png")
    main_img.save(p1)
    print(f"✅ {p1}")

    outputs = [p1]
    if not args.no_thumbnail:
        if args.overlay:
            thumb_img, r2 = build_thumb_overlay(art, cream, args, fonts, colors)
        else:
            thumb_img, r2 = build_thumb(art, cream, args, fonts, colors)
        p2 = os.path.join(args.outdir, "02-封面缩略图-1x1.png")
        thumb_img.save(p2)
        print(f"✅ {p2}")
        outputs.append(p2)

        if not args.no_merged:
            merged = build_merged(main_img, thumb_img, cream,
                                  gap=args.merged_gap, pad=args.merged_pad)
            p3 = os.path.join(args.outdir, "03-合并-横排.png")
            merged.save(p3)
            print(f"✅ {p3}　{merged.size[0]}x{merged.size[1]}")
            outputs.append(p3)
        reports = [r1, r2]
    else:
        reports = [r1]

    # ---- 安全区报告（二分校验的结果，供人工复核） ----
    print("\n安全区报告")
    print("-" * 62)
    print(f"  字体 {font_label}")
    if missing_chars:
        print(f"  ⚠️ 缺字（成图为空白）：{'、'.join(missing_chars)}")
    for r in reports:
        print(f"  {r['part']:<4} {r['size']:<10} {r['ratio']:<8} "
              f"标题 {r['title_px']}px / 宽 {r['title_w']}px")
        print(f"       文字底边 {r['bottom']}　画面上沿 {r['art_top']}　"
              f"余量 {r['gap']}px　（{r['source']}）")
    print("-" * 62)
    print("  余量为正即代表文字未压画面；本工具在压图时会直接报错退出。")


if __name__ == "__main__":
    main()
