# Second World Poster — Universal Agent Skill

通用系列营销海报技能，适用于 Claude、Codex 及支持 `SKILL.md` / Agent Skills 的其他智能体。

## 能力
- 一个卖点策划多张系列海报。
- 张数由用户指定；未指定默认3张，建议3–4张。
- 每张海报角度、标题、文案和视觉创意独立，不重复。
- 每张图单独生成，禁止擅自拼图或合并照片。
- 上半部分保留真实照片，下半部分由照片自身结构自然延伸为 Second World 第二世界。
- 融合商业洞察、受众分析、营销文案和真实性检查。

## 安装

### Claude Code
将本文件夹放入：
- 项目级：`.claude/skills/second-world-poster/`
- 用户级：`~/.claude/skills/second-world-poster/`

### Codex
将本文件夹放入：
- 项目级：`.agents/skills/second-world-poster/`
- 用户级：`~/.agents/skills/second-world-poster/`

确认 `SKILL.md` 位于 `second-world-poster` 文件夹根目录。

### 其他 Agent
把整个文件夹放入其技能目录，并确保 Agent 能读取根目录的 `SKILL.md`。如平台要求注册技能路径，请按平台说明配置。

## 使用示例
```text
围绕“员工健康，企业未来”这个卖点，策划并生成4张系列海报。
```
```text
核心卖点：快速安装
目标用户：中小企业采购负责人
生成张数：5张
先给我系列策划方案，确认后再生成。
```
```text
我上传了3张真实场景照片。请每张照片单独设计一张3:4海报，不要拼图。
```

## 默认规则
- 未指定张数：3张；推荐3–4张。
- 默认比例：3:4竖版。
- 一张海报只讲透一个价值。
- 每张海报独立生成、独立传播。
- 不编造数据、评价、资质、奖项或服务承诺。
