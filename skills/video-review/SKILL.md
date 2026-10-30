---
name: video-review
description: 审看参考图、视频和声音，记录失败经验、验证修订并维护适用规则。
---

# video-review

区分文字风险、实际观察、原因假设与验证结论。案例包含准确任务、输入、观察者、修改项、保留项与结果；case 保存，verified 才可 promote。规则按阶段/模型/模式匹配，supersede 退出旧规则。未查看媒体不推断质量通过；历史记录标 historical，不当本轮实测。不自动提交质量重生成。

## 共同执行契约

生成和修改前读取作品 AGENTS.md、当前资产版本和规则。创作正文与运行记录分离：Markdown 拥有创作事实，隐藏的 .short-drama 仅记录生产事务。规则命中必须写出落实方式，主观验收保持待审。

只读取当前任务需要的参考。上游参考提供技法；其中单集独占资产、固定五文档、输出仅限单集和逐步确认等旧组织约定由本整合版替代。格式与命令详见 [项目契约](references/integration.md)。

## 按需技法参考

只在当前任务涉及相应主题时读取：

- [project-calibration](references/project-calibration.md)
- [production-quality-gates](references/production-quality-gates.md)
