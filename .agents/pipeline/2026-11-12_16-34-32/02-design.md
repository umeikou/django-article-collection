# 小宇宙播客收藏技术设计（第二次修订）

## Overview

本设计在现有 Python 3、Django 5.2、Django REST Framework、SQLite、Requests、BeautifulSoup、Bootstrap 5、原生 JavaScript、Gunicorn 和 systemd 项目中增加小宇宙单集收藏。普通 URL 继续通过 `ArticleCollectionService.collect_article()` 在请求内同步收藏，现有响应、匿名普通收藏和重复文章语义不变。严格匹配的小宇宙单集 URL 在调用该 service 前分流：在短数据库事务中持久化任务并返回 HTTP 202；独立的 Django management-command worker 负责元数据、免费判定、ASR、文字稿、全文 AI 分析和最终 Article。

技术栈锁定为现有运行时依赖与 Python 标准库（`subprocess`、`json`、`re`、`hashlib`、`decimal`、`datetime`、`pathlib`、`urllib.parse`、`importlib`）。不增加 Celery、Redis、消息队列、SSE/WebSocket、密钥文件、持久音频存储或新运行时依赖。实施不得清理、覆盖或重构当前大量无关的未提交和未跟踪文件。已确认当前 `CollectionTask.article` 使用 `CASCADE`、`DeepSeekAIService.analyze_article()` 截断 3,000 字、`CollectionTaskViewSet` 当前公开只读，且 `umeikouagent.service` 以 `nginx` 用户运行 production settings。这些现状决定以下迁移、权限和服务边界。

## 提交分流、URL 验证和访问控制

新增 `articles/podcast.py`，承载播客专用的 URL 规范化、提交、状态迁移、事件、租约、脚本调用、ASR、文字稿和分析协调服务。它不会改变 `ArticleCollectionService` 的普通收藏实现。

`normalize_xiaoyuzhou_episode_url(value)` 使用 `urllib.parse.urlsplit()`，只接受长度不超过 2,048 的 HTTP/HTTPS URL，无用户名密码、无非默认端口，主机必须精确为 `xiaoyuzhoufm.com` 或 `www.xiaoyuzhoufm.com`，路径必须为 `/episode/<episode-id>` 或其单一尾随 `/`。`episode-id` 限制为 `[A-Za-z0-9_-]{1,200}`。函数删除 query 和 fragment，统一返回 `https://www.xiaoyuzhoufm.com/episode/<episode-id>`；不符合规则的值返回 `None`。小宇宙主页、短链、RSS、搜索页、非 HTTP(S) URL 都不进入播客管线，仍由现有 URL serializer 和普通流程处理。

`ArticleCreateSerializer.url` 和批量子 URL 的最大长度改为 2,048。`validate_url()` 先 normalise：普通 URL 保持当前 `Article.objects.filter(url=value).exists()` 的 400 “该文章已存在”语义；有效播客 URL 跳过原始 URL 查重，由 `PodcastSubmissionService` 用 canonical URL 判断历史 Article 和活跃任务。`ArticleViewSet.collect()` 在 serializer 成功后再次 normalise，普通 URL 调用原同步 service；播客 URL 要求 `request.user.is_authenticated`，未登录返回 401 且不写记录。此权限只保护会产生付费外部操作的新路径，不改变现有普通 URL 的匿名行为。`collect_view` 已要求登录，改为使用同一 JSON API；`collect_batch` 对每项复用相同分流，普通项维持原结果，播客项包含安全 task 数据或逐项 401/409。

`PodcastSubmissionService.submit(canonical_url, user)` 不访问网络、不启动子进程、不下载音频、不调用 ASR 或 AI。它在短 `transaction.atomic()` 中执行以下顺序：先以 normalizer 比较已有 `Article.url`，命中则按现有重复文章语义返回 400；随后查询 `task_type='podcast'`、`podcast_url_key=canonical_url`、`is_active=True` 的 URL 锁。相同 owner 或 staff 重提返回该 task 的 202；其他用户返回 409 的通用“该链接正在处理中”，不泄露任务 ID、状态或拥有者。无锁时创建 `pending/queued` `CollectionTask`、一对一 `PodcastEpisode` 和首个安全事件。条件唯一约束竞争失败时，在内层 savepoint 后重新读取胜出任务并按同样所有权规则响应。数据库异常仅记录受控错误代码，客户端收到无内部细节的 500。

播客 202 格式固定为 `success`、`task_id`、`task_url`、`status`、`stage`、`progress`、`progress_message`。它绝不包含 audio URL、ASR ID、脚本输出、provider response、临时路径或凭据。普通成功响应继续为当前 201 和 `ArticleSerializer` 数据。

## 持久化模型、状态机和不变量

