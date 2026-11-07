#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_density.py - 敏感词密度与高危组合检测脚本
用于微信公众号文章发前自检：统计同类敏感词出现密度，识别金融/纠纷联想词与高危相邻组合。
"""

import sys
import os
import re

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# 敏感词群定义
NEGATIVE_JOB_WORDS = [
    '被裁', '失业', '降薪', '裁员', '优化', '下岗', '待业', '找不到工作'
]

FINANCIAL_DISPUTE_WORDS = {
    '流水': '建议改为：卖了一千多块 / 每天账上能进点钱（避开资金流水金融联想）',
    '补偿金': '建议改为：拿了笔补偿 / 结清走人（避开劳资纠纷联想）',
    '赔偿金': '建议改为：拿了笔钱 / 双方协商结清',
    '税前': '建议改为：到手或者口语化表述（如年薪几十万）',
}

ENGLISH_JARGON = {
    'offer': '建议改为：有份工作找来了 / 有家公司想让我去',
    'headcount': '建议改为：编制 / 名额',
    'kpi': '建议改为：指标 / 考核',
    'pip': '建议改为：被约谈 / 被末位淘汰',
}

HIGH_RISK_COMBOS = [
    (r'(失业|被裁|下岗|降薪)[^，。！？\n]{0,3}(妇女|女性|宝妈|孕妇|中年女人)', '弱势群体+就业困境组合，极高拦截风险，建议拆解转述'),
    (r'(降薪|降了|砍掉)[^，。！？\n]{0,3}\d+%', '数字+就业挫折组合，建议改用生活化情绪转述（如“工资降到这个份上”）'),
    (r'税前[^，。！？\n]{0,3}\d+万', '精确高薪数字组合，容易触发金融联想'),
]

def analyze_text(text):
    warnings = []
    passes = []
    
    # 1. 就业负面词密度
    job_counts = {}
    total_job_count = 0
    for w in NEGATIVE_JOB_WORDS:
        cnt = len(re.findall(re.escape(w), text))
        if cnt > 0:
            job_counts[w] = cnt
            total_job_count += cnt
            
    if total_job_count > 3:
        over_words = [f"「{w}」({c}次)" for w, c in job_counts.items() if c > 2]
        over_str = f"，其中单个词超标: {', '.join(over_words)}" if over_words else ""
        warnings.append(f"就业负面词群总密度过高：累计出现 {total_job_count} 次（建议 ≤3 次）{over_str}。建议交替使用「离开公司」「换了活法」「没接着干」等生活化词汇稀释。")
    elif total_job_count > 0:
        over_words = [f"「{w}」({c}次)" for w, c in job_counts.items() if c > 2]
        if over_words:
            warnings.append(f"单项就业词频偏高：{', '.join(over_words)}。单个词全文建议 ≤2 次。")
        else:
            passes.append(f"就业负面词频达标：累计 {total_job_count} 次，分布较均匀 ({', '.join([f'{w}:{c}' for w, c in job_counts.items()])})。")
    else:
        passes.append("就业负面词频达标：全文未见高频就业负面词。")
        
    # 2. 金融与资质联想词
    found_financial = []
    for w, tip in FINANCIAL_DISPUTE_WORDS.items():
        cnt = len(re.findall(re.escape(w), text))
        if cnt > 0:
            found_financial.append((w, cnt, tip))
            
    if found_financial:
        for w, cnt, tip in found_financial:
            warnings.append(f"发现涉金融/纠纷敏感词「{w}」出现 {cnt} 次。{tip}")
    else:
        passes.append("涉金融/纠纷联想词排查通过：无直白流水、补偿金等词汇。")
        
    # 3. 英文词汇排查
    found_english = []
    for w, tip in ENGLISH_JARGON.items():
        cnt = len(re.findall(re.escape(w), text, re.IGNORECASE))
        if cnt > 0:
            found_english.append((w, cnt, tip))
            
    if found_english:
        for w, cnt, tip in found_english:
            warnings.append(f"发现英文特定语境词「{w}」出现 {cnt} 次。{tip}")
    else:
        passes.append("英文特定语境词排查通过。")
        
    # 4. 高危相邻组合
    found_combos = []
    for pattern, reason in HIGH_RISK_COMBOS:
        matches = re.findall(pattern, text)
        if matches:
            found_combos.append((pattern, len(matches), reason))
            
    if found_combos:
        for pat, cnt, reason in found_combos:
            warnings.append(f"命中高危敏感词组合（{cnt} 处）：{reason}。")
    else:
        passes.append("高危相邻词汇组合排查通过：无敏感词直接相邻。")
        
    return passes, warnings, total_job_count

def main():
    if len(sys.argv) < 2:
        print("用法: python3 scripts/check_density.py <文章文件路径>")
        sys.exit(1)
        
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"❌ 找不到文件: {path}")
        sys.exit(1)
        
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
    print(f"🔍 正在检测文章敏感词密度与机审风险: {os.path.basename(path)}")
    print("=" * 60)
    
    passes, warnings, total_job = analyze_text(content)
    
    for p in passes:
        print(f"✅ {p}")
        
    if warnings:
        print("\n⚠️ 发现以下潜在机审风险（请在发布前稀释或替换）：")
        for i, w in enumerate(warnings, 1):
            print(f"  {i}. {w}")
        print("\n💡 降敏原则：降频（单词≤2次）、换域（日常口语）、拆组合（转述化解）。若检测报警可使用二分法快速定位。")
        sys.exit(2)
    else:
        print("\n🎉 全文敏感词密度排查完全通过，机审合规良好！")
        sys.exit(0)

if __name__ == '__main__':
    main()
