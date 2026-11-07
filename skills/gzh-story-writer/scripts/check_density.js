#!/usr/bin/env node
/**
 * check_density.js - 敏感词密度与高危组合检测脚本 (Node.js 版)
 */

const fs = require('fs');
const path = require('path');

const NEGATIVE_JOB_WORDS = [
  '被裁', '失业', '降薪', '裁员', '优化', '下岗', '待业', '找不到工作'
];

const FINANCIAL_DISPUTE_WORDS = {
  '流水': '建议改为：卖了一千多块 / 每天账上能进点钱（避开资金流水金融联想）',
  '补偿金': '建议改为：拿了笔补偿 / 结清走人（避开劳资纠纷联想）',
  '赔偿金': '建议改为：拿了笔钱 / 双方协商结清',
  '税前': '建议改为：到手或者口语化表述（如年薪几十万）',
};

const ENGLISH_JARGON = {
  'offer': '建议改为：有份工作找来了 / 有家公司想让我去',
  'headcount': '建议改为：编制 / 名额',
  'kpi': '建议改为：指标 / 考核',
  'pip': '建议改为：被约谈 / 被末位淘汰',
};

const HIGH_RISK_COMBOS = [
  { pattern: /(失业|被裁|下岗|降薪)[^，。！？\n]{0,3}(妇女|女性|宝妈|孕妇|中年女人)/g, reason: '弱势群体+就业困境组合，极高拦截风险，建议拆解转述' },
  { pattern: /(降薪|降了|砍掉)[^，。！？\n]{0,3}\d+%/g, reason: '数字+就业挫折组合，建议改用生活化情绪转述（如“工资降到这个份上”）' },
  { pattern: /税前[^，。！？\n]{0,3}\d+万/g, reason: '精确高薪数字组合，容易触发金融联想' },
];

function analyzeText(text) {
  const passes = [];
  const warnings = [];

  // 1. 就业负面词密度
  const jobCounts = {};
  let totalJobCount = 0;
  for (const w of NEGATIVE_JOB_WORDS) {
    const reg = new RegExp(w, 'g');
    const matches = text.match(reg);
    const cnt = matches ? matches.length : 0;
    if (cnt > 0) {
      jobCounts[w] = cnt;
      totalJobCount += cnt;
    }
  }

  if (totalJobCount > 3) {
    const overWords = Object.entries(jobCounts).filter(([w, c]) => c > 2).map(([w, c]) => `「${w}」(${c}次)`);
    const overStr = overWords.length ? `，其中单个词超标: ${overWords.join(', ')}` : '';
    warnings.push(`就业负面词群总密度过高：累计出现 ${totalJobCount} 次（建议 ≤3 次）${overStr}。建议交替使用「离开公司」「换了活法」「没接着干」等生活化词汇稀释。`);
  } else if (totalJobCount > 0) {
    const overWords = Object.entries(jobCounts).filter(([w, c]) => c > 2).map(([w, c]) => `「${w}」(${c}次)`);
    if (overWords.length) {
      warnings.push(`单项就业词频偏高：${overWords.join(', ')}。单个词全文建议 ≤2 次。`);
    } else {
      passes.push(`就业负面词频达标：累计 ${totalJobCount} 次，分布较均匀 (${Object.entries(jobCounts).map(([w, c]) => `${w}:${c}`).join(', ')})。`);
    }
  } else {
    passes.push('就业负面词频达标：全文未见高频就业负面词。');
  }

  // 2. 金融与资质联想词
  for (const [w, tip] of Object.entries(FINANCIAL_DISPUTE_WORDS)) {
    const reg = new RegExp(w, 'g');
    const matches = text.match(reg);
    if (matches && matches.length > 0) {
      warnings.push(`发现涉金融/纠纷敏感词「${w}」出现 ${matches.length} 次。${tip}`);
    }
  }
  if (!warnings.some(w => w.includes('涉金融/纠纷'))) {
    passes.push('涉金融/纠纷联想词排查通过：无直白流水、补偿金等词汇。');
  }

  // 3. 英文特定语境
  for (const [w, tip] of Object.entries(ENGLISH_JARGON)) {
    const reg = new RegExp(`\\b${w}\\b`, 'gi');
    const matches = text.match(reg);
    if (matches && matches.length > 0) {
      warnings.push(`发现英文特定语境词「${w}」出现 ${matches.length} 次。${tip}`);
    }
  }
  if (!warnings.some(w => w.includes('英文特定语境词'))) {
    passes.push('英文特定语境词排查通过。');
  }

  // 4. 高危相邻组合
  for (const item of HIGH_RISK_COMBOS) {
    const matches = text.match(item.pattern);
    if (matches && matches.length > 0) {
      warnings.push(`命中高危敏感词组合（${matches.length} 处）：${item.reason}。`);
    }
  }
  if (!warnings.some(w => w.includes('命中高危敏感词组合'))) {
    passes.push('高危相邻词汇组合排查通过：无敏感词直接相邻。');
  }

  return { passes, warnings };
}

function main() {
  const file = process.argv[2];
  if (!file) {
    console.log('用法: node scripts/check_density.js <文章文件路径>');
    process.exit(1);
  }

  if (!fs.existsSync(file)) {
    console.error(`❌ 找不到文件: ${file}`);
    process.exit(1);
  }

  const content = fs.readFileSync(file, 'utf8');
  console.log(`🔍 正在检测文章敏感词密度与机审风险: ${path.basename(file)}`);
  console.log('='.repeat(60));

  const { passes, warnings } = analyzeText(content);

  for (const p of passes) {
    console.log(`✅ ${p}`);
  }

  if (warnings.length > 0) {
    console.log('\n⚠️ 发现以下潜在机审风险（请在发布前稀释或替换）：');
    warnings.forEach((w, i) => {
      console.log(`  ${i + 1}. ${w}`);
    });
    console.log('\n💡 降敏原则：降频（单词≤2次）、换域（日常口语）、拆组合（转述化解）。若检测报警可使用二分法快速定位。');
    process.exit(2);
  } else {
    console.log('\n🎉 全文敏感词密度排查完全通过，机审合规良好！');
    process.exit(0);
  }
}

main();