新增 `articles/migrations/0007_podcast_collection.py`，依赖 `0006_weeklydigest_stat`。迁移只增加表、字段、索引和约束并作安全默认值回填，不删除或重写既有 Article、CollectionTask、周刊或订阅数据。`Article.url` 和 `CollectionTask.url` 变为 `max_length=2048`；`Article.PLATFORM_CHOICES` 与 `detect_platform()` 加 `xiaoyuzhou`。通用同步解析器不增加播客分支。

`CollectionTask` 仍是调度、进度、取消、租约和 URL 锁的唯一所有者。其 status 扩展为 `pending`、`processing`、`success`、`failed`、`rejected`、`cancelled`、`needs_attention`，兼容旧值。新增字段为：

| 组 | 字段和约束 |
|---|---|
| 类型与访问 | `task_type`（`article`/`podcast`，默认 `article`）、可空 `created_by` FK。仅 podcast task 写 owner。 |
| 展示与错误 | `stage`、`progress`（0–100）、最多 200 字的 `progress_message`、受控 `error_code`、`next_action`。 |
| 调度与租约 | `retry_count`、`work_attempt_number`、`next_attempt_at`、`next_poll_at`、`lease_owner`、`lease_expires_at`、`heartbeat_at`、`is_retryable`、`cancel_requested`、`is_active`。 |
| 播客摘要 | `podcast_url_key`、可空 `known_cost_amount` decimal、`known_cost_currency`、受控 `external_status`。 |

历史 tasks 回填 `task_type='article'`、`is_active=False`、`is_retryable=False`；旧 success 映射 `completed/100`，旧 failed 映射 `failed`，其他为 `not_applicable` stage。普通 service 明确写入这些默认值。新增 `(task_type, status, next_attempt_at)`、`(task_type, stage, next_poll_at)` 和 URL key 索引，并建立 SQLite 支持的条件唯一锁：

```python
models.UniqueConstraint(
    fields=['podcast_url_key'],
    condition=models.Q(task_type='podcast', is_active=True),
    name='one_active_podcast_task_per_url',
)
```

`success`、`rejected`、`cancelled` 和不可重试 `failed` 释放 URL 锁。可重试 `failed`、等待轮询和 **`needs_attention` 都保留锁**。`needs_attention` 的明确定义是“自动处理终态、人工可恢复状态”：worker 永不自动领取它；进入时清除 lease 并执行幂等临时文件清理；页面停止自动轮询；`is_active=True` 保留 URL 锁。除以下白名单 staff reconcile 转换外，所有终态均不可回退：`needs_attention -> pending/asr_poll`（已验证 ASR ID）、`needs_attention -> pending/analysis_chunks|analysis_aggregate`（确认 AI 未派发）、以及 `needs_attention -> failed`（放弃不确定提交）。普通 retry 和 cancel 都不能使它回退。

新增的关联模型及其持久化边界如下：

- `PodcastEpisode`：与 task 一对一；与最终 Article 为可空一对一且 `on_delete=SET_NULL`。保存 canonical URL、episode ID、标题、节目名、作者、可空 UTC 发布时间、说明、shownotes、时长、pay type、private 标志、清洗的 hotwords、语言、transcript checksum 和安全 ASR 摘要。`audio_url`、`audio_url_alt` 为 worker-only `TextField`，从 serializer、Admin、`__str__`、event、日志和异常中排除，并在每一种终态清空。
- `PodcastTaskEvent`：task FK、时间、level、受控 code、最大 500 字安全 message、可空 actor user FK。仅追加，按 `(created_at, id)` 查询。
- `PodcastAsrAttempt`：episode、attempt number、input mode、`not_started/submitting/submitted/uncertain`、私有 external task ID、外部状态、金额/币种和时间；`(episode, attempt_number)` 唯一。ID 永不在普通 API、event 或 list Admin 显示。
- `PodcastTranscriptSegment`：episode、sequence、可空 start/end 秒、speaker 和验证后的 text；`(episode, sequence)` 唯一。它是完整文字稿的恢复源；provider 原始 JSON 不落库。
- `PodcastAnalysisChunk`：episode、sequence、source 字符范围、完整 input、SHA-256、`pending/calling/succeeded/failed/uncertain`、summary、key points、受控 error code、`dispatch_started_at`、`attempt_number`、稳定 `request_fingerprint`、调用完成时间；`(episode, sequence)` 唯一。
- `PodcastAnalysisRollup`：episode、level、sequence、子项范围、input、checksum、相同的状态/派发审计字段和结果；`(episode, level, sequence)` 唯一。

`CollectionTask.article` 改为 nullable `SET_NULL`。Article 只在所有 transcript segments、所有 leaf chunks 和 root rollup 都成功后的最终短事务创建与关联。因此正常的活跃任务没有 Article。纵深保护下，`delete_article` 和 `batch_delete` 在删除前检查关联 `task_type='podcast', is_active=True` 的 task；单删返回 409，批量原子拒绝并返回受保护 ID，不做部分删除。终态 Article 删除只清空关联，保留任务、attempt、segments、chunks 和 events。所有阶段迁移和新增 event 在同一个短事务；外部网络、子进程、sleep 和 AI 调用永不持有该事务。

