# 设计评审：小宇宙播客收藏技术设计（第二次修订）

## Verdict：CHANGES_REQUESTED

本轮有 4 个 MEDIUM finding。按机械规则，存在 HIGH 或 MEDIUM finding 时结论为 `CHANGES_REQUESTED`。

## 上轮 finding 复核

1. **Closed（上轮 HIGH，AI 调用已派发但结果未持久化时的恢复契约缺失）。** 修订设计已为 chunk 和 rollup 持久化 `dispatch_started_at`、`attempt_number` 与 `request_fingerprint`。租约接管会将 stale `calling` 转为 `uncertain` 和任务 `needs_attention`，禁止自动重发；`confirm_ai_not_dispatched` 也已定义 JSON schema、目标类型、CAS 前置条件、审计事件和仅重置一个 item 的规则。该规则避免了 provider 尚无已验证幂等契约时的重复 AI 调用。
2. **Closed（上轮 MEDIUM，`needs_attention` 的终态和可恢复语义冲突）。** 修订设计统一将它定义为“自动处理终态、人工可恢复状态”：worker 不自动领取，进入时清 lease 并执行幂等清理，保留 `is_active=True` 的 URL 锁，页面停止轮询；仅列出的 staff reconcile 白名单能让它回到可处理阶段。取消、普通 retry 和状态转换限制也已随之明确。
3. **Closed（上轮 MEDIUM，取消与 ASR submit 之间缺少计费闸门）。** 修订设计在 spawn 前加入 `task id + lease_owner + cancel_requested=False` 的 owner-guarded CAS，并在 `Popen` 前再次读取取消标志。闸门前取消不启动 submit；闸门之后的取消停止本地处理并明确可能产生外部费用。测试计划覆盖了两个竞态窗口。

## Findings

1. **MEDIUM — 安全重试的 ASR submit 429 没有可执行的 attempt 状态转换，下一次领取会被设计自己的计费闸门永久阻止。**  
   **位置：** “Worker、租约、轮询、重试、取消和清理”的 ASR retry 段落，以及“ASR 调用协议和不确定提交恢复”的计费闸门和 `PodcastAsrAttempt` 状态。  
   **问题：** 计费闸门先把唯一的 `PodcastAsrAttempt` 写为 `submitting`，且仅当“没有 `submitting/uncertain` attempt”才允许再次启动 `submit`。设计随后把 submit 的 HTTP 429 定义为“确定未被接受、可退避”，但没有规定将该同一 attempt 从 `submitting` 变为 `not_started`、设置 `next_attempt_at`，或如何记录本次已发出的调用次数。因此重试后的 worker 会看到仍是 `submitting` 的 attempt 并被闸门拒绝；若实现者自行创建新 attempt，又会偏离“已有 submitting attempt 时不得新建 attempt”的不变量。  
   **具体修复：** 明确 429 的唯一状态转换，并坚持复用同一 attempt。例如：
   ```text
   submit 返回已确认未接受的 429：
   owner-guarded transaction (task.id, lease_owner, attempt.status='submitting')：
     attempt.status = 'not_started'       # 同一 attempt，不创建新行
     task.status = 'pending'
     task.stage = 'asr_submit'
     task.retry_count += 1
     task.next_attempt_at = now + backoff(retry_count)
     清 lease，写 asr_submit_rate_limited 事件。
   ```
   同时规定最大自动次数后的 `failed/is_retryable=True` 行为，以及 `work_attempt_number` 是每次实际 spawn 递增、而不是新建 `PodcastAsrAttempt` 的条件。为 429 后的重新领取和第二次 submit 增加测试，并断言 timeout、未知非零退出仍只能进入 `uncertain`，绝不走这条重试路径。

2. **MEDIUM — 新增“播客必须登录”的访问控制改变了未要求的 API 提交语义，且不满足未附带认证前提的 202 提交要求。**  
   **位置：** “提交分流、URL 验证和访问控制”中 `collect()` 对有效播客 URL 要求 `request.user.is_authenticated` 的规则。  
   **问题：** 需求要求既有 `POST /api/articles/collect/` 检测合法单集后持久化并返回 202，验收标准也只要求该 POST 返回 202，并未把登录作为前提。当前源码中的 `ArticleViewSet` 没有 permission class，普通 API 收藏可匿名调用；只有 HTML `collect_view` 使用 `@login_required`。设计新增 401 会使匿名 API 调用的合法播客链接不能进入异步流程，属于未获要求的功能收缩。以付费调用为理由新增身份要求也没有在需求中得到确认。
   
   **具体修复：** 删除播客分流的强制登录条件，保持 API 提交兼容。若必须限制任务详情、取消和重试，应把它设计成不改变提交能力的显式 capability：创建时生成高熵随机 token，只保存其哈希；202 的 `task_url` 携带该 token，detail/events/retry/cancel 以 token 或已登录 owner/staff 授权。另一种可接受的选择是修改需求，明确“播客提交仅限已登录用户”，并相应更新验收标准；在需求未变更前不能默认返回 401。

