#!/usr/bin/env node
/**
 * 中文字数实测脚本（公众号文章专用）—— count_cjk.py 的 Node 等价实现
 *
 * 为什么需要它：模型自报的字数普遍不准（实测偏差可达 10%+）。
 * 本机若无可用 Python，就用这个脚本，逻辑与双口径与 count_cjk.py 完全一致。
 *
 * 两个口径（公众号场景都要看）：
 *   - 纯汉字数   cjk_only  ：只数中日韩统一表意文字，不含标点/数字/字母
 *   - 含标点数   with_punct：去掉所有空白字符后的字符数（含标点、数字、字母）
 *
 * 用法示例：
 *   # 全文统计
 *   node count_cjk.js article.md
 *
 *   # 只统计正文（第 9 行到第 57 行，1-based，含首含尾）
 *   node count_cjk.js article.md --body-start 9 --body-end 57
 *
 *   # 正文统计，但排除其中的脱敏说明段（第 19、20 行）
 *   node count_cjk.js article.md --body-start 9 --body-end 57 --exclude 19,20
 *
 *   # 以 JSON 输出（便于程序消费）
 *   node count_cjk.js article.md --json
 *
 * 退出码：0 正常；1 参数错误；2 行号越界。
 */

'use strict';

const fs = require('fs');

// 中日韩表意文字（含扩展A、兼容区），与 Python 版一致
const CJK_RE = /[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]/g;

function stripMarkdownNoise(text) {
  // 去掉 Markdown 语法符号，避免把 ** > # - 等计入字数。
  let t = text;
  t = t.replace(/\*\*([\s\S]+?)\*\*/g, '$1');                 // 粗体 **x**
  t = t.replace(/(^|[^*])\*(?!\*)([\s\S]+?)(?<!\*)\*(?!\*)/g, '$1$2'); // 斜体 *x*
  t = t.replace(/^[ \t]*>+[ \t]?/gm, '');                     // 引用 >
  t = t.replace(/^[ \t]*[-*+][ \t]+/gm, '');                  // 无序列表
  t = t.replace(/^[ \t]*\d+\.[ \t]+/gm, '');                  // 有序列表
  t = t.replace(/^[ \t]*#{1,6}[ \t]+/gm, '');                 // 标题 #
  t = t.replace(/^[ \t]*-{3,}[ \t]*$/gm, '');                 // 分隔线 ---
  t = t.replace(/\[([\s\S]+?)\]\(([\s\S]+?)\)/g, '$1');       // 链接
  t = t.replace(/`/g, '');                                    // 行内代码
  return t;
}

function count(text) {
  const cleaned = stripMarkdownNoise(text);
  const cjk = (cleaned.match(CJK_RE) || []).length;
  const noWs = cleaned.replace(/\s/g, '');
  return {
    cjk_only: cjk,                 // 纯汉字
    with_punct: noWs.length,       // 含标点（去空白）
    punctuation_only: noWs.length - cjk,
  };
}

function parseArgs(argv) {
  const args = { file: null, bodyStart: null, bodyEnd: null, exclude: '', json: false };
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--body-start') args.bodyStart = parseInt(argv[++i], 10);
    else if (a === '--body-end') args.bodyEnd = parseInt(argv[++i], 10);
    else if (a === '--exclude') args.exclude = argv[++i] || '';
    else if (a === '--json') args.json = true;
    else if (a === '-h' || a === '--help') args.help = true;
    else rest.push(a);
  }
  args.file = rest[0] || null;
  return args;
}

function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args.help || !args.file) {
    process.stderr.write('用法：node count_cjk.js <文件> [--body-start N] [--body-end N] [--exclude 行,行] [--json]\n');
    return 1;
  }

  if (!fs.existsSync(args.file)) {
    process.stderr.write(`[错误] 文件不存在：${args.file}\n`);
    return 1;
  }

  const raw = fs.readFileSync(args.file, 'utf8');
  const lines = raw.split('\n');
  const total = lines.length;

  const start = args.bodyStart || 1;
  const end = args.bodyEnd || total;
  if (start < 1 || end > total || start > end) {
    process.stderr.write(`[错误] 行号越界：文件共 ${total} 行，收到 start=${start} end=${end}\n`);
    return 2;
  }

  const excludes = new Set();
  if (args.exclude.trim()) {
    for (const piece of args.exclude.split(',')) {
      const p = piece.trim();
      if (!p) continue;
      const n = Number(p);
      if (!Number.isInteger(n)) {
        process.stderr.write(`[错误] --exclude 含非数字项：${p}\n`);
        return 1;
      }
      excludes.add(n);
    }
  }

  const segLines = [];
  for (let i = start; i <= end; i++) {
    if (!excludes.has(i)) segLines.push(lines[i - 1]);
  }
  const body = segLines.join('\n');
  const result = count(body);

  if (args.json) {
    const out = Object.assign({}, result, {
      file: args.file,
      body_start: start,
      body_end: end,
      excluded_lines: Array.from(excludes).sort((x, y) => x - y),
      total_lines: total,
    });
    process.stdout.write(JSON.stringify(out, null, 2) + '\n');
    return 0;
  }

  const exStr = excludes.size ? `，已排除行 ${Array.from(excludes).sort((x, y) => x - y).join(',')}` : '';
  process.stdout.write(`文件：${args.file}\n`);
  process.stdout.write(`统计范围：第 ${start}–${end} 行（共 ${total} 行）${exStr}\n`);
  process.stdout.write('-'.repeat(44) + '\n');
  process.stdout.write(`纯汉字数（不含标点）：${result.cjk_only}\n`);
  process.stdout.write(`含标点数（去空白）  ：${result.with_punct}\n`);
  process.stdout.write(`其中标点等非汉字    ：${result.punctuation_only}\n`);
  process.stdout.write('-'.repeat(44) + '\n');
  process.stdout.write('提示：用户给定字数区间时，两个口径都应落在区间内才算达标。\n');
  return 0;
}

process.exit(main());