重要不变量由服务层短事务及 `task id + lease_owner` 条件更新执行：只有 lease owner 能推进普通阶段；只要已有 ASR ID 或 attempt 为 `submitting/uncertain` 就绝不能新建 ASR attempt；成功 chunk/rollup 从不再调用 AI；所有 leaf 与 rollup 成功前不得写 Article 或 task success；活跃 task 保有 URL 锁；从 `needs_attention` 的回退仅能由明确的 staff action；每种终态均可重复执行安全 cleanup。

## 元数据脚本适配和外部输入边界

新增受版本控制的 `articles/podcast_metadata_adapter.py`，不修改 `/root/.kiro` 技能文件。worker 通过绝对 interpreter 和参数数组调用：

```text
<PODCAST_PYTHON> <absolute adapter> --episode-url <canonical-url> --skill-script <absolute fetch_episode.py>
```

已检查的 `fetch_episode.py` 有可导入的 `parse(url)`，CLI 在缺 audio URL 时才 `SystemExit`。adapter 用 `importlib.util.spec_from_file_location()` 导入后调用 `parse()`，让系统在音频缺失时仍能先判定付费/私有。adapter stdout 只能输出一行紧凑 JSON，stderr 不输出诊断。成功和失败分别为：

```json
{"ok": true, "metadata": {"eid": "…", "pay_type": "FREE", "is_private": false}}
{"ok": false, "code": "metadata_network_timeout", "retryable": true}
```

adapter 将超时映射为 `metadata_network_timeout/true`，临时 `URLError`、429、5xx 为 `metadata_platform_temporary/true`，非临时访问错误和 `SystemExit` 为 `metadata_unavailable/false`，结构错误为 `metadata_invalid_response/false`。不得回显异常、响应正文、最终 URL、payload 或 secret。runner 仅接收受限大小的单行 object、正确类型和白名单 code；非零退出、额外行、坏 JSON 或未知 code 均为 `needs_attention/metadata_adapter_invalid`。

`PodcastMetadataService.normalize_and_validate(raw, expected_eid, require_audio=False)` 是唯一的 metadata 输入边界：要求 object、eid 一致、无控制字符的非空 title、string pay type 和严格 bool `is_private`。未知/缺失 pay type 永不视为 FREE。duration 必须为非 bool、有限、非负整数。标题超出 Article 限制、NUL/C0/DEL、eid 不符或结构错误为不可重试失败。description/shownotes 规范换行并去控制字符；hotwords 最多 40 个，每项最多 40 字的合法字符串。可选 `pub_date` 接受 ISO-8601（包括 Z）或非负 epoch，转 UTC `published_at` 和 Article 的 ISO 字符串 `publish_time`；缺失/无效仅加 warning event。

worker 在 `metadata` 阶段先以 `require_audio=False` 持久化安全 metadata，再进入 `access_check`。`pay_type != 'FREE'`、`is_private=True` 或明确限制标志同事务转 `rejected/is_retryable=False/is_active=False`，记录“该单集为付费或受限内容，未提交转写”。该路径不创建 ASR attempt、不下载、不调用 AI。仅在确认为 FREE 且非 private 后要求匿名 HTTP(S) audio URL；缺失是不可重试 `failed/audio_url_missing`。临时 adapter 失败按退避处理；确定性元数据失败不重试。

## Worker、租约、轮询、重试、取消和清理

新增 `articles/management/commands/process_podcast_tasks.py`。`--once` 只领取并推进一个持久化边界，适合测试和崩溃恢复；`--loop` 在无工作时每五秒查到期任务；`--worker-id` 指定稳定 owner；`--max-tasks` 限制单次处理量。systemd unit 只启动一个 `--loop` worker，不处理现有同步 article tasks。

SQLite 领取不依赖 `select_for_update()`。短事务查找 active podcast 候选：queued、到期自动 retry、`pending/asr_poll` 且 `next_poll_at <= now`、租约过期的 processing task，以及无有效 owner 的 cancel 请求。随后以 task ID、先前状态和 “lease 为空或已过期” 的 CAS `UPDATE` 写入 `processing`、owner、120 秒 lease、heartbeat；只影响一行时获得 ownership。接管过期 lease 时保留已存 ASR ID、attempt、segments、成功 AI results、重试计数和 stage。