3. **MEDIUM — 规范化去重没有定义如何发现历史 `Article` 的非 canonical 小宇宙 URL，不能保证“同一规范化 URL”的既有文章语义。**  
   **位置：** “提交分流、URL 验证和访问控制”中“以 normalizer 比较已有 `Article.url`”及 `PodcastSubmissionService.submit()` 的历史 Article 查重。  
   **问题：** 当前 `Article.url` 只保存原始 URL，当前 `ArticleCreateSerializer` 也按原始字符串 `Article.objects.filter(url=value)` 查重。设计会把 `http`、无 `www`、query 或 fragment 的单集提交规范化为 `https://www.xiaoyuzhoufm.com/episode/<id>`，但没有 `Article.canonical_url` 字段、历史回填方案或明确查询算法。“用 normalizer 比较”不能直接成为数据库查询：只按 canonical 值 filter 会漏掉已存在的旧形式，扫描全表又没有定义范围、并发处理或性能边界。漏检会在最终创建时造成重复语义或把任务推进到 ASR 后才发现 Article 已存在。
   
   **具体修复：** 为历史 Article 的判定定义一个确定流程，并在创建任务前完成。例如，增加可空且带索引的 `Article.podcast_url_key`，迁移中仅对可规范化的小宇宙 `Article.url` 回填 key；`PodcastSubmissionService` 在同一事务中通过 `podcast_url_key=canonical_url` 检查。不能修改既有 Article 的情况下，明确使用受限候选查询（小宇宙 episode URL）并逐项 normalise，再在最终建 Article 前以 canonical URL 和内容 checksum 再作一次原子检查。两种方案都必须测试 HTTP、无 `www`、query/fragment 的历史 Article 不会创建任务或触发 ASR。

4. **MEDIUM — AI 的“请求尚未派发”失败没有完整的任务/item 状态与恢复矩阵，无法落实用户可重试的失败路径。**  
   **位置：** “文字稿、全量分析、AI 不确定调用和 Article 完成”中 `PodcastAnalysisClient.generate_or_raise()` 的配置和错误分类，以及 API `retry/` 的恢复规则。  
   **问题：** 设计正确地把 HTTP 已进网络后的 timeout、5xx、进程中断等归为 `uncertain/needs_attention`，避免重复收费。但对请求尚未派发的失败没有指定可实现的后果：例如 AI 功能关闭、凭据缺失、输入前置校验失败，及被明确认定为未派发的 429。文本只称 400/401/403 为“配置失败”，而 `retry/` 只接受 `failed && is_retryable`，也没有定义如何把 target chunk/rollup 从 `failed` 重置为 `pending`、哪些错误 `is_retryable`、或 `next_action` 应给出什么操作。实现可能把缺凭据误标为永久失败而没有重试入口，或把失败 item 留在 `failed` 使 retry 后仍不能派发，均不满足“保留文字稿并提供可恢复失败路径”。
   
   **具体修复：** 增加 item error 到 task/API 状态的明确矩阵。例如：
   ```text
   未发送请求：AI disabled / missing credential / invalid local configuration
     item=failed, task=failed, is_retryable=true,
     next_action='配置 AI 后重试'; retry 将该失败 item 改为 pending。
   明确未被 provider 接受的 pre-dispatch 限流
     item=pending, task=pending, next_attempt_at=backoff；到期后自动调用。
   请求可能已到达 provider：timeout / 5xx / lease loss / 无法验证响应
     item=uncertain, task=needs_attention；仅 staff reconcile 能重派。
   ```
   为 leaf 和 rollup 分别测试凭据缺失、配置修复后的 retry、以及明确未派发限流；断言只恢复失败/待处理 item，成功 item 不再调用，且不确定 item 不能由普通 retry 重发。

## Verified Assumptions

