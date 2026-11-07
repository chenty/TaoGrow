#!/usr/bin/env bash
# 环境自检：写作脚本只用 Python/Node 标准库；make_cover.py 需要 Pillow+numpy
# 与默认字体龙藏体（Long Cang，OFL 可商用）。加 --install-font 可把龙藏体
# 下载到当前用户的字体目录（不写系统目录，不需要管理员权限）。
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FONT_URL="https://raw.githubusercontent.com/google/fonts/main/ofl/longcang/LongCang-Regular.ttf"
case "$(uname -s 2>/dev/null)" in
  Darwin) USER_FONT_DIR="$HOME/Library/Fonts" ;;
  *)      USER_FONT_DIR="$HOME/.local/share/fonts" ;;
esac

find_longcang() {
  local d
  for d in "$USER_FONT_DIR" "$HOME/.fonts" /usr/local/share/fonts /usr/share/fonts \
           "$HOME/Library/Fonts" /Library/Fonts; do
    [ -d "$d" ] || continue
    find "$d" \( -iname '*longcang*.ttf' -o -iname '*long cang*.ttf' \
                 -o -iname '*longcang*.otf' -o -iname '*龙藏*' \) 2>/dev/null | head -n 1
  done
}

if [ "${1:-}" = "--install-font" ]; then
  mkdir -p "$USER_FONT_DIR"
  DEST="$USER_FONT_DIR/LongCang-Regular.ttf"
  echo "==> 下载龙藏体 Long Cang -> $DEST"
  if ! curl -fsSL "$FONT_URL" -o "$DEST" || [ ! -s "$DEST" ]; then
    # 直连下载域名不可达时（如受限沙箱），改走 github.com 稀疏克隆同一仓库
    echo "    直连失败，改用 git 稀疏克隆 google/fonts …"
    TMP_FONT="$(mktemp -d)"
    git clone -q --depth 1 --filter=blob:none --sparse \
      https://github.com/google/fonts.git "$TMP_FONT"
    git -C "$TMP_FONT" sparse-checkout set ofl/longcang
    git -C "$TMP_FONT" checkout -q
    cp "$TMP_FONT/ofl/longcang/LongCang-Regular.ttf" "$DEST"
    cp "$TMP_FONT/ofl/longcang/OFL.txt" "$USER_FONT_DIR/OFL-LongCang.txt"
    rm -rf "$TMP_FONT"
  else
    curl -fsSL "https://raw.githubusercontent.com/google/fonts/main/ofl/longcang/OFL.txt" \
      -o "$USER_FONT_DIR/OFL-LongCang.txt" || true
  fi
  command -v fc-cache >/dev/null 2>&1 && fc-cache -f "$USER_FONT_DIR" >/dev/null 2>&1 || true
fi

echo "==> Python / Node"
python3 --version
node --version 2>/dev/null || echo "    Node 未安装：count_cjk.js / ledger.js 不可用（.py 版不受影响）"

echo "==> 脚本语法检查（不写字节码）"
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import ast
from pathlib import Path
for f in ("scripts/count_cjk.py", "scripts/ledger.py", "scripts/make_cover.py"):
    ast.parse(Path(f).read_text(encoding="utf-8"), filename=f)
    print(f"    OK  {f}")
PY
if command -v node >/dev/null 2>&1; then
  node --check scripts/count_cjk.js && node --check scripts/ledger.js \
    && echo "    OK  scripts/count_cjk.js / scripts/ledger.js"
fi

echo "==> Pillow / numpy（make_cover.py 需要）"
if python3 -c "import PIL, numpy; print('    Pillow', PIL.__version__, '/ numpy', numpy.__version__)" 2>/dev/null; then
  :
else
  echo "    未安装。建议用虚拟环境：python3 -m venv .venv && .venv/bin/pip install Pillow numpy"
fi

echo "==> 默认字体：龙藏体 Long Cang"
FOUND="$(find_longcang | head -n 1)"
if [ -n "${TAOZI_FONT_LONGCANG:-}" ] && [ -f "$TAOZI_FONT_LONGCANG" ]; then
  echo "    环境变量 TAOZI_FONT_LONGCANG=$TAOZI_FONT_LONGCANG"
elif [ -n "$FOUND" ]; then
  echo "    已找到 $FOUND"
else
  echo "    未找到。make_cover.py 会警告并回退系统 CJK。安装任选其一："
  echo "      bash scripts/setup.sh --install-font"
  echo "      手动下载 $FONT_URL 放到 $USER_FONT_DIR/"
fi

echo
echo "==> 快速验证"
echo "    python3 scripts/make_cover.py --check-font"
echo "    python3 scripts/count_cjk.py <稿件.md>"
