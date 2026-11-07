#!/usr/bin/env node
/**
 * gzh-story-writer 文章台账与防批量化检查脚本 (Node.js 等价实现)
 * 用于跨篇检查、冷却管理、选项与钩子形态轮换、防止平台识别 AI 批量特征。
 */

const fs = require('fs');
const path = require('path');

const HOOK_TYPES = [
  '① 数字选项',
  '② AB 二选一',
  '③ 字母选项',
  '④ 开放式填空',
  '⑤ 一句话留言'
];

const OPENING_TYPES = [
  '物件开场',
  '台词/对话开场',
  '场景细节开场',
  '第二人称代入开场',
  '动作开场',
  '时间线/倒叙开场'
];

const STRUCTURE_TYPES = [
  '标准生活流叙事',
  '纯对话体',
  '时间线推进',
  '一封回信/信件体',
  '第一人称自述深挖',
  '清单反转'
];

const DEFAULT_CHOICE_COUNTS = [2, 3, 4, 5];

function parseArgs(args) {
  const result = { _: [] };
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg.startsWith('--')) {
      const key = arg.slice(2);
      const next = args[i + 1];
      if (next && !next.startsWith('--')) {
        result[key] = next;
        i++;
      } else {
        result[key] = true;
      }
    } else {
      result._.push(arg);
    }
  }
  return result;
}

function getLedgerPath(accountId, workspaceDir) {
  const root = workspaceDir || process.cwd();
  const candidates = [
    path.join(root, 'out', `${accountId}手记`, '台账'),
    path.join(root, 'out', `${accountId}的人间账本`, '台账'),
    path.join(root, 'out', accountId, '台账'),
    path.join(root, 'out', '台账'),
    root
  ];
  for (const c of candidates) {
    const candidateFile = path.join(c, `ledger_${accountId}.json`);
    if (fs.existsSync(candidateFile)) {
      return candidateFile;
    }
  }
  for (const c of candidates) {
    if (fs.existsSync(c)) {
      return path.join(c, `ledger_${accountId}.json`);
    }
  }
  return path.join(root, `ledger_${accountId}.json`);
}

function loadLedger(ledgerPath) {
  if (!fs.existsSync(ledgerPath)) return [];
  try {
    const raw = fs.readFileSync(ledgerPath, 'utf8');
    const data = JSON.parse(raw);
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.records)) return data.records;
    return [];
  } catch (e) {
    console.error(`⚠️ 读取台账失败: ${e.message}`);
    return [];
  }
}

function saveLedger(ledgerPath, records) {
  const account = path.basename(ledgerPath).replace('ledger_', '').replace('.json', '');
  const now = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const data = {
    account,
    updated_at: now,
    records
  };
  fs.writeFileSync(ledgerPath, JSON.stringify(data, null, 2), 'utf8');
}

function cmdInit(args) {
  const account = args._[1];
  if (!account) {
    console.error('❌ 请提供账号简称，如: node scripts/ledger.js init 小满');
    process.exit(1);
  }
  const ledgerPath = getLedgerPath(account, args.workspace);
  if (fs.existsSync(ledgerPath)) {
    console.log(`ℹ️ 台账已存在: ${ledgerPath}`);
    return;
  }
  saveLedger(ledgerPath, []);
  console.log(`✅ 已初始化账号 [${account}] 的台账: ${ledgerPath}`);
}

