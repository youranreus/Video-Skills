# Video-Skills 整合契约 v1

适用于 `short-drama.json` 中 `video_skills_format: video-skills/1` 的作品。Python 3.11+；生产只从 `video-produce/scripts/workflow.py` 进入。全部 video-* 技能作为一组安装。上游 project_tool、creator_markdown_check 仅用于保留的上游格式；整合版用 workflow.py check。

## 文件所有权

- 项目开发：故事动机、关系、弧光、世界观；山音方法由 video-write 按类型加载。
- 资产库：角色、场景、道具的稳定身份、外观和声线版本；原始输入留输入目录。
- 每集视觉设定：引用资产版本、进入和结束状态；分镜：按镜号排列的状态变化及瞬态；正式剧本：台词唯一来源。
- 图片提示词与视频提示词：可复制正文及准确输入绑定；配音单：引用台词、声线、表演与音频采用结果。
- 制作成果：镜头媒体；资产生成媒体放对应资产目录。媒体登记初始 candidate；实际审看后才能 accepted。
- 规则/经验：项目内规则与证据；.short-drama：上游生产事务，非创作真相。

## 可读 Markdown 与少量数据块

数据块是所在 Markdown 的唯一机器可读事实，不另写长期 JSON 副本。块外正文解释意图，不重复维护字段。每个文件对应类型只允许一个块。

### 资产

`资产库/角色/CHAR-LIN/设定.md` 的 `video-asset` 块由 add-version 维护：`id`、`versions`（版本到项目相对路径）、`seals`（版本文件摘要）。采用版本不可覆盖。角色外观/声音文件放该角色目录，变体可作为独立版本并说明继承与差异；不同变体生效时点属于剧集。

用 `video-version` 块起草版本文件，然后运行 add-version：

```json
{"id":"CHAR-LIN","version":"v001","status":"candidate","description":"基础外观与声线，待选型","files":[],"voice":{"model":"qwen-audio-3.0-tts-plus","id":null,"audition":null,"pronunciation":{}}}
```

采用时新建版本，status 为 accepted，files 为 `[{"path":"资产库/.../face.png","sha256":"实际摘要"}]`。voice.id 为实际选定音色，audition 为已听过的试听路径并包含在 files；暂未选择声线可省略 voice，TTS 会阻止投产。状态变化使用如 `CHAR-LIN.sleeve` 的键，值为项目定义的明确状态。

### 单集与镜头

视觉设定的 `video-episode`：

```json
{"assets":["CHAR-LIN@v002","LOC-ROOM@v001"],"entry":{"CHAR-LIN.sleeve":"intact"},"exit":{"CHAR-LIN.sleeve":"torn"},"deliverables":[]}
```

分镜的 `video-shots` 是按顺序的数组，每项有 `id`、`duration`、`start`、`end`，真实变化写 `changes`：

```json
{"id":"SHOT-EP001-001","duration":5,"start":{"CHAR-LIN.sleeve":"intact"},"changes":{"CHAR-LIN.sleeve":{"before":"intact","after":"torn","cause":"EP001-SC001 擦碰门框"}},"end":{"CHAR-LIN.sleeve":"torn"},"media":[]}
```

跨集 entry 必须继承上集 exit。确有跳时或修复时，`entry_changes` 将变化键指向项目内说明文档；检查器只证明来源存在，因果是否成立需审稿。纯姿势等不持续事实写在分镜正文，无需进入状态链。

### 媒体与提示词

`import` 复制到指定位置并创建 `<媒体文件>.md` 的 `video-media` 块，记录来源、用途、摘要和状态。`accept-media` 写实际验收说明。内置工具生成的图片同样导入登记。

视频提示词的 `video-inputs` 对象以 MOTION ID 为键，值有 `assets`、`duration` 和有序 `media`。每个 media 是 `{"path":"项目内文件","record":"媒体登记.md","type":"first_frame"}`。模式使用 first_frame、first_last_frame、reference 或 text；参考类型使用 reference_image/reference_audio/reference_video。项目相对文件是权威输入，上传 URL 只在执行时产生。

对应 `## MOTION-EP001-001 · 标题` 下保留 `### 可复制提示词` 与引用块正文。prepare 检查任务与文档输入、资产、镜长、提示词完全一致。IMG 是提示词，REF 是实际参考槽位，PLAN 是未落实计划；它们不互相替代。

配音单的 `video-lines` 数组，每项有 `id`（LINE-EP001-001）、`script`（剧本路径）、`text`、`voice_asset`（ID@版本）、`instruction`、`audio`。TTS job.parameters.line_id 引用该行；台词必须来自剧本，选用音色从 voice_asset 解析。生成后把采用音频路径与实际时长记录在本行；视频分镜的 dialogue_audio 指向实际音频，检查器核验其时长。

## CLI

以下 `TOOL` 指已安装 video-produce/scripts/workflow.py；调用时用实际绝对路径。

