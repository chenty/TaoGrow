#!/usr/bin/env python3
"""gzh-story-writer 文章台账与防批量化检查脚本 (Python 等价实现)

与 scripts/ledger.js 逐行等价：子命令、参数解析、路径查找、输出文案、
JSON 落盘格式、排序与比较语义均按 JS 版复刻。

用于跨篇检查、冷却管理、选项与钩子形态轮换、防止平台识别 AI 批量特征。

用法：
    python3 scripts/ledger.py <子命令> [参数]
    python3 scripts/ledger.py check 小满
"""

import json
import math
import os
import random
import sys
from datetime import datetime, timezone

HOOK_TYPES = [
    '① 数字选项',
    '② AB 二选一',
    '③ 字母选项',
    '④ 开放式填空',
    '⑤ 一句话留言',
]

OPENING_TYPES = [
    '物件开场',
    '台词/对话开场',
    '场景细节开场',
    '第二人称代入开场',
    '动作开场',
    '时间线/倒叙开场',
]

STRUCTURE_TYPES = [
    '标准生活流叙事',
    '纯对话体',
    '时间线推进',
    '一封回信/信件体',
    '第一人称自述深挖',
    '清单反转',
]

DEFAULT_CHOICE_COUNTS = [2, 3, 4, 5]

# JS 里 args 缺少某个键时取到 undefined；用哨兵复刻，以区分「未传」与 null
UNDEFINED = object()


# ---------------------------------------------------------------- JS 语义辅助


def js_number(v):
    """复刻 JS 的 Number()：None→0, True→1, ''→0, 'abc'→NaN"""
    if v is UNDEFINED:
        return float('nan')
    if v is None:
        return 0
    if v is True:
        return 1
    if v is False:
        return 0
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip()
    if s == '':
        return 0
    try:
        f = float(s)
    except ValueError:
        return float('nan')
    if math.isinf(f):
        return f
    return f if math.isnan(f) else (int(f) if f.is_integer() else f)


def js_truthy(v):
    if v is UNDEFINED or v is None or v is False:
        return False
    if v is True:
        return True
    if isinstance(v, (int, float)):
        return not (v == 0 or (isinstance(v, float) and math.isnan(v)))
    if isinstance(v, str):
        return v != ''
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return True


def js_str(v):
    """复刻打印时的 String() 转换"""
    if v is UNDEFINED:
        return 'undefined'
    if v is None:
        return 'null'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, float):
        if math.isnan(v):
            return 'NaN'
        if math.isinf(v):
            return 'Infinity' if v > 0 else '-Infinity'
        return str(int(v)) if v.is_integer() else repr(v)
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False, separators=(',', ':'))
    return str(v)


def js_strict_eq(a, b):
    """JS 的 ===：类型不同即不等"""
    if a is UNDEFINED or b is UNDEFINED:
        return a is b
    if a is None or b is None:
        return a is b
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, float) and math.isnan(a):
            return False
        if isinstance(b, float) and math.isnan(b):
            return False
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    return False


def utf16_key(s):
    """JS 数组默认排序按 UTF-16 码元比较"""
    return str(s).encode('utf-16-be', 'surrogatepass')