接管时必须先处理不确定的已派发 AI：任一 `calling` chunk/rollup 的 `dispatch_started_at` 早于失效 lease，或 owner 在 HTTP timeout、进程被杀、lease refresh 失败后不能确认结果已持久化，均在 owner-guarded 短事务改为 `uncertain`，保留 input、checksum、fingerprint、attempt number 与 dispatch timestamp，task 转 `needs_attention`，清 lease 并写安全 event。它**绝不自动重发**，普通 retry 也不能清除它。原因是现有 DeepSeek API 路径没有可验证的 provider idempotency-key 契约；`request_fingerprint` 用于审计和人工核对，而非假设上游去重。

网络调用、子进程和 sleep 在事务外。长子进程期间每 20 秒 `refresh_lease()`；CAS 失败代表 lease 丢失，旧 worker 终止 child、丢弃未持久化输出并请求清理。阶段和 progress 固定为：queued 0、metadata 5、access_check 15、asr_submit 20、asr_poll 25–50、asr_result 55、transcript 60、analysis_prepare 65、analysis_chunks 65–90、analysis_aggregate 91–99、completed 100。分析进度由数据库内 succeeded/total chunks 与 rollups 计算。

ASR `status` 为 `pending`/`processing` 时，owner 短事务将同一 task 转为 `pending/asr_poll`，写 `next_poll_at=now + PODCAST_ASR_POLL_SECONDS`、清 lease/owner/heartbeat；仅外部 status 变化时追加 event。正常 polling 不增加 `retry_count`。status/result timeout、连接错误、5xx 或确定 429 保留同一 ASR ID，按 60、300、900 秒退避设置下一 poll 并增加 retry；第三次后为 `failed/is_retryable=True/is_active=True`，manual retry 只恢复 poll。metadata transient error 和**尚未派发**的明确 AI 429 也可使用这组退避。凭据缺失/无效、余额不足、provider 明确限额、永久 metadata/audio failure、无效 result 和 remote `failed/abandoned` 都不无限自动重试；明确远端失败为 `needs_attention`，防止自动产生新费用。

取消 API 不直接删除数据，只写 `cancel_requested=True`。没有有效 lease 时，CAS 直接进入 `cancelled`；有 owner 时返回 202，owner 在 heartbeat、子进程返回或下一持久边界优先完成取消。cancel 发生在已有 external ID 后，事件和 API 明确“本地处理已停止，远端任务可能已经产生费用”，不尝试远端取消。

**ASR 提交计费闸门**是唯一允许启动 `auralwise.py submit` 的入口。在启动子进程前，worker 用 `id + lease_owner + cancel_requested=False + no existing external ID + no submitting/uncertain attempt` 的短事务 CAS，将唯一 attempt 写成 `submitting` 并将 task 写到 `asr_submit`。若零行受影响，worker 不启动 child，按 cancellation 完成收敛。闸门提交后、`Popen` 之前再次读取 task 的 `cancel_requested`：若为真且 child 尚未 spawn，则 owner 转 `cancelled` 且零 submit；若为假才可 spawn。一旦闸门成功且 child 已启动，取消仍会停止后续本地处理但可能已有外部费用。提交 timeout、信号终止、零退出却没有可确认 ID、未知非零退出或 worker 在该持久化边界崩溃，都将 attempt 标为 `uncertain`、task 转 `needs_attention`，绝不自动 submit。

临时目录限定为 `<PODCAST_TEMP_ROOT>/<task-id>/attempt-<n>/`，权限 0700。任何候选路径先 `resolve()` 后以 `relative_to()` 验证仍在 task root 内。清理协议为 `terminate -> wait(5s) -> kill if necessary -> wait(5s) -> close pipes -> cleanup`；清理失败只记录 `temp_cleanup_failed`，不记录路径、URL 或 secret。本期不实现 `download_audio.py` 本地 fallback，因为 server-side audio URL 是首选且 requirements 并不要求 fallback；服务端拉取失败将进入安全错误分类或人工处理。故本设计没有持久音频、归档音频或本地上传路径。

## ASR 调用协议和不确定提交恢复

`PodcastAsrClient` 只通过受控 runner 调用绝对路径脚本。runner 在 parent process 检查 `AURALWISE_API_KEY` 非空；为空则不启动子进程，任务为 `failed/asr_credentials_missing`。child 使用新建的 0700 HOME 和白名单环境：`PATH`、`LANG=C.UTF-8`、`LC_ALL=C.UTF-8`、`PYTHONIOENCODING=utf-8`、`HOME`、`AURALWISE_API_KEY`。这样已检查的 `auralwise.py` 无法回退到 `~/.config/auralwise/api_key`。环境值永不写日志。

只允许以下参数数组：

```text
submit --audio-url <private-url> --lang zh --mode standard --hotwords <sanitized-values> --prompt <controlled-prompt>
status <external-task-id>
result <external-task-id> -o <attempt-dir>/provider-result.json
```

