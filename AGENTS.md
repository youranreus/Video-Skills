# Video-Skills 开发约定

这是技能与工具仓库，真实作品放在独立目录。修改前读取 README.md、docs/provenance.md 和对应技能的 integration.md。

- 创作事实归 Markdown；运行事务复用 video-produce 的 production_tool，不新建并行任务系统。
- 资产身份、单集状态和镜头瞬态分层；稳定版本不覆写。候选和采用必须区分。
- 上游固定提交见 UPSTREAM.json。保留来源与许可，选择性更新，不用上游覆盖本地。
- 新接口以官方文档为依据，离线模拟与真实验证分别报告；本仓库测试不提交付费任务。
- skills/*/references/integration.md 由 docs/project-contract.md 同步生成，修改源后运行 scripts/sync_contract.py。
- Python 3.11+，核心仅用标准库；校验运行 `python3 -m unittest discover -s tests -v` 和 `python3 scripts/validate_skills.py`。
- 图像、声音和实际内容质量需要对应观察证据。测试夹具不冒充媒体验收。
