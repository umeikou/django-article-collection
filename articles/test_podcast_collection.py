"""Focused podcast collection pipeline tests (plan step 2).

All external operations (metadata adapter, ASR client, AI client) are mocked.
No network, subprocess, or credential access happens in this suite.
"""
import json
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (Article, CollectionTask, PodcastAnalysisChunk,
                     PodcastAnalysisRollup, PodcastAsrAttempt)
from .podcast import (PodcastSubmissionService, PodcastWorker,
                      normalize_xiaoyuzhou_episode_url, safe_event, task_payload)

User = get_user_model()

CANONICAL = 'https://www.xiaoyuzhoufm.com/episode/ep123'
META = {
    'eid': 'ep123', 'title': '单集标题', 'podcast': '节目名', 'author': '作者',
    'description': '描述', 'shownotes': 'shownotes', 'duration': 1200,
    'pay_type': 'FREE', 'is_private': False,
    'audio_url': 'https://audio.example/signed/SECRET-URL', 'hotwords': ['热词'],
    'pub_date': None,
}
ASR_STATUS_DONE = {'id': 'ext1', 'status': 'done', 'billing': {'amount': '0.5', 'currency': 'CNY'}}
ASR_STATUS_PROCESSING = {'id': 'ext1', 'status': 'processing', 'billing': None}
ASR_RESULT = {'segments': [{'text': '第一句内容。', 'speaker': '甲', 'start': 0.0, 'end': 3.0}]}
AI_RESULT = {'summary': '摘要', 'key_points': ['要点一', '要点二']}


def make_metadata(**overrides):
    data = dict(META)
    data.update(overrides)
    return data


class NormalizeUrlTests(TestCase):
    def test_valid_forms_canonicalize(self):
        cases = [
            CANONICAL,
            'http://xiaoyuzhoufm.com/episode/ep123',
            'https://xiaoyuzhoufm.com/episode/ep123/',
            'https://www.xiaoyuzhoufm.com/episode/ep123?utm=x#frag',
        ]
        for value in cases:
            self.assertEqual(normalize_xiaoyuzhou_episode_url(value), CANONICAL, value)

    def test_invalid_forms_rejected(self):
        cases = [
            'https://other.com/episode/ep123',
            'https://xiaoyuzhoufm.com/show/ep123',
            'https://xiaoyuzhoufm.com/episode/',
            'https://u:p@xiaoyuzhoufm.com/episode/ep123',
            'https://xiaoyuzhoufm.com:8443/episode/ep123',
            'ftp://xiaoyuzhoufm.com/episode/ep123',
            'https://xiaoyuzhoufm.com/episode/' + 'a' * 201,
            'x' * 2049,
            None, 12,
            'https://xiaoyuzhoufm.com/episode/ep 123',
        ]
        for value in cases:
            self.assertIsNone(normalize_xiaoyuzhou_episode_url(value), repr(value))

    def test_invalid_port_string_rejected_not_raised(self):
        self.assertIsNone(normalize_xiaoyuzhou_episode_url('https://xiaoyuzhoufm.com:bad/episode/ep123'))


class SubmissionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='x')
        self.other = User.objects.create_user(username='bob', password='x')

    def test_submit_creates_task_and_episode(self):
        task, message, code = PodcastSubmissionService.submit(CANONICAL, self.user)
        self.assertEqual(code, 202)
        self.assertEqual(task.task_type, 'podcast')
        self.assertEqual(task.podcast_url_key, CANONICAL)
        self.assertEqual(task.podcast_episode.canonical_url, CANONICAL)
        self.assertTrue(task.is_active)

    def test_same_owner_resubmission_returns_same_task(self):
        first, _, _ = PodcastSubmissionService.submit(CANONICAL, self.user)
        second, _, _ = PodcastSubmissionService.submit(CANONICAL, self.user)
        self.assertEqual(first.id, second.id)
        self.assertEqual(CollectionTask.objects.count(), 1)

    def test_other_user_gets_409_without_task_details(self):
        PodcastSubmissionService.submit(CANONICAL, self.user)
        task, message, code = PodcastSubmissionService.submit(CANONICAL, self.other)
        self.assertIsNone(task)
        self.assertEqual(code, 409)
        self.assertEqual(CollectionTask.objects.count(), 1)

    def test_existing_canonical_article_rejected(self):
        Article.objects.create(title='t', url=CANONICAL, platform='xiaoyuzhou')
        task, message, code = PodcastSubmissionService.submit(CANONICAL, self.user)
        self.assertIsNone(task)
        self.assertEqual(code, 400)

    def test_historical_raw_form_article_rejected(self):
        """http / no-www / query forms of a historical article must dedupe."""
        for raw in ('http://xiaoyuzhoufm.com/episode/ep123',
                    'https://www.xiaoyuzhoufm.com/episode/ep123?utm=1'):
            with self.subTest(raw=raw):
                Article.objects.create(title='旧', url=raw, platform='web')
                task, message, code = PodcastSubmissionService.submit(CANONICAL, self.user)
                self.assertIsNone(task)
                self.assertEqual(code, 400)


class CollectApiTests(TestCase):
    def setUp(self):
        self.client_api = APIClient()
        self.user = User.objects.create_user(username='alice', password='x')

    def test_anonymous_podcast_submit_is_401_without_records(self):
        response = self.client_api.post(reverse('articles:article-collect'), {'url': CANONICAL}, format='json')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(CollectionTask.objects.count(), 0)

    def test_authenticated_submit_returns_safe_202(self):
        self.client_api.force_authenticate(self.user)
        response = self.client_api.post(
            reverse('articles:article-collect'),
            {'url': 'http://xiaoyuzhoufm.com/episode/ep123'}, format='json')
        self.assertEqual(response.status_code, 202)
        body = json.dumps(response.data)
        self.assertNotIn('signed', body)
        self.assertNotIn('SECRET', body)
        self.assertIn('task_id', response.data)
        self.assertEqual(response.data['status'], 'pending')

    def test_batch_podcast_anonymous_item_reports_401(self):
        response = self.client_api.post(
            reverse('articles:article-collect-batch'), {'urls': [CANONICAL]}, format='json')
        self.assertEqual(response.status_code, 201)
        item = response.data['results'][0]
        self.assertEqual(item['status'], 401)
        self.assertFalse(item['success'])
        self.assertEqual(CollectionTask.objects.count(), 0)

    def test_batch_podcast_authenticated_dedupes(self):
        self.client_api.force_authenticate(self.user)
        self.client_api.post(reverse('articles:article-collect'), {'url': CANONICAL}, format='json')
        response = self.client_api.post(
            reverse('articles:article-collect-batch'), {'urls': [CANONICAL]}, format='json')
        item = response.data['results'][0]
        self.assertTrue(item['success'])
        self.assertEqual(CollectionTask.objects.count(), 1)


class WorkerClaimTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='x')
        self.task, _, _ = PodcastSubmissionService.submit(CANONICAL, self.user)

    def test_claim_sets_lease(self):
        claimed = PodcastWorker('w1').claim()
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.status, 'processing')
        self.assertEqual(claimed.lease_owner, 'w1')

    def test_second_worker_cannot_take_live_lease(self):
        PodcastWorker('w1').claim()
        self.assertIsNone(PodcastWorker('w2').claim())

    def test_expired_lease_is_reclaimable(self):
        PodcastWorker('w1').claim()
        CollectionTask.objects.update(lease_expires_at=timezone.now() - timedelta(seconds=1))
        claimed = PodcastWorker('w2').claim()
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.lease_owner, 'w2')

    def test_needs_attention_never_claimed(self):
        CollectionTask.objects.filter(pk=self.task.pk).update(status='needs_attention')
        self.assertIsNone(PodcastWorker('w1').claim())