禁止 `run`、`--wait`、batch、callback、audio-events、`--file` 和 `download_audio.py`。已检查 `auralwise.py submit` 成功时打印单行人类输出，runner 只在 return code 0 且 stdout 完整匹配下列受限模式时提取 ID；其他 stdout/stderr 均丢弃：

```text
^✅ 任务已创建 [0-9]+s  id=([A-Za-z0-9_-]{1,128})  status=([A-Za-z0-9_-]{1,32})  size=(?:[0-9]+|None)\r?\n?$
```

提交成功在 owner-guarded 短事务写同一 attempt 的 external ID 和 `submitted`。非零 submit 时，只从受限 stderr 锚定提取 `^❌ HTTP (401|402|413|429)(?:\s|$)`：429 代表确定未被接受，可退避；401、402、413 分别是无效凭据、余额不足、provider 限额。其他 nonzero 全部是不确定提交。

`status` stdout 必须是单一 JSON object，id 与已存 ID 相同，status 在 `{pending, processing, done, failed, abandoned}`，billing 仅接受有限非负 decimal 和 3–8 位大写 currency。安全金额/币种/status 写入 attempt 和 task。畸形 JSON、ID/status 不符或非法 billing 转 `needs_attention/asr_status_invalid`。`done` 才运行 result；`failed`/`abandoned` 转 `needs_attention`。`result` 只读取固定临时文件；必须有非空 segments list，每段 text 非空，speaker 可选，start/end 是非 bool 的有限非负数字且 end 不小于 start。验证后按 sequence 写 segments、更新计费和状态并删除 provider JSON。空或畸形结果转 `needs_attention/asr_result_invalid`。

不确定、没有 external ID 的 submit 仅允许 staff 的 `POST /api/tasks/{id}/reconcile/`：

```json
{"action":"attach_verified_asr", "external_task_id":"<id>"}
{"action":"abandon_uncertain_submission"}
```

`attach_verified_asr` 仅允许 `needs_attention`、同一 attempt 为 `uncertain` 且 ID 为空。ID 校验 `[A-Za-z0-9_-]{1,128}`，服务在事务外做非计费 `status <candidate-id>` 验证，随后在短事务重新 CAS 确认原状态并写入**同一 attempt**，转 `pending/asr_poll`、`next_poll_at=now`，写 actor 审计 event。不调用 submit、不建新 attempt。验证失败不改变 DB。`abandon_uncertain_submission` 对相同前置条件，将 task 转 `failed/is_retryable=False/is_active=False`，记录“已停止本地处理，外部提交结果仍可能存在，请人工核实费用”，并清理。普通 retry 永远不能处理 `needs_attention`。

## 文字稿、全量分析、AI 不确定调用和 Article 完成

`PodcastTranscriptFormatter` 从已验证 segments 确定性生成完整 Markdown，不调用 `render_transcript.py` 或输出文件。它输出节目元信息和每段 `[HH:MM:SS] speaker：text`，未知身份仅保留 provider speaker label，不推断真实姓名。segments 持久化后，即使后续 AI 失败，文字稿仍可恢复且完整保留。

播客不能调用截断的 `DeepSeekAIService.analyze_article()` 或会记录 provider body 的 `generate()`。`articles/ai_service.py` 新增 `PodcastAnalysisClient.generate_or_raise(kind, title, text)`，复用现有 Requests/OpenAI-compatible DeepSeek endpoint、模型和 credentials，但走独立的安全错误路径。它要求功能启用、凭据存在、合法 kind、非空 title/text，单次 input 不超过 2,800 字。受控 prompt 要求 JSON `{"summary":"...","key_points":[...]}`；只接受非空 summary（最多 500 字）和 2–5 条、每条最多 80 字的 key points。日志不得含 Authorization、prompt、全文、URL 或 provider body。HTTP 400/401/403 是配置失败；在 request 尚未发出前发现的 429 可退避；HTTP request 已进入网络后的 timeout、断线、5xx、进程中断、lease 丢失和无法验证的成功 body均为不确定调用，不能自动重发。

`PodcastAnalysisService` 从所有 persisted segments 以 sequence 构建唯一 `analysis_source`，确保每个 segment text 只出现一次。它以约 2,400 字、绝不超过 2,800 字形成 leaf，优先在段落、speaker/timestamp 和句末拆分；超长段依次按句末、空白、最后字符边界拆分。无全文长度、段数、chunk 数或 rollup 层数的业务上限。创建后必须验证 source offsets 串接严格等于 `analysis_source`，无空块、重复、交叠或缺口；失败是内部永久错误且零 AI 调用。

