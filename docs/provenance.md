# 来源与调整

确切提交见根目录 UPSTREAM.json。drama-skills：ed095d7b53682c24a3c76cc0dfaa148dde229ddb；山音编剧：ca20ce245ae028e64418393d6cf4688b7dbe3d89。

保留并改名 drama-skills 技能、技法参考和生产/剪辑工具；新入口使用 video-*。复用原 production_tool 的任务指纹、输入快照、授权消费、输出原子提交和 collect。新增资产目录输出、契约文件快照、配置变化检查及整合版单任务禁止重新提交。原生产格式的回归夹具保持独立。

山音的方法资料从固定提交的 .skill 包提取至 video-write/references/shanyin，保留 @山音 署名。八步创作方法按格式加载；逐步暂停改为用户授权范围内连续工作，正式剧本保持唯一。其 README 对分发另有说明，原 README 和 MIT LICENSE 一并保留；本项目未作商业分发。

新增 workspace/workflow、官方适配器、安装工具、混音工具和整合测试。资产引用和连续性数据写在 Markdown 数据块中，生产 JSON 不作为第二套创作内容。

官方接口核对于 2026-10-30：
- https://help.aliyun.com/en/model-studio/wan3-video-generation-api-reference
- https://help.aliyun.com/en/model-studio/qwen-audio-tts-http-api
- https://help.aliyun.com/en/model-studio/get-temporary-file-url

初版仅做离线验收；后续真实调用结果见 docs/acceptance.md。未导入私人 Qingyi 2 媒体；个人经验由各作品本地保存，不随公共示例分发。

## 保留工具的边界

原有 Dashboard、旧初始化/导出以及旧五文档检查脚本保留用于上游格式参考与回归；整合版技能入口不调用它们。整合版的生产引擎沿用同一套 .short-drama 元数据，并由 workflow/workspace 在准备与执行前实施资产和规则检查。原有剪辑工具继续处理明确的媒体路径，新增音轨编排作为补充。

通过 skills CLI 分发时，各技能目录携带上游 LICENSE；video-write 的山音参考目录另附原 LICENSE 和 UPSTREAM-README.md，以保留单独安装后的署名与分发说明。

Token Plan 独立网关依据：https://platform.qianwenai.com/docs/token-plan/best-practices/multimodal-generation （2026-10-30 核对）。不再将 WorkspaceId 作为所有官方接入方式的必要条件。