class WorkerPipelineTests(TestCase):
    """Worker stage machine with every external client mocked."""

    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='x')
        self.task, _, _ = PodcastSubmissionService.submit(CANONICAL, self.user)
        self.worker = PodcastWorker('w1')
        self.claimed = self.worker.claim()

    def _reclaim(self):
        CollectionTask.objects.filter(pk=self.task.pk).update(
            lease_expires_at=timezone.now() - timedelta(seconds=1),
            next_attempt_at=timezone.now() - timedelta(seconds=1))
        return self.worker.claim()

    def _process(self, claimed, meta=None, submit_result=('ext1', 'pending'),
                 submit_side_effect=None, status_result=None, result_result=None):
        with mock.patch('articles.podcast.PodcastMetadataAdapter') as adapter, \
             mock.patch('articles.podcast.PodcastAsrClient') as asr, \
             mock.patch('articles.ai_service.PodcastAnalysisClient') as ai:
            adapter.fetch.return_value = (make_metadata() if meta is None else meta, '', False)
            asr.return_value.submit.return_value = submit_result
            if submit_side_effect is not None:
                asr.return_value.submit.side_effect = submit_side_effect
            asr.return_value.status.return_value = ASR_STATUS_PROCESSING if status_result is None else status_result
            asr.return_value.result.return_value = ASR_RESULT if result_result is None else result_result
            ai.return_value.generate_or_raise.return_value = dict(AI_RESULT)
            self.worker.process(claimed)
        self.task.refresh_from_db()
        return self.task

    def test_paid_episode_rejected_before_asr(self):
        task = self._process(self.claimed, meta=make_metadata(pay_type='PAID'))
        self.assertEqual(task.status, 'rejected')
        self.assertFalse(task.is_active)
        self.assertEqual(PodcastAsrAttempt.objects.count(), 0)
        self.assertEqual(task.podcast_episode.audio_url, '')

    def test_private_episode_rejected(self):
        task = self._process(self.claimed, meta=make_metadata(is_private=True))
        self.assertEqual(task.status, 'rejected')

    def test_missing_audio_fails_without_asr(self):
        task = self._process(self.claimed, meta=make_metadata(audio_url=''))
        self.assertEqual(task.status, 'failed')
        self.assertEqual(PodcastAsrAttempt.objects.count(), 0)

    def test_submit_boundary_releases_lease_and_schedules_poll(self):
        task = self._process(self.claimed)
        self.assertEqual(task.status, 'pending')
        self.assertEqual(task.stage, 'asr_poll')
        self.assertEqual(task.lease_owner, '')
        self.assertIsNotNone(task.next_attempt_at)
        self.assertEqual(PodcastAsrAttempt.objects.get().status, 'submitted')
        self.assertTrue(task.podcast_events.filter(code='asr_submitted').exists())

    def test_full_happy_path_creates_article(self):
        task = self._process(self.claimed)  # metadata → submit → poll processing
        claimed = self._reclaim()
        task = self._process(claimed, status_result=ASR_STATUS_DONE)
        self.assertEqual(task.status, 'success')
        article = task.article
        self.assertIsNotNone(article)
        self.assertEqual(article.platform, 'xiaoyuzhou')
        self.assertIn('第一句内容。', article.content)
        self.assertTrue(article.ai_key_point.startswith('1. 主要观点\n1.1 '))
        self.assertEqual(task.podcast_episode.audio_url, '')
        self.assertEqual(PodcastAnalysisChunk.objects.filter(status='succeeded').count(), 1)
        self.assertEqual(PodcastAnalysisRollup.objects.filter(status='succeeded').count(), 1)
        self.assertEqual(task.known_cost_amount, Decimal('0.5'))

    def test_asr_submit_429_reuses_same_attempt(self):
        """Confirmed-not-accepted 429 → attempt back to not_started, retryable;
        next run reuses the SAME attempt row and submits successfully."""
        task = self._process(self.claimed, submit_side_effect=RuntimeError('asr_rate_limited'))
        self.assertEqual(task.status, 'failed')
        self.assertTrue(task.is_retryable)
        attempt = PodcastAsrAttempt.objects.get()
        self.assertEqual(attempt.status, 'not_started')
        # manual-retry semantics: reset the task like POST /api/tasks/{id}/retry/
        CollectionTask.objects.filter(pk=task.pk).update(
            status='pending', stage='asr_submit', next_attempt_at=None,
            error_code='', error_message='')
        claimed = self._reclaim()
        task = self._process(claimed)
        self.assertEqual(PodcastAsrAttempt.objects.count(), 1, 'must reuse the same attempt row')
        self.assertEqual(PodcastAsrAttempt.objects.get().status, 'submitted')

    def test_asr_submit_uncertain_goes_needs_attention_and_never_auto_resubmits(self):
        task = self._process(self.claimed, submit_side_effect=RuntimeError('asr_submission_uncertain'))
        self.assertEqual(task.status, 'needs_attention')
        self.assertEqual(PodcastAsrAttempt.objects.get().status, 'uncertain')
        # worker never re-claims needs_attention tasks
        self.assertIsNone(PodcastWorker('w9').claim())

    def test_cancel_before_submit_prevents_spawn(self):
        def set_cancel(*args, **kwargs):
            CollectionTask.objects.filter(pk=self.task.pk).update(cancel_requested=True)
            return ('ext1', 'pending')

        with mock.patch('articles.podcast.PodcastMetadataAdapter') as adapter, \
             mock.patch('articles.podcast.PodcastAsrClient') as asr, \
             mock.patch('articles.ai_service.PodcastAnalysisClient'):
            adapter.fetch.return_value = (make_metadata(), '', False)
            asr.return_value.submit.side_effect = set_cancel
            self.worker.process(self.claimed)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'cancelled')
        asr.return_value.submit.assert_called()