每个 leaf/rollup 都有相同、可审计的派发状态机。owner 在调用前用 `task id + lease_owner + item.status=pending` CAS：写 `calling`、`dispatch_started_at`、递增 `attempt_number`、将稳定 `request_fingerprint=SHA256(kind + input checksum + model configuration)` 固化，然后才发 HTTP 请求。成功结果由同一 owner CAS 写 `succeeded` 和 result。收到 provider 响应后、写库前 lease 被夺走或进程崩溃，新的 worker 不把 item 重新 pending，而依上节改为 `uncertain`/`needs_attention`。已成功 item 永远跳过。任何 `failed` 或 `uncertain` item 都阻止父级和 Article completion。

由于当前 provider integration 没有经验证的 idempotency-key，只有 staff 能确认未派发的 AI item：

```json
{"action":"confirm_ai_not_dispatched", "item_type":"chunk", "sequence":12}
{"action":"confirm_ai_not_dispatched", "item_type":"rollup", "level":2, "sequence":0}
```

请求 body 不允许额外字段。仅 task owner 的 staff 可调用，且 task 必须为 `needs_attention`、无有效 lease、目标 item 必须为 `uncertain`。chunk 需 `sequence` 为非负整数且不得给 `level`；rollup 需 `level` 和 `sequence` 都为非负整数。短事务以 item 的状态、task 状态和无 lease 为 CAS 前置条件，把**仅该 item**转回 `pending`，清空显示 error/completed time，但保留 input、checksum、dispatch timestamp、attempt number 和 fingerprint；task 转 `pending` 到正确的 `analysis_chunks` 或 `analysis_aggregate` 阶段，并追加含 actor 的审计 event，明确该操作代表管理员已人工确认上次请求未被 provider 接受。重复 action、非 staff、item 不存在、成功/failed/calling item、有效 lease 或 task 非 `needs_attention` 都返回 409/404 且不改变任何记录。随后 worker 仅会对已被确认的 item 再发起一次调用。若今后 provider 明确支持 idempotency key，可在保持 schema 和测试的前提下将已持久化 fingerprint 传入；本期不假设其存在。

所有 leaf 成功后，服务用它们的 summary/key points 创建 rollups，继续按同一 2,800 字限制递归聚合直到唯一 root。每层 input 由所有成功 child 的 sequence、范围和 checksum 组成，确保 root 覆盖全稿而非仅开头。只有 root、全部 leaf 和全部 rollup 成功，一个短事务 `get_or_create` canonical Article，写 `platform='xiaoyuzhou'`、标题、作者、publish time、**完整** transcript `content`、root `ai_summary` 和 `ai_key_point`，关联 Episode/task、写 success/completed/100 event、释放 URL 锁。若同 URL Article 并发存在，只有 content checksum 一致才能关联；不一致转 `needs_attention`，绝不覆盖。

## API、前端、Admin 和运维

`CollectionTaskViewSet` 保留普通 article tasks 的当前 list/detail 读取行为。对 podcast task，staff 可看全部，普通已登录用户仅能看 `created_by=request.user`，匿名用户不可见，非 owner 返回 404。新增 podcast task serializer 返回 ID、canonical page URL、status/stage/progress/message、leaf/rollup completed/total、最新最多 50 条安全 events、error/next action、`retry_allowed`、`cancel_allowed`、关联 Article `{id,title,url}` 和 `{status,cost_amount,currency}`。不返回 audio URL、ASR ID、provider result、临时路径、headers、key 或 stderr。

新增 `GET /api/tasks/{id}/events/`（分页）、`POST /api/tasks/{id}/retry/`、`POST /api/tasks/{id}/cancel/` 和 staff-only `POST /api/tasks/{id}/reconcile/`。retry body 为空，只允许 owner/staff 对 `failed && is_retryable && is_active && !cancel_requested` 使用。它永不清除 submitted ASR ID、attempt 或成功 AI record：已有 ID 回到 `asr_poll`，无 ID 回到 metadata，已有 transcript 的失败回到第一个未成功 analysis item。非法状态返回 409。reconcile 的 schema 只接受 `attach_verified_asr`、`abandon_uncertain_submission` 和以上严格的 `confirm_ai_not_dispatched`；所有动作均写 actor 审计 event，不得建立新 ASR attempt。cancel 对 `needs_attention` 返回 409，并指导 staff 使用适当 reconcile；重复终态 cancel 返回 409。

`templates/articles/collect.html` 的单篇 form 改为带 CSRF token 的 JSON `fetch`。201 显示原普通成功体验，202 创建播客进度卡；批量脚本同样识别 202。每张卡默认每五秒轮询 `task_url`；网络错误依 5/10/20/30 秒退避，成功后回到五秒，在 `success`、`failed`、`rejected`、`cancelled`、`needs_attention` 或 `pagehide` 时清 timer。卡显示状态、stage、overall progress、chunk/rollup progress、最新安全 event、已知费用、actionable error、Article link，并仅由 API allow flags 显示 retry/cancel。动态服务端值一律以 `document.createElement()`、属性 API 和 `textContent` 写入，同时替换当前批量结果和 toast 对服务端值的 `innerHTML` 拼接。`static/css/style.css` 只增加局部 podcast card 与 `xiaoyuzhou` badge。