function cmdCheck(args) {
  const account = args._[1];
  if (!account) {
    console.error('❌ 请提供账号简称，如: node scripts/ledger.js check 小满');
    process.exit(1);
  }
  const ledgerPath = getLedgerPath(account, args.workspace);
  const records = loadLedger(ledgerPath);

  console.log('==================================================');
  console.log(`📊 账号 [${account}] 跨篇防批量化纪律检查`);
  console.log(`台账路径: ${ledgerPath}`);
  console.log(`累计已登记: ${records.length} 篇`);
  console.log('==================================================');

  if (records.length === 0) {
    console.log('\n💡 台账为空或刚初始化，本篇为第一篇，不受历史冷却限制。');
    console.log('建议规则：');
    console.log('1. 避免使用"先问你个事""那天""老X跟我讲起"等高频AI开头套路');
    console.log('2. 选项数量选 2-5 之间任一数字');
    console.log('3. 结尾互动从五种形态中任选一种\n');
    return;
  }

  const recent5 = records.slice(-5);
  const last1 = records[records.length - 1];

  // 2. 人物称呼冷却
  const recentNames = new Set();
  recent5.forEach(r => {
    const names = r.character_names || [];
    if (Array.isArray(names)) {
      names.forEach(n => n && recentNames.add(n.trim()));
    } else if (typeof names === 'string' && names) {
      recentNames.add(names.trim());
    }
  });

  console.log('\n🚫 【人物称呼与代称冷却池（最近 5 篇禁用，同名不同人亦禁止）】');
  if (recentNames.size > 0) {
    const sortedNames = [...recentNames].sort();
    console.log(`   已用称呼: ${sortedNames.join(', ')}`);
    const laox = sortedNames.filter(n => n.startsWith('老'));
    if (laox.length > 0) {
      console.log(`   ⚠️ 警惕"老X"连续剧感！已用过: ${laox.join(', ')}。本篇强烈建议用身份代称（如"一个开饭馆的""我表姐夫"）！`);
    }
  } else {
    console.log('   （无近期人物记录）');
  }

  // 3. 选择数相邻与连续性
  const lastChoice = last1.choice_count;
  console.log('\n🔢 【正文选择数纪律】');
  console.log(`   上一篇选择数: ${lastChoice !== undefined ? lastChoice : '未记录'}`);
  if (lastChoice !== undefined) {
    const allowed = DEFAULT_CHOICE_COUNTS.filter(c => c !== Number(lastChoice));
    console.log(`   🚫 本篇禁用选择数: [${lastChoice}] （相邻篇目严禁同数）`);
    console.log(`   ✅ 本篇可选选择数: [${allowed.join(', ')}]`);
  } else {
    console.log(`   ✅ 本篇可选选择数: [${DEFAULT_CHOICE_COUNTS.join(', ')}]`);
  }

  const consecutive5 = recent5.filter(r => Number(r.choice_count) === 5).length;
  if (consecutive5 >= 2) {
    console.log(`   ⚠️ 警告：最近 5 篇中出现过 ${consecutive5} 次 5 选项，严禁再次选 5！`);
  }

  // 4. 结尾互动钩子形态
  const lastHook = last1.hook_type || '';
  console.log('\n🪝 【结尾互动钩子形态轮换】');
  console.log(`   上一篇钩子形态: ${lastHook || '未记录'}`);
  const allowedHooks = HOOK_TYPES.filter(h => h !== lastHook);
  console.log(`   🚫 本篇禁用上一篇同款形态: ${lastHook || '无'}`);
  console.log(`   ✅ 本篇可用形态: ${JSON.stringify(allowedHooks)}`);

  const numHooks = recent5.filter(r => (r.hook_type || '').includes('数字')).length;
  if (numHooks >= 3) {
    console.log(`   ⚠️ 警惕：最近 5 篇有 ${numHooks} 篇使用数字选项！本篇建议强制切换为 AB二选一、开放式填空或一句话留言！`);
  }

  // 5. 结构骨架
  const recentStructs = recent5.map(r => (r.structure || '').trim()).filter(Boolean);
  console.log('\n🏛️ 【结构骨架与节奏】');
  if (recentStructs.length > 0) {
    console.log(`   最近使用结构: ${recentStructs.join(', ')}`);
    if (recentStructs.length >= 2 && recentStructs[recentStructs.length - 1] === recentStructs[recentStructs.length - 2]) {
      console.log(`   ⚠️ 警告：最近已连续两篇使用同一种结构 [${recentStructs[recentStructs.length - 1]}]，本篇必须换结构！`);
    }
  } else {
    console.log('   （未记录具体结构）');
  }

  // 6. 金句与加粗
  console.log('\n✍️ 【金句与加粗纪律（自检硬约束）】');
  console.log('   1. 全篇"不是…是…"或"X靠的是A，Y靠的是B"对仗判断句严格 ≤ 1 句。');
  console.log('   2. 严禁固定节拍（转折加粗 + 中段对仗加粗 + 结尾判断加粗）。允许某篇 0-1 处加粗，金句不加粗。');
  console.log('   3. 避免篇篇两个朋友对比（少用"我有个朋友甲乙"），可深挖单个样本或自身事件。');
  console.log('==================================================\n');
}