class WorkerAiErrorMatrixTests(TestCase):
    """Review finding 4: per-failure-class item/task state transitions."""

    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='x')
        self.task, _, _ = PodcastSubmissionService.submit(CANONICAL, self.user)
        self.worker = PodcastWorker('w1')
        self.claimed = self.worker.claim()

    def _reclaim(self):
        CollectionTask.objects.filter(pk=self.task.pk).update(
            lease_expires_at=timezone.now() - timedelta(seconds=1),
            next_attempt_at=timezone.now() - timedelta(seconds=1))
        return self.worker.claim()

    def _process_ai(self, side_effect):
        """Run from metadata through analysis with the AI client raising."""
        claimed = self.claimed or self._reclaim()
        with mock.patch('articles.podcast.PodcastMetadataAdapter') as adapter, \
             mock.patch('articles.podcast.PodcastAsrClient') as asr:
            adapter.fetch.return_value = (make_metadata(), '', False)
            asr.return_value.submit.return_value = ('ext1', 'pending')
            asr.return_value.status.return_value = dict(ASR_STATUS_PROCESSING)
            self.worker.process(claimed)
        self.task.refresh_from_db()
        self.assertEqual(self.task.stage, 'asr_poll')
        claimed = self._reclaim()
        with mock.patch('articles.podcast.PodcastAsrClient') as asr, \
             mock.patch('articles.ai_service.PodcastAnalysisClient') as ai:
            asr.return_value.status.return_value = dict(ASR_STATUS_DONE)
            asr.return_value.result.return_value = dict(ASR_RESULT)
            ai.return_value.generate_or_raise.side_effect = side_effect
            self.worker.process(claimed)
        self.task.refresh_from_db()
        self.claimed = None
        return self.task

    def test_credentials_missing_is_failed_retryable_with_next_action(self):
        task = self._process_ai(RuntimeError('analysis_credentials_missing'))
        self.assertEqual(task.status, 'failed')
        self.assertTrue(task.is_retryable)
        self.assertTrue(task.is_active)
        self.assertEqual(task.next_action, '配置 AI 后重试')
        chunk = PodcastAnalysisChunk.objects.get()
        self.assertEqual(chunk.status, 'failed')
        self.assertEqual(chunk.error_code, 'analysis_credentials_missing')

    def test_configuration_error_is_retryable(self):
        task = self._process_ai(RuntimeError('analysis_configuration_error'))
        self.assertEqual(task.status, 'failed')
        self.assertTrue(task.is_retryable)
        self.assertFalse(task.status == 'needs_attention')

    def test_rate_limited_backs_off_without_terminal_state(self):
        task = self._process_ai(RuntimeError('analysis_rate_limited'))
        self.assertEqual(task.status, 'pending')
        self.assertIsNotNone(task.next_attempt_at)
        self.assertEqual(PodcastAnalysisChunk.objects.get().status, 'pending')

    def test_uncertain_request_goes_needs_attention(self):
        task = self._process_ai(RuntimeError('analysis_uncertain'))
        self.assertEqual(task.status, 'needs_attention')
        self.assertEqual(PodcastAnalysisChunk.objects.get().status, 'uncertain')
        self.assertIsNone(PodcastWorker('w9').claim())

    def test_provider_invalid_json_backs_off_and_redispatches(self):
        """200-with-bad-content is confirmed answered: retry is safe, no ambiguity."""
        task = self._process_ai(RuntimeError('analysis_result_invalid'))
        self.assertEqual(task.status, 'pending')
        self.assertIsNotNone(task.next_attempt_at)
        chunk = PodcastAnalysisChunk.objects.get()
        self.assertEqual(chunk.status, 'pending')
        self.assertEqual(chunk.error_code, 'analysis_result_invalid')

    def test_retry_after_config_fix_completes(self):
        self._process_ai(RuntimeError('analysis_credentials_missing'))
        self.assertEqual(self.task.status, 'failed')
        # manual-retry semantics: reset failed items to pending, then AI succeeds
        CollectionTask.objects.filter(pk=self.task.pk).update(
            status='pending', stage='analysis_chunks', next_attempt_at=None,
            error_code='', error_message='', next_action='')
        PodcastAnalysisChunk.objects.filter(status='failed').update(
            status='pending', error_code='')
        claimed = self._reclaim()
        with mock.patch('articles.ai_service.PodcastAnalysisClient') as ai:
            ai.return_value.generate_or_raise.return_value = dict(AI_RESULT)
            self.worker.process(claimed)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'success')
        self.assertIsNotNone(self.task.article)


class RedactionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='x')
        self.task, _, _ = PodcastSubmissionService.submit(CANONICAL, self.user)

    def test_payload_and_events_never_contain_audio_url(self):
        from .models import PodcastEpisode, PodcastTaskEvent
        PodcastEpisode.objects.filter(task=self.task).update(
            audio_url='https://audio.example/signed/SECRET-URL')
        self.task.refresh_from_db()
        body = json.dumps(task_payload(self.task))
        self.assertNotIn('SECRET', body)
        self.assertNotIn('audio.example', body)
        safe_event(self.task, 'test_event', '进度事件')
        for event in PodcastTaskEvent.objects.filter(task=self.task):
            blob = json.dumps({'m': event.message, 'c': event.code})
            self.assertNotIn('SECRET', blob)
            self.assertNotIn('audio.example', blob)


class AiResultNormalizationTests(TestCase):
    """Verbose-but-valid provider content must be normalized, not rejected."""

    def _post(self, content):
        response = mock.Mock(status_code=200)
        response.json.return_value = {'choices': [{'message': {'content': content}}]}
        return response

    def _run(self, content):
        from articles.ai_service import PodcastAnalysisClient
        with mock.patch('articles.ai_service.requests.post', return_value=self._post(content)):
            return PodcastAnalysisClient().generate_or_raise('chunk', '标题', '内容文字')

    def test_six_points_truncated_to_five(self):
        content = json.dumps({'summary': '摘要' * 300, 'key_points': ['第%d条要点内容' % i for i in range(6)]}, ensure_ascii=False)
        result = self._run(content)
        self.assertEqual(len(result['key_points']), 5)
        self.assertLessEqual(len(result['summary']), 500)

    def test_overlong_point_truncated(self):
        content = json.dumps({'summary': '摘要', 'key_points': ['甲' * 120, '乙' * 120]}, ensure_ascii=False)
        result = self._run(content)
        self.assertEqual(len(result['key_points'][0]), 80)

    def test_unusable_structure_still_rejected(self):
        with self.assertRaises(RuntimeError):
            self._run(json.dumps({'summary': '', 'key_points': ['只有一条']}))