- 当前 `ArticleCollectionService.collect_article()` 在请求内创建 `CollectionTask(status='processing')`，同步用 Requests/BeautifulSoup 解析，并在有内容且 AI 可用时调用 AI，最后创建 Article。播客必须在调用它之前分流，才能满足无外部调用的 202 提交。
- 当前 `DeepSeekAIService.analyze_article()` 明确截断前 3,000 个字符。其 `generate()` 在非 200 时记录响应 body、在空 choices 时记录解析数据；播客使用独立、脱敏的分块 AI client 是必要且可行的。
- 当前 `Article.url` 和 `CollectionTask.url` 都是默认 `URLField(max_length=200)`；`Article` 尚没有 `xiaoyuzhou` 平台；`CollectionTask` 只有 `pending`、`processing`、`success`、`failed` 状态，且 `article` 使用 `on_delete=models.CASCADE`。设计提出迁移扩展模型和将关联改为 `SET_NULL` 有源码依据。
- 当前迁移链终点是 `articles.0006_weeklydigest_stat`，因此新迁移依赖 `0006_weeklydigest_stat` 正确。
- 当前 `ArticleCreateSerializer.validate_url()` 仅按原始 `url` 查重，`ArticleViewSet.collect()` 在 serializer 验证后直接调用同步 service。有效播客 URL 必须先走专用 canonical 去重，普通 URL 可维持既有 400 查重语义。
- 当前 `CollectionTaskViewSet` 是无权限过滤的 `ReadOnlyModelViewSet`，当前路由存在 `/api/articles/` 和 `/api/tasks/`。为 podcast task 在 `get_queryset()` 和 action 中新增 owner/staff 或 capability 访问控制，不会要求改动普通 task 的读取行为。
- 当前 `collect.html` 单篇收藏是普通 HTML POST；批量区逐项 `fetch('/api/articles/collect/')`，并把 URL 和服务端 message 拼到 `innerHTML`。使用 JSON fetch 区分 201/202、轮询卡片和对动态值使用 `textContent` 都有明确的实现位置。
- 已安装的 `fetch_episode.py` 确实提供可导入的 `parse(url)`。`parse()` 在音频 URL 缺失时仍会返回 metadata；只有 CLI `main()` 会因 `audio_url` 缺失而 `SystemExit`。由 adapter 在子进程中导入 `parse()` 以先拒绝付费/私有内容具有技术可行性。
- 已安装的 `auralwise.py` 支持独立 `submit`、`status`、`result` 子命令，也支持设计禁止的 `run` 和 `submit --wait`。它优先读取 `AURALWISE_API_KEY`，其次读取 HOME 下的配置文件；受控空 HOME 和白名单子进程环境确实能阻止后者回退。
- `auralwise.py submit` 成功的输出格式与设计的受限 regex 相符；`status` 将 provider 响应用 `json.dumps(..., indent=2)` 输出为一个 JSON object（可含格式化换行），`result -o` 将 provider JSON 写入指定文件。因此 status parser 应接受受限大小的一个 JSON 值及 JSON whitespace，而不能把格式化换行当作多响应。
- 当前 `umeikouagent.service` 使用 `nginx` 用户、production settings 和项目绝对路径；`/root/.kiro` 所在目录不可供该用户读取。将审核后的 skill scripts 复制到 worker 可读的受控绝对路径，而非放宽 `/root` 权限，符合现有部署边界。

## Unverified/Wrong Assumptions

- **Wrong/Incomplete：** submit 429 已确认未被接受时，只要安排退避就能安全重试。当前状态机仍保留 `submitting` attempt，而计费闸门禁止该状态下再次 submit，见 finding 1。
- **Wrong（相对于已给需求）：** 合法播客 API 提交可以额外要求用户已登录。现有 API 收藏匿名可用，需求和验收标准没有加入认证前提，见 finding 2。
- **Unverified/Incomplete：** “以 normalizer 比较已有 Article.url”能在不增加 canonical 持久化或查询算法的情况下发现所有历史 URL 形式，见 finding 3。
- **Unverified/Incomplete：** AI 未派发的配置、凭据和限流失败会自然获得可用的 retry 路径。设计没有给出 item 状态、task 状态、`is_retryable` 和 retry reset 的完整契约，见 finding 4。
- **Unverified：** AuralWise 上游实际的 status/result payload 恒含设计所接受的 ID、状态、billing 和 segments 字段。已安装 CLI 基本透传上游响应；设计的严格运行时验证可防御坏数据，但不构成对上游 schema 的验证。
- **Unverified：** DeepSeek provider 支持可用的 idempotency key。当前源码没有传递该类 header；修订设计不假定此能力并在请求不确定时要求 staff reconcile，这一保守策略是合理的。
