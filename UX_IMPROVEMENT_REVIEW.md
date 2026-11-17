# 用户体验升级评估

> 评估时间:2026-05-24
> 评估范围:`article_collection_django` 站点(导航、首页、文章库、收藏页、阅读分享、订阅/退订、视图后端)
> 排序原则:**用户体验影响 × 修复难度**

---

## 高优先级(影响明显、改造可控)

### 1. 文章库分页其实没生效 [bug]

`articles/views.py:205-223` 的 `article_list` 直接把 `QuerySet` 传给模板,但模板里却调用 `articles.has_other_pages / has_previous / has_next / number`(`templates/articles/list.html:132-156`)——这些只在 Django `Paginator.page` 对象上才有。

**后果:** 订阅多了之后,所有文章一次性渲染,首屏会越来越慢,而且分页栏永远不显示。

**修复:** view 里用 `Paginator(articles, 20).get_page(request.GET.get('page'))` 包一层。

---

### 2. 品牌名混乱

同一个站点出现三套名字,新访客难以建立认知:

| 位置 | 名字 |
|---|---|
| 导航栏 (`base.html:24`) | Umeikou 的阅读分享 |
| 页脚 (`base.html:180`) | Reader - 智能文章收藏系统 |
| 邮件签名(memory 规则) | 于明浩的阅读列表 |
| HTML title 默认值 | Umeikou 的阅读分享 |

**建议:** 统一为「于明浩的阅读列表」(与邮件一致),页脚去掉 "Reader" 标语。

---

### 3. 退订链接把邮箱明文写在 URL 里

`articles/urls.py:30`:

```python
path('unsubscribe/<str:email>/', views.unsubscribe_view, name='unsubscribe'),
```

邮箱出现在浏览器历史、CDN 日志、Referer 头里,有隐私和滥用风险(他人构造 URL 即可触发退订意图)。

**修复:** 改为签名 token(`django.core.signing.TimestampSigner`)、一次性、带过期。

---

### 4. 移动端布局:订阅卡片永远占满半屏

`base.html` 用 `col-lg-8 / col-lg-4` 写死,所有页面都带右侧"个人名片 + 订阅卡片"。结果:

- 在文章列表页内容被压缩到 8/12 宽度;
- 在窄屏 (`<992px`) 卡片跟着内容垂直堆叠,首屏几乎看不到文章,只看到订阅表单;
- "收藏文章""阅读合集详情"这类页面侧边栏存在意义不大,但仍占空间。

**建议:** 侧边栏只在首页 + 阅读分享列表展示,或在列表/详情页折叠为顶部一行紧凑信息条。

---

### 5. 订阅成功之后毫无反馈深度

当前流程是"提交 → 5 秒后消失的小字提示"(`base.html:229`)。问题:

- 用户不知道是否真的发了欢迎邮件;
- 没有"请前往邮箱确认"的明确指引;
- 没有"已订阅过"的友好提示(对方又要填一遍才知道);
- 没有 double opt-in → 任何人都能用别人的邮箱订阅,留下骚扰风险。

**升级方向:** 成功后跳独立页面/模态框,列出"接下来会收到什么、退订路径";加 double opt-in 流程。

---

## 中优先级

### 6. 搜索与筛选太单薄

`templates/articles/list.html` 只支持"关键词 + 平台"二维,且:

- 没有"清除搜索"按钮;
- 没有搜索结果数量提示("找到 N 篇");
- 没有时间范围、作者、是否有 AI 摘要、是否已纳入 weekly digest 等维度;
- 实时搜索代码留了空壳 (`list.html:330-340` 的 `setTimeout` 里没有逻辑);
- 没有排序选项(默认按 `collected_at desc`)。

---

### 7. 文章卡片缺少"阅读态"

当前 `Article` 模型(`articles/models.py`)只有原始元数据。用户没法标记:

- 已读 / 未读 / 稍后读
- 收藏(星标)
- 标签 / 分类
- 个人笔记

对于一个"阅读列表"网站,缺这些就只是个 URL 仓库。

---

### 8. 阅读分享 (weekly) 没有"分享"能力

名字叫"阅读分享",但 `templates/articles/weekly_list.html` 既没有分享按钮(微信/X/复制链接)、也没有 RSS、也没有按月份归档导航。

同时该页面用了 emoji `📚`(`weekly_list.html:11`),和"邮件无 emoji 极简"规则的视觉风格不一致——网站和邮件应保持同一审美。

---

### 9. 批量收藏 form 有 Enter 键回退陷阱

`templates/articles/collect.html:91`:

```html
<form method="post" action="#" id="batchForm">
```

提交按钮是 `type="button"`,但 textarea 里如果用户按 Tab 后误按 Enter,浏览器默认会 submit 表单,跳转到 `#` 并丢失输入。

**修复:** 改成 `<div>`,或在 form 上 `onsubmit="return false"`。

---

### 10. 删除是硬删除 + 立刻刷新

`templates/articles/list.html:244-257` 的 `confirmDelete` 调 `DELETE`,成功后 1 秒后 `location.reload()`。没有撤销窗口。一次手滑无法恢复。

**建议:** 服务端软删除(标记 `deleted_at`),前端 5 秒内显示"撤销"按钮。

---

### 11. AI 摘要可信度无标识

首页和列表显示 `ai_key_point / ai_summary` 时没有标明:

- 是哪个模型生成的(DeepSeek / Qwen?);
- 生成时间;
- 用户能否重新生成 / 报告错误。

读者会把"AI 核心观点"当原文事实,出错时无追责。

---

### 12. CDN 在国内访问慢

`templates/articles/base.html:14-15` 用 `cdn.jsdelivr.net`。该 CDN 在中国大陆解析时常波动,首屏 CSS 阻塞会让站点感官变慢。

**建议:**

- 切到 `cdn.bootcdn.net` / `cdn.staticfile.org`(国内厂商),或
- 自托管到 `static/vendor/`。

---

## 低优先级 / 长期

### 13. 无密码重置 / 注册

`templates/registration/` 目录只有 `login.html`。用户忘密码只能找管理员。

### 14. 可访问性

- 验证码刷新按钮、三点菜单按钮缺 `aria-label`;
- 数学验证码无音频替代,对视障用户不友好;
- "liquid glass" 半透明效果在某些场景可能不过 WCAG AA 对比度。

### 15. 无 dark mode

"Liquid glass"风格在暗色下更出效果,可加 `prefers-color-scheme` 适配。

### 16. 订阅卡片侧栏即使已订阅也照样展示

没有"检测到用户已订阅则隐藏表单 / 改为退订入口"的逻辑。

### 17. 收藏页是同步表单 POST

`articles/views.py:236-254` 的 `collect_view` 走整页刷新,丢失滚动位置,失败时还要重新粘贴 URL。批量框是 AJAX 但单条不是——交互不一致。

---

## 建议落地顺序

1. **修分页 bug**(#1)+ **统一品牌名**(#2)+ **退订改 signed token**(#3) — 1-2 个晚上能搞定,马上拉高质量感。
2. **订阅成功专属页 + double opt-in**(#5)+ **侧栏分页面策略**(#4)。
3. **文章卡片加"已读 / 星标 / 标签"**(#7)+ **搜索增强**(#6)。
4. **批量删除撤销 + AI 来源标识**(#10、#11)。
5. **国内 CDN**(#12)、**dark mode**(#15)。
