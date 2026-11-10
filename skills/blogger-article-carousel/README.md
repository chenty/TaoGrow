# Blogger Article Carousel Skill

一套可迁移到 Claude Code、Codex 等支持 Agent Skills 的通用 Skill，通过多轮共创把文章转成系列信息卡/轮播图文。可在原文有依据时，将具体选题连接到个人成长、商业经营与作者的个人 IP 视角。

## 必需依赖

**生成最终出图提示词必须依赖 `handdraw-style-prompter` Skill。** 本 Skill 不自己编写或改写最终提示词：它负责文章拆解、访谈、卡片故事线、逐卡文案与视觉 brief；`handdraw-style-prompter` 负责根据其画风/图型/颜色库和模型规则生成每张卡的最终提示词。图片生成工具是可选的；如没有图片工具，仍可交付依赖 Skill 生成的提示词。

依赖仓库：[`yang0/handraw-style`](https://github.com/yang0/handraw-style)。请安装**完整仓库**，保留仓库根目录 `SKILL.md`、`images/` 和嵌套的 `skills/handdraw-style-prompter/`；不要只复制嵌套的一个 `SKILL.md`，否则画廊与参考资源可能缺失。

## 内容

- `SKILL.md`：入口、互动流程与依赖委托规则
- `references/interactive-workflow.md`：分轮提问脚本
- `references/editorial-structure.md`：文章拆解、多维故事线与个人 IP 升维
- `references/visual-system.md`：系列视觉 brief 与 handdraw-style-prompter 交接
- `references/qa-checklist.md`：内容与图像校对清单
- `references/interaction-notes.md`：争议内容、信息不足时的处理边界
- `examples/sample-dialogue.md`：示例对话
- `examples/card-outline-template.md`：自适应逐卡大纲

## 安装

两个 Skill 都要放在同一个 Agent 能发现的 skills 目录下，并保留各自文件夹：

### Claude Code

- 用户级：`~/.claude/skills/handdraw-style-prompter/`（复制完整 `yang0/handraw-style` 仓库）
- 用户级：`~/.claude/skills/blogger-article-carousel/`（复制本 Skill 文件夹）
- 项目级也可分别放入 `<项目>/.claude/skills/` 下。

### Codex

- 用户级：`~/.agents/skills/handdraw-style-prompter/`（复制完整 `yang0/handraw-style` 仓库）
- 用户级：`~/.agents/skills/blogger-article-carousel/`（复制本 Skill 文件夹）
- 项目级也可分别放入 `<项目>/.agents/skills/` 下。

其他兼容 Agent：把两个完整文件夹放入该 Agent 能发现的 Skill 目录，并确认它能调用/读取 `handdraw-style-prompter`。按客户端要求重载或开启新会话。不同版本的目录约定可能变化，以客户端文档为准。

如果 `handdraw-style-prompter` 未安装或不可用，`blogger-article-carousel` 仍能完成文章分析、访谈、逐卡文案和视觉 brief，但会暂停最终出图提示词与图片生成；不会自行绕过依赖。

## 使用示例

- “把这篇文章做成小红书系列图文，先多轮问我几个问题。”
- “帮我把博客拆成 7 张 Instagram 轮播卡，先给我看文案大纲。”
- “基于这份长文，确认故事线和视觉方向后，让 handdraw-style-prompter 为每张卡生成提示词。”
- “把这个具体选题提升到个人成长/商业经营角度，但先让我确认是否符合文章原意。”

默认不会自动发布到社交平台，也不会把原文另存或上传到外部服务。
