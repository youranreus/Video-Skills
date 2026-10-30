# Video-Skills

个人 AI 视频制作技能套件：山音编剧 → 项目资产库 → 分镜与参考图 → Wan 3.0 / Qwen TTS → 剪辑 → 经验回流。

版本 0.1.0。Python 3.11+，核心脚本仅使用标准库。视频/非 WAV 音频检查和混音需要 ffmpeg/ffprobe。没有调用付费 API；离线夹具不代表生成质量。

## 安装与使用

推荐在作品项目目录中安装整套技能（需要 Node.js 22.20+ 和 Git）：

```bash
npx skills@latest add youranreus/Video-Skills --skill '*' --agent codex -y
```

跨项目使用可安装到用户级：

```bash
npx skills@latest add youranreus/Video-Skills --skill '*' --agent codex -g -y
```

先查看技能列表：

```bash
npx skills@latest add youranreus/Video-Skills --list
```

整套共 12 个技能；`video-workflow` 会路由其他技能，生产与恢复脚本位于 `video-produce`，因此请用 `--skill '*'` 安装全套。其他 Agent 可替换 `--agent codex`，或省略该参数交互选择。安装后在新聊天使用 `$video-workflow`，指定作品目录。内置图片生成仍取决于宿主是否提供该工具，否则走外部图片导入。

更新与卸载由同一安装工具管理：

```bash
npx skills@latest update
npx skills@latest remove --skill video-workflow video-develop video-write video-assets video-images video-storyboard video-voice video-motion video-produce video-review video-edit video-novel-analyze --agent codex -y
```

全局卸载在 remove 命令加 `-g`。如果需要完全控制安装位置，也可以克隆仓库并使用本地安装工具：

```bash
python3 scripts/install.py install --target /你选择的技能安装目录
python3 scripts/install.py uninstall --target /你选择的技能安装目录
```

本地安装工具默认拒绝覆盖，卸载保护已修改文件；不要混用两种工具管理同一安装。Python 3.11+ 用于项目与生产脚本，ffmpeg/ffprobe 用于相关媒体处理。无需执行 npm install 或发布 npm 包。

从 `$video-workflow` 开始，也可直接使用 `$video-write`、`$video-assets`、`$video-voice` 等阶段技能。真实作品放在独立目录：

```bash
python3 skills/video-produce/scripts/workflow.py init /作品路径 --title 示例作品
python3 skills/video-produce/scripts/workflow.py check /作品路径
```

- [完整项目格式、命令与生成契约](skills/video-produce/references/integration.md)
- [待生成试片包](examples/starter/README.md)
- [离线验收报告](docs/acceptance.md)
- [上游来源和改动边界](docs/provenance.md)

`资产库/` 保存角色、场景、道具版本，角色声音与外观同目录。每集保存本集状态、五份创作文档、配音单和制作成果。规则按阶段/模型/模式加载，失败案例验证后才能成为执行规则。

默认模型为 wan3.0-video 和 qwen-audio-3.0-tts-plus。正式生成前需要同地域的工作空间、环境变量 DASHSCOPE_API_KEY、已采用参考图和已选声线。任务预览不联网；显式执行才上传和调用服务。首尾帧不混入音频，重复质量尝试不自动提交。

## 从新聊天恢复

安装后直接说：

```text
$video-workflow 恢复 /我的作品目录，告诉我当前进度并继续。
$video-workflow 恢复 /我的作品目录，继续 EP002 的分镜。
```

也可直接运行 `python3 skills/video-produce/scripts/workflow.py resume /作品路径`，限定单集加 `--episode EP002`。恢复报告从现有文件与生产记录重建，包含当前成果、验收未知/待审内容、在途/待取回任务、阻塞和下一阶段建议。不会自动联网、生成或重投；不把“文件存在”当成“已验收”。

## 开发验证

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_skills.py
```

保留的上游 Dashboard 和旧项目工具属于继承代码，尚未适配整合版资产数据；首版不把它们作为整合版用户入口。整合版检查与导出统一用 workflow.py。

## 来源

基于 [drama-skills](https://github.com/zenstory-ai/drama-skills) 与由 **@山音** 设计的 [山音超级编剧大师](https://github.com/Shanyin-ai/shanyin-screenwriting-master)。固定版本及修改记录见 UPSTREAM.json 和来源说明；原许可证保留在 third_party。
