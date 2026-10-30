---
name: video-storyboard
description: 把剧本转为分镜、关键帧和跨镜动作边界。
---

# video-storyboard

读取单集引用的资产版本和状态。保留 SHOT-、IMG-、REF-、PLAN- 不同含义。分镜.md 的 video-shots 块声明可机械核对的状态链，正文说明镜头职责与动作。对白先用 video-voice 试听测时，再锁镜长。同场续接以采用视频实际尾帧为准，不用计划尾图冒充实际尾帧。动作与对白冲突时明确控制目标或拆镜，不静默牺牲剧情。

## 共同执行契约

生成和修改前读取作品 AGENTS.md、当前资产版本和规则。创作正文与运行记录分离：Markdown 拥有创作事实，隐藏的 .short-drama 仅记录生产事务。规则命中必须写出落实方式，主观验收保持待审。

只读取当前任务需要的参考。上游参考提供技法；其中单集独占资产、固定五文档、输出仅限单集和逐步确认等旧组织约定由本整合版替代。格式与命令详见 [项目契约](references/integration.md)。

## 按需技法参考

只在当前任务涉及相应主题时读取：

- [shot-craft](references/shot-craft.md)
