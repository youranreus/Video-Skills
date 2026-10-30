---
name: video-novel-analyze
description: 对已有长篇原著进行改编分析和分集候选整理。
---

# video-novel-analyze

依据 references 中的原著分析方法，仅在用户需要时执行；输出项目开发中的分析材料，后续路由 video-develop 和 video-write，不建立并行正式剧本。

## 共同执行契约

生成和修改前读取作品 AGENTS.md、当前资产版本和规则。创作正文与运行记录分离：Markdown 拥有创作事实，隐藏的 .short-drama 仅记录生产事务。规则命中必须写出落实方式，主观验收保持待审。

只读取当前任务需要的参考。上游参考提供技法；其中单集独占资产、固定五文档、输出仅限单集和逐步确认等旧组织约定由本整合版替代。格式与命令详见 [项目契约](references/integration.md)。