function cmdSuggest(args) {
  const account = args._[1];
  if (!account) {
    console.error('❌ 请提供账号简称，如: node scripts/ledger.js suggest 小满');
    process.exit(1);
  }
  const ledgerPath = getLedgerPath(account, args.workspace);
  const records = loadLedger(ledgerPath);

  const last1 = records[records.length - 1] || {};
  const recent5 = records.slice(-5);

  const lastChoice = last1.choice_count;
  const choicePool = DEFAULT_CHOICE_COUNTS.filter(c => c !== Number(lastChoice));
  const suggestedChoice = choicePool[Math.floor(Math.random() * choicePool.length)] || 3;

  const lastHook = last1.hook_type || '';
  let hookPool = HOOK_TYPES.filter(h => h !== lastHook);
  const numHooks = recent5.filter(r => (r.hook_type || '').includes('数字')).length;
  if (numHooks >= 2) {
    hookPool = hookPool.filter(h => !h.includes('数字'));
  }
  const suggestedHook = hookPool[Math.floor(Math.random() * hookPool.length)] || HOOK_TYPES[1];

  const recentStructs = recent5.map(r => r.structure || '').slice(-2);
  const structPool = STRUCTURE_TYPES.filter(s => !recentStructs.includes(s));
  const suggestedStruct = structPool[Math.floor(Math.random() * structPool.length)] || STRUCTURE_TYPES[0];

  console.log(`\n🎯 账号 [${account}] 下一篇参数智能推荐：`);
  console.log(`   - 推荐选择数: ${suggestedChoice} 种（避开上一篇 ${lastChoice !== undefined ? lastChoice : '无'}）`);
  console.log(`   - 推荐互动钩子: ${suggestedHook}`);
  console.log(`   - 推荐结构骨架: ${suggestedStruct}`);
  console.log(`   - 人物样本设计: 建议 1 个样本写透或以自身事件深挖，避开"两个老朋友"公式\n`);
}

function cmdLog(args) {
  const account = args._[1];
  if (!account || !args.title || !args.hook) {
    console.error('❌ 参数不足。用法: node scripts/ledger.js log <账号> --title "<标题>" --hook "<钩子形态>" [--choices N] [--opening "..."] [--names "..."]');
    process.exit(1);
  }
  const ledgerPath = getLedgerPath(account, args.workspace);
  const records = loadLedger(ledgerPath);

  const charNames = args.names ? args.names.split(',').map(s => s.trim()).filter(Boolean) : [];
  const tags = args.tags ? args.tags.split(',').map(s => s.trim()).filter(Boolean) : [];

  const record = {
    id: records.length + 1,
    date: args.date || new Date().toISOString().slice(0, 10),
    account,
    title: args.title,
    opening_phrase: args.opening || '',
    opening_style: args['opening-style'] || '',
    character_names: charNames,
    choice_count: args.choices !== undefined ? Number(args.choices) : 3,
    hook_type: args.hook,
    structure: args.structure || '标准生活流叙事',
    bold_count: args['bold-count'] !== undefined ? Number(args['bold-count']) : 2,
    antithesis_count: args['antithesis-count'] !== undefined ? Number(args['antithesis-count']) : 1,
    word_count: args.words !== undefined ? Number(args.words) : 0,
    tags,
    notes: args.notes || ''
  };

  records.push(record);
  saveLedger(ledgerPath, records);

  console.log(`✅ 成功追加台账记录 #${record.id} 至 ${ledgerPath}`);
  console.log(`   标题: ${record.title}`);
  console.log(`   选择数: ${record.choice_count} | 钩子: ${record.hook_type} | 结构: ${record.structure}`);
}