def json_dumps_js(data):
    """复刻 JSON.stringify(data, null, 2)：无空格分隔符、非 ASCII 原样、NaN→null"""
    def sanitize(o):
        if isinstance(o, float):
            if math.isnan(o):
                return None
            if o.is_integer():
                return int(o)
            return o
        if isinstance(o, dict):
            return {k: sanitize(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [sanitize(v) for v in o]
        return o

    return json.dumps(sanitize(data), ensure_ascii=False, indent=2)


def now_iso():
    """复刻 new Date().toISOString().replace('T',' ').slice(0,19)（UTC）"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def today_utc():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


# ---------------------------------------------------------------- 参数与路径


def parse_args(argv):
    """复刻 JS parseArgs：--key value / --flag(布尔)"""
    result = {'_': []}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith('--'):
            key = arg[2:]
            nxt = argv[i + 1] if i + 1 < len(argv) else None
            if nxt is not None and not nxt.startswith('--'):
                result[key] = nxt
                i += 1
            else:
                result[key] = True
        else:
            result['_'].append(arg)
        i += 1
    return result


def get_ledger_path(account_id, workspace_dir=None):
    root = workspace_dir if js_truthy(workspace_dir) and workspace_dir is not True else os.getcwd()
    candidates = [
        os.path.join(root, 'out', f'{account_id}手记', '台账'),
        os.path.join(root, 'out', f'{account_id}的人间账本', '台账'),
        os.path.join(root, 'out', account_id, '台账'),
        os.path.join(root, 'out', '台账'),
        root,
    ]
    for c in candidates:
        candidate_file = os.path.join(c, f'ledger_{account_id}.json')
        if os.path.exists(candidate_file):
            return candidate_file
    for c in candidates:
        if os.path.exists(c):
            return os.path.join(c, f'ledger_{account_id}.json')
    return os.path.join(root, f'ledger_{account_id}.json')


def load_ledger(ledger_path):
    if not os.path.exists(ledger_path):
        return []
    try:
        with open(ledger_path, encoding='utf-8') as f:
            raw = f.read()
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get('records'), list):
            return data['records']
        return []
    except Exception as e:
        sys.stderr.write(f'⚠️ 读取台账失败: {e}\n')
        return []


def save_ledger(ledger_path, records):
    base = os.path.basename(ledger_path).replace('ledger_', '', 1).replace('.json', '', 1)
    data = {
        'account': base,
        'updated_at': now_iso(),
        'records': records,
    }
    with open(ledger_path, 'w', encoding='utf-8') as f:
        f.write(json_dumps_js(data))


# ---------------------------------------------------------------- 子命令


def cmd_init(args):
    account = args['_'][1] if len(args['_']) > 1 else None
    if not account:
        sys.stderr.write('❌ 请提供账号简称，如: python3 scripts/ledger.py init 小满\n')
        sys.exit(1)
    ledger_path = get_ledger_path(account, args.get('workspace', UNDEFINED))
    if os.path.exists(ledger_path):
        print(f'ℹ️ 台账已存在: {ledger_path}')
        return
    save_ledger(ledger_path, [])
    print(f'✅ 已初始化账号 [{account}] 的台账: {ledger_path}')


def cmd_check(args):
    account = args['_'][1] if len(args['_']) > 1 else None
    if not account:
        sys.stderr.write('❌ 请提供账号简称，如: python3 scripts/ledger.py check 小满\n')
        sys.exit(1)
    ledger_path = get_ledger_path(account, args.get('workspace', UNDEFINED))
    records = load_ledger(ledger_path)

    print('==================================================')
    print(f'📊 账号 [{account}] 跨篇防批量化纪律检查')
    print(f'台账路径: {ledger_path}')
    print(f'累计已登记: {len(records)} 篇')
    print('==================================================')

    if len(records) == 0:
        print('\n💡 台账为空或刚初始化，本篇为第一篇，不受历史冷却限制。')
        print('建议规则：')
        print('1. 避免使用"先问你个事""那天""老X跟我讲起"等高频AI开头套路')
        print('2. 选项数量选 2-5 之间任一数字')
        print('3. 结尾互动从五种形态中任选一种\n')
        return

    recent5 = records[-5:]
    last1 = records[-1]

    # 2. 人物称呼冷却
    recent_names = {}
    for r in recent5:
        names = r.get('character_names', [])
        if isinstance(names, list):
            for n in names:
                if js_truthy(n):
                    recent_names[str(n).strip()] = True
        elif isinstance(names, str) and names:
            recent_names[names.strip()] = True

    print('\n🚫 【人物称呼与代称冷却池（最近 5 篇禁用，同名不同人亦禁止）】')
    if recent_names:
        sorted_names = sorted(recent_names.keys(), key=utf16_key)
        print(f'   已用称呼: {", ".join(sorted_names)}')
        laox = [n for n in sorted_names if n.startswith('老')]
        if laox:
            print(f'   ⚠️ 警惕"老X"连续剧感！已用过: {", ".join(laox)}。'
                  f'本篇强烈建议用身份代称（如"一个开饭馆的""我表姐夫"）！')
    else:
        print('   （无近期人物记录）')

    # 3. 选择数相邻与连续性
    last_choice = last1.get('choice_count', UNDEFINED)
    print('\n🔢 【正文选择数纪律】')
    print(f'   上一篇选择数: {js_str(last_choice) if last_choice is not UNDEFINED else "未记录"}')
    if last_choice is not UNDEFINED:
        allowed = [c for c in DEFAULT_CHOICE_COUNTS if not js_strict_eq(c, js_number(last_choice))]
        print(f'   🚫 本篇禁用选择数: [{js_str(last_choice)}] （相邻篇目严禁同数）')
        print(f'   ✅ 本篇可选选择数: [{", ".join(str(c) for c in allowed)}]')
    else:
        print(f'   ✅ 本篇可选选择数: [{", ".join(str(c) for c in DEFAULT_CHOICE_COUNTS)}]')

    consecutive5 = sum(1 for r in recent5 if js_strict_eq(js_number(r.get('choice_count', UNDEFINED)), 5))
    if consecutive5 >= 2:
        print(f'   ⚠️ 警告：最近 5 篇中出现过 {consecutive5} 次 5 选项，严禁再次选 5！')

    # 4. 结尾互动钩子形态
    last_hook = last1.get('hook_type', '') or ''
    print('\n🪝 【结尾互动钩子形态轮换】')
    print(f'   上一篇钩子形态: {last_hook if last_hook else "未记录"}')
    allowed_hooks = [h for h in HOOK_TYPES if h != last_hook]
    print(f'   🚫 本篇禁用上一篇同款形态: {last_hook if last_hook else "无"}')
    print(f'   ✅ 本篇可用形态: {json.dumps(allowed_hooks, ensure_ascii=False, separators=(",", ":"))}')

    num_hooks = sum(1 for r in recent5 if '数字' in str(r.get('hook_type', '') or ''))
    if num_hooks >= 3:
        print(f'   ⚠️ 警惕：最近 5 篇有 {num_hooks} 篇使用数字选项！'
              f'本篇建议强制切换为 AB二选一、开放式填空或一句话留言！')

    # 5. 结构骨架
    recent_structs = [str(r.get('structure', '') or '').strip() for r in recent5]
    recent_structs = [x for x in recent_structs if x]
    print('\n🏛️ 【结构骨架与节奏】')
    if recent_structs:
        print(f'   最近使用结构: {", ".join(recent_structs)}')
        if len(recent_structs) >= 2 and recent_structs[-1] == recent_structs[-2]:
            print(f'   ⚠️ 警告：最近已连续两篇使用同一种结构 [{recent_structs[-1]}]，本篇必须换结构！')
    else:
        print('   （未记录具体结构）')

    # 6. 金句与加粗
    print('\n✍️ 【金句与加粗纪律（自检硬约束）】')
    print('   1. 全篇"不是…是…"或"X靠的是A，Y靠的是B"对仗判断句严格 ≤ 1 句。')
    print('   2. 严禁固定节拍（转折加粗 + 中段对仗加粗 + 结尾判断加粗）。'
          '允许某篇 0-1 处加粗，金句不加粗。')
    print('   3. 避免篇篇两个朋友对比（少用"我有个朋友甲乙"），可深挖单个样本或自身事件。')
    print('==================================================\n')


def _pick(pool, fallback):
    """复刻 pool[Math.floor(Math.random() * pool.length)] || fallback"""
    if not pool:
        return fallback
    v = pool[int(random.random() * len(pool))]
    return v if js_truthy(v) else fallback


def cmd_suggest(args):
    account = args['_'][1] if len(args['_']) > 1 else None
    if not account:
        sys.stderr.write('❌ 请提供账号简称，如: python3 scripts/ledger.py suggest 小满\n')
        sys.exit(1)
    ledger_path = get_ledger_path(account, args.get('workspace', UNDEFINED))
    records = load_ledger(ledger_path)

    last1 = records[-1] if records else {}
    recent5 = records[-5:]

    last_choice = last1.get('choice_count', UNDEFINED)
    choice_pool = [c for c in DEFAULT_CHOICE_COUNTS
                   if not js_strict_eq(c, js_number(last_choice))]
    suggested_choice = _pick(choice_pool, 3)

    last_hook = last1.get('hook_type', '') or ''
    hook_pool = [h for h in HOOK_TYPES if h != last_hook]
    num_hooks = sum(1 for r in recent5 if '数字' in str(r.get('hook_type', '') or ''))
    if num_hooks >= 2:
        hook_pool = [h for h in hook_pool if '数字' not in h]
    suggested_hook = _pick(hook_pool, HOOK_TYPES[1])

    recent_structs = [str(r.get('structure', '') or '') for r in recent5][-2:]
    struct_pool = [s for s in STRUCTURE_TYPES if s not in recent_structs]
    suggested_struct = _pick(struct_pool, STRUCTURE_TYPES[0])

    print(f'\n🎯 账号 [{account}] 下一篇参数智能推荐：')
    last_choice_disp = js_str(last_choice) if last_choice is not UNDEFINED else '无'
    print(f'   - 推荐选择数: {suggested_choice} 种（避开上一篇 {last_choice_disp}）')
    print(f'   - 推荐互动钩子: {suggested_hook}')
    print(f'   - 推荐结构骨架: {suggested_struct}')
    print('   - 人物样本设计: 建议 1 个样本写透或以自身事件深挖，避开"两个老朋友"公式\n')


def cmd_log(args):
    account = args['_'][1] if len(args['_']) > 1 else None
    if not account or not js_truthy(args.get('title', UNDEFINED)) or not js_truthy(args.get('hook', UNDEFINED)):
        sys.stderr.write(
            '❌ 参数不足。用法: python3 scripts/ledger.py log <账号> --title "<标题>" '
            '--hook "<钩子形态>" [--choices N] [--opening "..."] [--names "..."]\n')
        sys.exit(1)
    ledger_path = get_ledger_path(account, args.get('workspace', UNDEFINED))
    records = load_ledger(ledger_path)

    names_v = args.get('names', UNDEFINED)
    char_names = ([s.strip() for s in str(names_v).split(',') if s.strip()]
                  if js_truthy(names_v) else [])
    tags_v = args.get('tags', UNDEFINED)
    tags = ([s.strip() for s in str(tags_v).split(',') if s.strip()]
            if js_truthy(tags_v) else [])

    opening_style = args.get('opening-style', UNDEFINED)
    record = {
        'id': len(records) + 1,
        'date': args['date'] if js_truthy(args.get('date', UNDEFINED)) else today_utc(),
        'account': account,
        'title': args['title'],
        'opening_phrase': args['opening'] if js_truthy(args.get('opening', UNDEFINED)) else '',
        'opening_style': opening_style if opening_style is not UNDEFINED else True if opening_style is True else '',
        'character_names': char_names,
        'choice_count': js_number(args['choices']) if 'choices' in args else 3,
        'hook_type': args['hook'],
        'structure': args['structure'] if js_truthy(args.get('structure', UNDEFINED)) else '标准生活流叙事',
        'bold_count': js_number(args['bold-count']) if 'bold-count' in args else 2,
        'antithesis_count': js_number(args['antithesis-count']) if 'antithesis-count' in args else 1,
        'word_count': js_number(args['words']) if 'words' in args else 0,
        'tags': tags,
        'notes': args['notes'] if js_truthy(args.get('notes', UNDEFINED)) else '',
    }

    records.append(record)
    save_ledger(ledger_path, records)

    print(f'✅ 成功追加台账记录 #{record["id"]} 至 {ledger_path}')
    print(f'   标题: {record["title"]}')
    print(f'   选择数: {js_str(record["choice_count"])} | 钩子: {record["hook_type"]} '
          f'| 结构: {record["structure"]}')


def cmd_report(args):
    account = args['_'][1] if len(args['_']) > 1 else None
    if not account:
        sys.stderr.write('❌ 请提供账号简称，如: python3 scripts/ledger.py report 小满\n')
        sys.exit(1)
    ledger_path = get_ledger_path(account, args.get('workspace', UNDEFINED))
    records = load_ledger(ledger_path)

    if len(records) == 0:
        print(f'ℹ️ 账号 [{account}] 暂无台账数据。')
        return

    print(f'\n📈 账号 [{account}] 历史创作台账分析报告（共 {len(records)} 篇）')
    print('--------------------------------------------------')

    choice_counts = {}
    hook_types = {}
    structures = {}

    for r in records:
        if 'choice_count' in r and r['choice_count'] is not UNDEFINED:
            k = js_str(r['choice_count'])
            choice_counts[k] = choice_counts.get(k, 0) + 1
        hk = r.get('hook_type', '') or ''
        if hk:
            hook_types[hk] = hook_types.get(hk, 0) + 1
        st = r.get('structure', '') or ''
        if st:
            structures[st] = structures.get(st, 0) + 1

    print('📊 选择数分布:')
    for k in sorted(choice_counts.keys()):  # JS 默认 sort：字符串字典序
        print(f'   {k} 种选择: {choice_counts[k]} 篇')

    print('\n🪝 互动钩子分布:')
    for k, v in hook_types.items():
        print(f'   {k}: {v} 篇')

    print('\n🏛️ 结构分布:')
    for k, v in structures.items():
        print(f'   {k}: {v} 篇')

    violations = []
    for i in range(1, len(records)):
        prev = records[i - 1]
        curr = records[i]
        pc = prev.get('choice_count', UNDEFINED)
        cc = curr.get('choice_count', UNDEFINED)
        if pc is not UNDEFINED and cc is not UNDEFINED and js_strict_eq(pc, cc):
            violations.append(
                f'篇目 #{js_str(prev.get("id", UNDEFINED))}({prev.get("title", "") or ""}) '
                f'与 #{js_str(curr.get("id", UNDEFINED))}({curr.get("title", "") or ""}) '
                f'选择数相邻重复 ({js_str(cc)})')
        ph = prev.get('hook_type', '') or ''
        ch = curr.get('hook_type', '') or ''
        if ph and ch and ph == ch:
            violations.append(
                f'篇目 #{js_str(prev.get("id", UNDEFINED))}({prev.get("title", "") or ""}) '
                f'与 #{js_str(curr.get("id", UNDEFINED))}({curr.get("title", "") or ""}) '
                f'钩子形态相邻重复 ({ch})')

    if violations:
        print('\n⚠️ 历史相邻重复违规记录:')
        for v in violations:
            print(f'   - {v}')
    else:
        print('\n🎉 历史排期良好，未发现相邻重复违规！')
    print('')


def cmd_export(args):
    account = args['_'][1] if len(args['_']) > 1 else None
    if not account:
        sys.stderr.write('❌ 请提供账号简称，如: python3 scripts/ledger.py export 小满\n')
        sys.exit(1)
    ledger_path = get_ledger_path(account, args.get('workspace', UNDEFINED))
    records = load_ledger(ledger_path)
    out_path = (args['output'] if js_truthy(args.get('output', UNDEFINED))
                else os.path.join(os.path.dirname(ledger_path), f'防批量登记_{account}.md'))

    now = now_iso()
    lines = [
        f'# 防批量登记台账 · {account}',
        '',
        f'> 自动导出自 `{os.path.basename(ledger_path)}` | 导出时间：{now}',
        '',
        '## 逐篇登记表',
        '',
        '| # | 日期 | 标题 | 人物称呼 | 选择数 | 钩子形态 | 结构骨架 | 对仗/加粗 | 标签 |',
        '|---|---|---|---|---|---|---|---|---|---|',
    ]

    for r in records:
        names = ', '.join(str(x) for x in (r.get('character_names', []) or []))
        tags = ' '.join(str(x) for x in (r.get('tags', []) or []))
        a = r.get('antithesis_count', 0)
        b = r.get('bold_count', 0)
        bold_info = (f'对仗{0 if (a is None or a is UNDEFINED or isinstance(a, bool)) else js_str(a)}'
                     f'/加粗{0 if (b is None or b is UNDEFINED or isinstance(b, bool)) else js_str(b)}')
        cc = r.get('choice_count', UNDEFINED)
        lines.append(
            f'| {js_str(r.get("id", UNDEFINED)) if r.get("id", UNDEFINED) is not UNDEFINED else ""} '
            f'| {r.get("date", "") or ""} '
            f'| {r.get("title", "") or ""} '
            f'| {names} '
            f'| {"" if cc is UNDEFINED else js_str(cc)} '
            f'| {r.get("hook_type", "") or ""} '
            f'| {r.get("structure", "") or ""} '
            f'| {bold_info} '
            f'| {tags} |'
        )

    lines.append('')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'✅ 已成功导出 Markdown 台账: {out_path}')


USAGE = """
用法: python3 scripts/ledger.py <子命令> [参数]

子命令:
  init <账号>           初始化台账 (ledger_<账号>.json)
  check <账号>          检查最近5篇冷却与禁用项
  suggest <账号>        推荐本篇选择数、钩子形态与结构
  log <账号> [选项]     追加成稿记录
  report <账号>         分析历史分布与违规检测
  export <账号> [选项]  导出为 Markdown 表格

选项:
  --workspace <路径>    指定工作目录
  --title <标题>        文章标题 (用于 log)
  --hook <形态>         钩子形态 (用于 log)
  --choices <数量>      选择数 2-5 (用于 log)
  --names <称呼>        人物称呼，逗号分隔 (用于 log)
  --opening <前几句>    开头句式 (可选，仅记录不再参与校验)
  --structure <结构>    结构骨架 (用于 log)
  --bold-count <数量>   加粗段落数 (用于 log)
  --antithesis-count N  对仗句数 (用于 log)
    """


def main():
    args = parse_args(sys.argv[1:])
    cmd = args['_'][0] if args['_'] else None

    if not cmd:
        print(USAGE)
        sys.exit(0)

    if cmd == 'init':
        return cmd_init(args)
    if cmd == 'check':
        return cmd_check(args)
    if cmd == 'suggest':
        return cmd_suggest(args)
    if cmd == 'log':
        return cmd_log(args)
    if cmd == 'report':
        return cmd_report(args)
    if cmd == 'export':
        return cmd_export(args)

    sys.stderr.write(f'❌ 未知命令: {cmd}\n')
    sys.exit(1)


if __name__ == '__main__':
    main()
