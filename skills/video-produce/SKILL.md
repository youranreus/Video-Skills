---
name: video-produce
description: 预览、执行和恢复明确授权的图片导入、Wan 视频与 Qwen TTS 任务。
---

# video-produce

使用 scripts/workflow.py 作为整合版入口；调用 prepare、confirm、run、status、collect。复用 production_tool.py 的指纹、授权和取回记录，不另建任务队列。prepare 会读取资产、媒体、规则并检查输入契约。明确授权可覆盖展示过的批次，不让用户重复确认未改变的任务；程序确认口令由助手根据真实授权填写。每个 job 只提交一次；中断优先 collect，结果未知则核查，不自动重投。质量重生成使用新 job 和输出版本，需用户指令。结果先 candidate，再实际审看采用。

## 共同执行契约

生成和修改前读取作品 AGENTS.md、当前资产版本和规则。创作正文与运行记录分离：Markdown 拥有创作事实，隐藏的 .short-drama 仅记录生产事务。规则命中必须写出落实方式，主观验收保持待审。

只读取当前任务需要的参考。上游参考提供技法；其中单集独占资产、固定五文档、输出仅限单集和逐步确认等旧组织约定由本整合版替代。格式与命令详见 [项目契约](references/integration.md)。