```text
python3 TOOL init /作品路径 --title 作品名
python3 TOOL check /作品路径
python3 TOOL add-version /作品路径 --file /版本草案.md
python3 TOOL impact /作品路径 --asset CHAR-LIN@v001
python3 TOOL import /作品路径 --file /素材.png --target 资产库/角色/CHAR-LIN/外观/face-v001.png --origin 用户提供 --purpose 身份
python3 TOOL accept-media /作品路径 --record 资产库/角色/CHAR-LIN/外观/face-v001.png.md --review "用户认可外观；本轮已审看"
python3 TOOL prepare /作品路径 --file /单次任务.json
python3 TOOL confirm /作品路径 --job-id JOB-001 --confirmation "预览返回的精确口令"
python3 TOOL adapter-config /作品路径 --out /项目外/adapter.json
python3 TOOL run /作品路径 --job-id JOB-001 --adapter-config /项目外/adapter.json
python3 TOOL status /作品路径 --job-id JOB-001
python3 TOOL collect /作品路径 --job-id JOB-001 --adapter-config /项目外/adapter.json
python3 TOOL export /作品路径 --episode EP001 --out /项目外/交付目录
```

job 使用上游字段：job_id、modality、adapter（aliyun）、prompt、source、视频的 source_entry、outputs（唯一新版本路径）、parameters。parameters：mode、duration、assets、media、rule_actions；TTS 使用 line_id。prepare 自动补模型、连接配置、规则报告和输入快照。任务 JSON 是运行请求，不替代正式 Markdown。

用户已授权展示过的批次时，助手可逐任务 confirm/run；不可把程序口令当用户授权。一个 job 一次提交，失败后优先 collect；新质量尝试建立新 job 并取得授权。未知提交结果需要核查。程序结果只代表执行完成，媒体仍需验收。

## 规则与经验

`case --file case.json` 写入经验 Markdown。字段：id、job_id、inputs（准确版本/文件）、observation、observer、change_set、preserve_set、conclusion、status。status 可为 hypothesis、verified、historical、failed。无法查看媒体时只能记录文字风险或来源转述。

`promote --case 经验/案例/CASE-001.md --file rule.json` 只接受 verified。规则字段：id、stages（image/video/tts）、models、modes、instruction；空数组代表该维度不限。新规则自动记录 evidence 和 active 状态。user_constraint 类型直接来自明确用户要求，保留证据文件。`supersede --old 规则/旧.md --new 规则/新.md` 退出旧规则。

prepare 为所有适用规则要求 parameters.rule_actions 中有具体落实方式，并在预览标 pending_review。规则文件和证据进入任务快照；修改后旧授权失效。内置出图同样先 prepare 一个 image 任务获取规则预览，再调用内置工具、导入产物；不使用 aliyun adapter 执行 image。

## 官方连接与后期

production.region 默认 cn-beijing，workspace_id 需真实值；endpoint 默认由地域与工作空间构建，也可显式配置同地域官方 HTTPS `/api/v1`。仅从 DASHSCOPE_API_KEY 环境变量读取凭据。不切换模型或地域兜底。

Wan 图片以 Base64 输入，音频/视频通过同地域临时 OSS 上传。Qwen HTTP 非流式返回音频 URL，立即下载保存并测时。取回使用原任务 ID 或保存的 TTS 结果 URL，不重新合成。临时 URL 保存在私有运行元数据，不进入交付。

音轨编排由 video-produce/scripts/mix_audio.py 执行，默认仅打印 ffmpeg 参数，--run 执行。plan 包含 video、output、duration、original_audio（keep/replace）、tracks（path/start/gain）。保留原素材；没有自动口型修复。实际渲染依赖 ffmpeg，非 WAV 测时依赖 ffprobe。

## 首次声线试听

为避免“没有试听就不能建声线、没有声线又不能生成试听”的循环，配音单可有明确的试听行：`audition: true`、`voice_asset: null`。试听任务 parameters 使用 `audition: true`、`voice: 实际候选音色ID`、`assets: []` 和 line_id。台词和 instruction 仍须与配音单一致，台词须来自正式剧本。试听输出始终为 candidate，回听后再建带试听文件的采用声线版本；该路径不能用于绕过正式对白的声线绑定。

采用资产的 files 中每项还需对应媒体登记文件（默认 `<path>.md`，也可通过 record 字段指定）；采用版本检查摘要及媒体采用状态，防止候选图被当正式资产。版本本身不可原地修改，晋升采用时建立新版本。

## 新聊天恢复

```text
python3 TOOL resume /作品路径
python3 TOOL resume /作品路径 --episode EP002
```

恢复只读本地文件，不调用供应商、不写进度文件。报告包括 completed、pending_review、episodes、assets、jobs、in_flight、blockers、structural_check、next_actions。即使限定一集，也检查全项目的在途任务，避免遗漏已计费请求。provider_state=not_queried 表示供应商实时状态尚未查询。

优先顺序：有句柄的未完成任务取回／未知提交核查 → 处理损坏和冲突 → 检查已有任务预览 → 从已有最深入阶段读取与审阅 → 补下一个必要阶段。图片提示词和配音单可按实际作品需要省略，不机械补齐。用户指定阶段优先于默认建议，独立工作不受无关素材阻塞。

文件存在不证明文稿已验收。可在拥有正文的文稿末尾加入唯一 `video-review` 块：`{"status":"accepted","evidence":"实际用户验收依据","content_sha256":"正文摘要"}`；status 也可为 pending/revise。摘要算法是移除该数据块后对 `.strip()` 的 UTF-8 正文取 SHA-256，可用 video-produce/scripts/resume.py 的 review_digest 计算。摘要缺失或不匹配时恢复为验收状态未知。此块只记录原文稿的验收，不保存第二套阶段状态。

媒体仍以 video-media 登记和字节摘要为准。没有登记的已存在媒体列为待核对，不丢弃、不自动重新生成。完整结构检查对早期项目可能有缺口，其报告不代表当前写作阶段失败。