`articles/admin.py` 注册 Episode、Attempt、Segment、Chunk、Rollup、Event。CollectionTask admin 增加类型、stage、progress、retry、费用和 readonly Article 信息及 event inline。Episode、segment、chunk、rollup、attempt 都是 readonly 排障视图；列表、字段、`__str__` 和 inlines 排除 audio URL、ASR ID、临时路径、provider payload、headers 和 credentials。lease/state 不能直接编辑；staff admin action 调用相同 reconcile validation 并写 actor event。

`settings.py` 与 `settings_production.py` 新增可 `override_settings` 的无秘密配置：metadata/ASR script 绝对路径、Python interpreter、temporary root、child PATH、lease/heartbeat/poll/idle/backoff 和 AI input max。开发默认可以指向已安装 skill 的绝对路径；生产不能使 `nginx` 读取 `/root`。运维文档必须要求管理员将经审核、同版本的 scripts 放到 worker 可读且受控的绝对路径后覆盖 settings，不放宽 `/root` 权限，也不以 root 跑 worker。

新增 `podcast-collection-worker.service` 与 `PODCAST_WORKER.md`。unit 使用项目绝对路径、`nginx`、`settings_production`、`PYTHONPATH`，仅运行一个 `process_podcast_tasks --loop`，并设置 `Restart=on-failure`、`NoNewPrivileges=true`、`PrivateTmp=true`、`ProtectSystem=strict` 和只包含数据库、logs、cache、temporary root 的 `ReadWritePaths`。unit 不含 secret。文档说明环境变量名称（不含值）、脚本路径、SQLite 单 worker 限制、迁移、安装/启动/停止/日志、lease 恢复、取消、staff reconcile、不确定 ASR/AI 的人工步骤和临时目录清理。实现不执行 daemon-reload、enable、start、stop、restart 或任何部署。

## 具体文件变更

- `articles/models.py`：平台、CollectionTask 播客/lease/poll/owner 字段，`SET_NULL` Article FK 和 podcast models。
- `articles/migrations/0007_podcast_collection.py`：SQLite-compatible schema、历史回填、索引、条件唯一约束和 FK 删除策略。
- `articles/podcast.py`：normalizer、submission、metadata validation、event/state/lease、ASR protocol、formatter、analysis、cleanup 和 staff reconcile validation。
- `articles/podcast_metadata_adapter.py`：单行安全 JSON metadata adapter。
- `articles/management/commands/process_podcast_tasks.py`：DB-backed worker。
- `articles/services.py`：仅处理 batch/HTML routing glue 和普通 task defaults，不重构同步收藏。
- `articles/serializers.py`、`articles/views.py`、`articles/urls.py`：202 分流、任务 visibility、events/retry/cancel/reconcile、active podcast Article deletion 409。
- `articles/ai_service.py`：安全的 chunk/rollup client，普通文章路径不变。
- `articles/admin.py`：脱敏 readonly admin、inlines 和受控 reconcile actions。
- `article_collection_django/settings.py`、`article_collection_django/settings_production.py`：无秘密 worker configuration。
- `templates/articles/collect.html`、`static/css/style.css`：polling card、安全 DOM rendering 和局部样式。
- `podcast-collection-worker.service`、`PODCAST_WORKER.md`：未部署的 worker template 与 runbook。
- `articles/test_podcast_collection.py`：隔离的聚焦测试。

## 测试和验证计划

所有网络、adapter、subprocess、ASR、AI、时钟均 mock；测试使用临时 `PODCAST_TEMP_ROOT` 和 `override_settings`，不读取凭据、不联网、不下载真实音频、不运行 systemd。服务/API/serializer 用 `TestCase`，跨连接 lease/CAS 用 `TransactionTestCase`。

