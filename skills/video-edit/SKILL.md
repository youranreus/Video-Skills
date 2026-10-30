---
name: video-edit
description: 将采用素材和对白音轨剪辑、混音并导出成片。
---

# video-edit

剪辑单记录采用的精确素材与入出点，原素材保留。调用本技能原有 edit_tool.py 剪辑工具；音轨编排由 video-produce 的 mix_audio.py 执行，明确 keep/replace 原声以避免重复对白。口型修正首版未接入，发现偏差标记重生成或外部处理，不能宣称自动修好。导出统一交 video-produce workflow.py export。

## 共同执行契约

生成和修改前读取作品 AGENTS.md、当前资产版本和规则。创作正文与运行记录分离：Markdown 拥有创作事实，隐藏的 .short-drama 仅记录生产事务。规则命中必须写出落实方式，主观验收保持待审。

只读取当前任务需要的参考。上游参考提供技法；其中单集独占资产、固定五文档、输出仅限单集和逐步确认等旧组织约定由本整合版替代。格式与命令详见 [项目契约](references/integration.md)。