function cmdReport(args) {
  const account = args._[1];
  if (!account) {
    console.error('❌ 请提供账号简称，如: node scripts/ledger.js report 小满');
    process.exit(1);
  }
  const ledgerPath = getLedgerPath(account, args.workspace);
  const records = loadLedger(ledgerPath);

  if (records.length === 0) {
    console.log(`ℹ️ 账号 [${account}] 暂无台账数据。`);
    return;
  }

  console.log(`\n📈 账号 [${account}] 历史创作台账分析报告（共 ${records.length} 篇）`);
  console.log('--------------------------------------------------');

  const choiceCounts = {};
  const hookTypes = {};
  const structures = {};

  records.forEach(r => {
    if (r.choice_count !== undefined) {
      choiceCounts[r.choice_count] = (choiceCounts[r.choice_count] || 0) + 1;
    }
    if (r.hook_type) {
      hookTypes[r.hook_type] = (hookTypes[r.hook_type] || 0) + 1;
    }
    if (r.structure) {
      structures[r.structure] = (structures[r.structure] || 0) + 1;
    }
  });

  console.log('📊 选择数分布:');
  Object.keys(choiceCounts).sort().forEach(k => {
    console.log(`   ${k} 种选择: ${choiceCounts[k]} 篇`);
  });

  console.log('\n🪝 互动钩子分布:');
  Object.entries(hookTypes).forEach(([k, v]) => {
    console.log(`   ${k}: ${v} 篇`);
  });

  console.log('\n🏛️ 结构分布:');
  Object.entries(structures).forEach(([k, v]) => {
    console.log(`   ${k}: ${v} 篇`);
  });

  const violations = [];
  for (let i = 1; i < records.length; i++) {
    const prev = records[i - 1];
    const curr = records[i];
    if (prev.choice_count !== undefined && curr.choice_count !== undefined && prev.choice_count === curr.choice_count) {
      violations.push(`篇目 #${prev.id}(${prev.title}) 与 #${curr.id}(${curr.title}) 选择数相邻重复 (${curr.choice_count})`);
    }
    if (prev.hook_type && curr.hook_type && prev.hook_type === curr.hook_type) {
      violations.push(`篇目 #${prev.id}(${prev.title}) 与 #${curr.id}(${curr.title}) 钩子形态相邻重复 (${curr.hook_type})`);
    }
  }

  if (violations.length > 0) {
    console.log('\n⚠️ 历史相邻重复违规记录:');
    violations.forEach(v => console.log(`   - ${v}`));
  } else {
    console.log('\n🎉 历史排期良好，未发现相邻重复违规！');
  }
  console.log('');
}

function cmdExport(args) {
  const account = args._[1];
  if (!account) {
    console.error('❌ 请提供账号简称，如: node scripts/ledger.js export 小满');
    process.exit(1);
  }
  const ledgerPath = getLedgerPath(account, args.workspace);
  const records = loadLedger(ledgerPath);
  const outPath = args.output || path.join(path.dirname(ledgerPath), `防批量登记_${account}.md`);

  const now = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const lines = [
    `# 防批量登记台账 · ${account}`,
    '',
    `> 自动导出自 \`${path.basename(ledgerPath)}\` | 导出时间：${now}`,
    '',
    '## 逐篇登记表',
    '',
    '| # | 日期 | 标题 | 人物称呼 | 选择数 | 钩子形态 | 结构骨架 | 对仗/加粗 | 标签 |',
    '|---|---|---|---|---|---|---|---|---|---|'
  ];

  records.forEach(r => {
    const names = (r.character_names || []).join(', ');
    const tags = (r.tags || []).join(' ');
    const boldInfo = `对仗${r.antithesis_count || 0}/加粗${r.bold_count || 0}`;
    lines.push(
      `| ${r.id || ''} | ${r.date || ''} | ${r.title || ''} | | ${names} | ${r.choice_count !== undefined ? r.choice_count : ''} | ${r.hook_type || ''} | ${r.structure || ''} | ${boldInfo} | ${tags} |`
    );
  });

  lines.push('');
  fs.writeFileSync(outPath, lines.join('\n'), 'utf8');
  console.log(`✅ 已成功导出 Markdown 台账: ${outPath}`);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const cmd = args._[0];

  if (!cmd) {
    console.log(`
用法: node scripts/ledger.js <子命令> [参数]

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
    `);
    process.exit(0);
  }

  switch (cmd) {
    case 'init': return cmdInit(args);
    case 'check': return cmdCheck(args);
    case 'suggest': return cmdSuggest(args);
    case 'log': return cmdLog(args);
    case 'report': return cmdReport(args);
    case 'export': return cmdExport(args);
    default:
      console.error(`❌ 未知命令: ${cmd}`);
      process.exit(1);
  }
}

main();