1. normalizer 覆盖 canonicalization、query/fragment、HTTP/无 www 历史形式、host/episode ID 边界、credentials/port、主页/短链/搜索页和普通 URL。
2. API 覆盖认证播客提交只创建 task/Episode/event 并返回 202，所有外部 mock 零调用；匿名播客 401；普通 URL 成功、失败、重复仍保持既有响应。
3. 去重覆盖历史 Article、相同 owner active task、他人 409、条件唯一竞争及不会创建第二个 submit-capable task。
4. metadata fixtures 覆盖 FREE、非 FREE、private、无 audio URL、eid mismatch、控制符、日期和 transient failure；paid/private 断言 ASR、下载、AI 都零调用。
5. adapter/runner 覆盖 timeout、`URLError`、`SystemExit`、bad JSON、多行、unknown code、非零退出，断言 URL、exception、payload 与 secret 不进入 event/API/log mock。
6. migration 从 `0006` 的 success/failed/processing/pending task 升级，验证 default mapping、索引/constraint 和两个 Article relation 的 `SET_NULL`。
7. lease 覆盖同一有效 lease 只能一个 worker 领取、过期 processing 可接管、正常 pending `asr_poll` 到期前不可领取、到期后无需等 lease 超时即可轮询、lease loss 终止 child、cancel 优先于下一 poll。
8. ASR 覆盖绝对 Python subprocess 的 submit/status/result parser、ID/计费持久化、401/402/413/429、坏 stdout/JSON、timeout/signal；uncertain submit 永不自动 submit，retry 不产生新 attempt。
9. 在 metadata 完成与 spawn 之间注入 cancel，断言 submit 调用为零；在计费闸门后再 cancel，断言不开始后续本地流程且安全地显示潜在费用风险。
10. staff ASR reconcile 覆盖 owner/nonstaff 拒绝、`attach_verified_asr` 的先 status 验证和同 attempt 恢复、失败不改 DB、`abandon_uncertain_submission` 安全关闭，均零新 submit/new attempt。
11. cleanup 覆盖 success、failed、rejected、cancelled、needs_attention 和 lease loss，断言无敏感 path/URL event；本设计不允许 fallback 调用下载脚本。
12. 删除覆盖 active task 的单删/批删 409，task/attempt/segment/chunk/event/URL lock 留存，重提不会再次 submit；终态 Article 删除只清关联。
13. 使用超过 3,000 字、带 speaker/timestamp 且需要多层 rollup 的 segments，验证完整 Article.content、平台筛选与搜索、每个 source character 恰一次进入 leaf、全部 chunks/rollups 各只调用一次、全成功前不创建 Article。
14. 模拟 AI request 已到达 provider 而 worker 在写结果前崩溃或 lease 失效，断言 stale `calling` 变 `uncertain/needs_attention` 且自动恢复不会第二次调用。分别覆盖 chunk/rollup 的 staff `confirm_ai_not_dispatched` schema、CAS、审计、单 item reset 与随后成功；非法/重复 action 不改变数据。
15. 覆盖 AI 未配置、未派发 429、请求后 timeout、bad JSON、chunk/final rollup failure，验证文字稿与进度保留、无伪 Article/summary，且只在准许的 retry 或 reconcile 后恢复。
16. API/template 覆盖 event `(created_at,id)` ordering、task owner/staff visibility、retry/cancel constraints、Article link、`needs_attention` 停止 polling 和 `createElement`/`textContent` 安全 rendering。
17. 实施后运行 `python3 manage.py makemigrations --check --dry-run`、`python3 manage.py migrate --plan`、`python3 manage.py check`、`python3 manage.py test articles.test_podcast_collection` 及适用既有 tests。所有 ASR/AI/subprocess/network calls 必须 mock。

## Out of scope

不下载、转写或分析真实播客；不读取、显示或查询 API key/余额；不自动充值；不收藏节目主页、RSS、短链、付费/私有内容；不持久保存原始音频、字幕、provider JSON 或文字稿文件；不实现本地音频 fallback；不做人工校对、说话人身份推断、Celery/Redis、多 worker 分布式调度、SSE/WebSocket；不重构周刊、订阅、认证、整体前端或实际部署/重启 systemd。

## Design review responses

1. **Finding 1（HIGH，已处理）：AI 派发后、结果持久化前的崩溃恢复已被明确为不确定计费边界。** Chunk/Rollup 现持久化 `dispatch_started_at`、`attempt_number` 和稳定 `request_fingerprint`；过期 lease、HTTP 后 timeout、进程中断或 lease 丢失会把 stale `calling` 转为 `uncertain` 并把 task 转 `needs_attention`，永不自动重发。设计定义了 staff-only `confirm_ai_not_dispatched` 的精确 JSON schema、item type/sequence 前置条件、CAS、审计、字段保留和 pending 重置规则。新增 crash-before-persist 测试确保不会产生二次 AI 调用。
2. **Finding 2（MEDIUM，已处理）：`needs_attention` 的状态语义现已统一。** 它是自动处理终态、人工可恢复状态，不被 worker 领取、无 lease、保留 `is_active` URL 锁、进入时执行幂等 cleanup，UI 停止自动轮询。只有列出的 staff reconcile 白名单能使其恢复，其他终态不回退。测试覆盖恢复、关闭、重复 reconcile 和重复 cleanup。
3. **Finding 3（MEDIUM，已处理）：ASR submit 前增加了 owner-guarded 取消计费闸门。** `cancel_requested=False` 是把 attempt 写为 `submitting` 的原子前提；零行更新则不 spawn。spawn 前再读 cancel flag，闸门前取消保证零 submit；闸门后取消则停止本地后续处理并明确可能已发生外部费用。测试覆盖两个竞态窗口。