class RecursiveRollupTests(TestCase):
    """Combined chunk outputs over the AI input limit must split into levels."""

    def test_large_combined_input_splits_across_levels(self):
        user = User.objects.create_user(username='alice', password='x')
        task, _, _ = PodcastSubmissionService.submit(CANONICAL, user)
        episode = task.podcast_episode
        worker = PodcastWorker('w1')
        with mock.patch('articles.ai_service.PodcastAnalysisClient') as ai:
            ai.return_value.generate_or_raise.return_value = dict(AI_RESULT)
            final = worker._rollups(task, episode, ['甲' * 1500, '乙' * 1500, '丙' * 1500])
        self.assertIsNotNone(final)
        self.assertEqual(final.status, 'succeeded')
        self.assertEqual(final.summary, '摘要')
        # 3×1500 chars cannot fit one call: level 0 splits into 3, level 1 is final
        self.assertEqual(PodcastAnalysisRollup.objects.filter(level=0).count(), 3)
        self.assertEqual(PodcastAnalysisRollup.objects.filter(level=1).count(), 1)

    def test_stale_oversized_rollup_row_is_reset(self):
        import hashlib as _h
        user = User.objects.create_user(username='alice', password='x')
        task, _, _ = PodcastSubmissionService.submit(CANONICAL, user)
        episode = task.podcast_episode
        stale = '旧' * 11000
        PodcastAnalysisRollup.objects.create(episode=episode, level=0, sequence=0,
            input_text=stale, checksum=_h.sha256(stale.encode()).hexdigest(), status='failed',
            error_code='analysis_input_invalid')
        worker = PodcastWorker('w1')
        with mock.patch('articles.ai_service.PodcastAnalysisClient') as ai:
            ai.return_value.generate_or_raise.return_value = dict(AI_RESULT)
            final = worker._rollups(task, episode, ['短文本一', '短文本二'])
        self.assertIsNotNone(final)
        row = PodcastAnalysisRollup.objects.get(level=0, sequence=0)
        self.assertEqual(row.status, 'succeeded')
        self.assertNotEqual(row.checksum, _h.sha256(stale.encode()).hexdigest())


class ArticleAnalysisPromptTests(TestCase):
    def test_article_content_not_truncated(self):
        from articles.ai_service import DeepSeekAIService
        svc = DeepSeekAIService()
        svc.is_available = lambda: True
        captured = []
        svc.generate = lambda prompt, **kw: (captured.append(prompt) or '1. 主要观点\n1.1 测试观点')
        long_content = '这是一段测试内容。' * 700  # ~6300 chars, well over the old 3000 cap
        svc.analyze_article(long_content, '标题')
        self.assertEqual(len(captured), 2)  # key_point + summary prompts
        self.assertGreater(max(len(p) for p in captured), 6000)
        self.assertNotIn('...', captured[0][-20:])

    def test_podcast_prompt_includes_style_requirements(self):
        from articles.ai_service import PodcastAnalysisClient
        client = PodcastAnalysisClient()
        captured = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured['prompt'] = json['messages'][0]['content']
            response = mock.Mock(status_code=200)
            response.json.return_value = {'choices': [{'message': {'content': '{"summary":"摘要","key_points":["一","二"]}'}}]}
            return response

        with mock.patch('articles.ai_service.requests.post', side_effect=fake_post):
            client.generate_or_raise('chunk', '标题', '内容文字')
        prompt = captured['prompt']
        for marker in ('金句', '底层逻辑', '只返回 JSON', 'key_points', '300 字左右'):
            self.assertIn(marker, prompt)
