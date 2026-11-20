"""Durable, database-backed Xiaoyuzhou podcast collection pipeline."""
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from .models import (Article, CollectionTask, PodcastAnalysisChunk, PodcastAnalysisRollup,
                     PodcastAsrAttempt, PodcastEpisode, PodcastTaskEvent,
                     PodcastTranscriptSegment)

EPISODE_RE = re.compile(r'^/episode/([A-Za-z0-9_-]{1,200})/?$')
EXTERNAL_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,128}$')
SUBMIT_RE = re.compile(r'^✅ 任务已创建 [0-9]+s  id=([A-Za-z0-9_-]{1,128})  status=([A-Za-z0-9_-]{1,32})  size=(?:[0-9]+|None)\r?\n?$')
TERMINAL = {'success', 'failed', 'rejected', 'cancelled', 'needs_attention'}


def normalize_xiaoyuzhou_episode_url(value):
    """Return canonical supported episode URL, or None for every other URL."""
    if not isinstance(value, str) or len(value) > 2048:
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if parsed.scheme not in {'http', 'https'} or parsed.username or parsed.password:
        return None
    try:
        port = parsed.port
    except ValueError:
        return None
    if port not in (None, 80 if parsed.scheme == 'http' else 443):
        return None
    if (parsed.hostname or '').lower() not in {'xiaoyuzhoufm.com', 'www.xiaoyuzhoufm.com'}:
        return None
    match = EPISODE_RE.fullmatch(parsed.path)
    if not match:
        return None
    return 'https://www.xiaoyuzhoufm.com/episode/' + match.group(1)


def safe_event(task, code, message, level='info', actor=None):
    """Append a safe, user-facing event. Callers must never pass provider output."""
    return PodcastTaskEvent.objects.create(task=task, code=code, level=level,
                                           message=str(message)[:500], actor=actor)


def task_payload(task):
    episode = getattr(task, 'podcast_episode', None)
    chunks = episode.analysis_chunks if episode else PodcastAnalysisChunk.objects.none()
    rollups = episode.analysis_rollups if episode else PodcastAnalysisRollup.objects.none()
    article = task.article
    return {
        'success': True, 'task_id': task.id, 'task_url': f'/api/tasks/{task.id}/',
        'status': task.status, 'stage': task.stage, 'progress': task.progress,
        'progress_message': task.progress_message,
        'analysis': {'chunks_completed': chunks.filter(status='succeeded').count(),
                     'chunks_total': chunks.count(),
                     'rollups_completed': rollups.filter(status='succeeded').count(),
                     'rollups_total': rollups.count()},
        'error_code': task.error_code or None, 'next_action': task.next_action or None,
        'retry_allowed': task.status == 'failed' and task.is_retryable and task.is_active and not task.cancel_requested,
        'cancel_allowed': task.is_active and task.status not in {'needs_attention'} and not task.cancel_requested,
        'article': ({'id': article.id, 'title': article.title, 'url': article.url} if article else None),
        'cost': ({'amount': str(task.known_cost_amount), 'currency': task.known_cost_currency}
                 if task.known_cost_amount is not None else None),
    }


class PodcastSubmissionService:
    @staticmethod
    def _article_exists(canonical_url):
        """Detect both exact and historical raw-form Xiaoyuzhou article URLs.

        Historical rows predate podcast_url_key persistence, so dedupe runs a
        bounded candidate scan (xiaoyuzhou URLs only) and normalizes each one.
        """
        if Article.objects.filter(url=canonical_url).exists():
            return True
        for article in Article.objects.filter(url__icontains='xiaoyuzhoufm.com'):
            if normalize_xiaoyuzhou_episode_url(article.url) == canonical_url:
                return True
        return False

    @staticmethod
    def submit(canonical_url, user):
        """Persist only; this method intentionally has no network/subprocess side effects."""
        with transaction.atomic():
            if PodcastSubmissionService._article_exists(canonical_url):
                return None, '该文章已存在', 400
            existing = CollectionTask.objects.filter(task_type='podcast', podcast_url_key=canonical_url, is_active=True).first()
            if existing:
                if existing.created_by_id == user.id or user.is_staff:
                    return existing, '', 202
                return None, '该链接正在处理中', 409
            try:
                task = CollectionTask.objects.create(
                    url=canonical_url, task_type='podcast', created_by=user,
                    podcast_url_key=canonical_url, status='pending', stage='queued',
                    progress=0, progress_message='已排队等待处理', is_active=True,
                )
                PodcastEpisode.objects.create(task=task, canonical_url=canonical_url)
            except IntegrityError:
                existing = CollectionTask.objects.filter(task_type='podcast', podcast_url_key=canonical_url, is_active=True).first()
                if existing and (existing.created_by_id == user.id or user.is_staff):
                    return existing, '', 202
                return None, '该链接正在处理中', 409
            safe_event(task, 'queued', '播客已排队，正在等待后台处理。')
            return task, '', 202


class PodcastMetadataService:
    @staticmethod
    def normalize_and_validate(raw, expected_eid, require_audio=False):
        if not isinstance(raw, dict) or raw.get('eid') != expected_eid:
            raise ValueError('metadata_invalid_response')
        title = raw.get('title')
        if not isinstance(title, str) or not title.strip() or len(title) > 500 or any(ord(c) < 32 for c in title):
            raise ValueError('metadata_invalid_response')
        pay_type = raw.get('pay_type')
        if not isinstance(pay_type, str):
            raise ValueError('metadata_invalid_response')
        if not isinstance(raw.get('is_private'), bool):
            raise ValueError('metadata_invalid_response')
        duration = raw.get('duration')
        if duration is not None and (isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration < 0):
            raise ValueError('metadata_invalid_response')
        audio_url = raw.get('audio_url')
        if require_audio and (not isinstance(audio_url, str) or not audio_url.startswith(('http://', 'https://'))):
            raise ValueError('audio_url_missing')
        def clean(value, limit):
            return value.replace('\x00', '').strip()[:limit] if isinstance(value, str) else ''
        return {'eid': expected_eid, 'title': clean(title, 500), 'podcast': clean(raw.get('podcast'), 500),
                'author': clean(raw.get('author'), 200), 'description': clean(raw.get('description'), 10000),
                'shownotes': clean(raw.get('shownotes'), 50000), 'duration': int(duration) if duration is not None else None,
                'pay_type': pay_type, 'is_private': raw['is_private'], 'audio_url': audio_url or '',
                'hotwords': [clean(x, 40) for x in raw.get('hotwords', []) if isinstance(x, str) and clean(x, 40)][:40],
                'pub_date': raw.get('pub_date')}


class PodcastMetadataAdapter:
    """Runs the versioned adapter with an absolute interpreter/script path."""
    @staticmethod
    def fetch(url):
        command = [settings.PODCAST_PYTHON, settings.PODCAST_METADATA_ADAPTER,
                   '--episode-url', url, '--skill-script', settings.PODCAST_FETCH_SCRIPT]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=settings.PODCAST_METADATA_TIMEOUT,
                                       env={'PATH': settings.PODCAST_CHILD_PATH, 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'})
        except subprocess.TimeoutExpired:
            return None, 'metadata_network_timeout', True
        if completed.returncode or completed.stdout.count('\n') > 1:
            return None, 'metadata_adapter_invalid', False
        try:
            response = json.loads(completed.stdout)
        except (TypeError, ValueError):
            return None, 'metadata_adapter_invalid', False
        if not isinstance(response, dict) or response.get('ok') is not True or not isinstance(response.get('metadata'), dict):
            return None, response.get('code', 'metadata_adapter_invalid') if isinstance(response, dict) else 'metadata_adapter_invalid', bool(response.get('retryable')) if isinstance(response, dict) else False
        return response['metadata'], '', False


class PodcastSubprocessError(RuntimeError):
    """Client error carrying a sanitized stderr snippet for safe events."""
    def __init__(self, code, stderr=''):
        super().__init__(code)
        self.detail = sanitize_detail(stderr)


def sanitize_detail(text, limit=200):
    """Strip URLs, query strings, and anything key-like from diagnostic output."""
    if not isinstance(text, str):
        return ''
    cleaned = re.sub(r'https?://\S+', '[url]', text)
    cleaned = re.sub(r'(?i)((api[-_]?key|token|authorization|signature)\s*[=:]\s*)\S+', r'\1[redacted]', cleaned)
    cleaned = cleaned.replace('\n', ' ').strip()
    return cleaned[:limit]


def format_key_points(points, limit=500):
    """Render stored key points in the numbered structure used by article
    analysis: '1. 主要观点' header followed by 1.1/1.2/… lines."""
    if not isinstance(points, list) or not points:
        return ''
    lines = ['1. 主要观点'] + [f'1.{index} {point}' for index, point in enumerate(points, start=1)]
    return '\n'.join(lines)[:limit]


class PodcastAsrClient:
    def _run(self, args, timeout=300):
        if not os.environ.get('AURALWISE_API_KEY', '').strip():
            raise RuntimeError('asr_credentials_missing')
        env = {'PATH': settings.PODCAST_CHILD_PATH, 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
               'PYTHONIOENCODING': 'utf-8', 'HOME': settings.PODCAST_CHILD_HOME,
               'AURALWISE_API_KEY': os.environ['AURALWISE_API_KEY']}
        return subprocess.run([settings.PODCAST_PYTHON, settings.PODCAST_ASR_SCRIPT, *args],
                              capture_output=True, text=True, timeout=timeout, env=env)
    def submit(self, audio_url, hotwords):
        result = self._run(['submit', '--audio-url', audio_url, '--lang', 'zh', '--mode', 'standard', '--hotwords', *hotwords, '--prompt', '这是一档中文播客，请保留说话人和时间信息。'], 900)
        match = SUBMIT_RE.fullmatch(result.stdout)
        if result.returncode == 0 and match: return match.group(1), match.group(2)
        if re.search(r'^❌ HTTP 429(?:\s|$)', result.stderr): raise RuntimeError('asr_rate_limited')
        if re.search(r'^❌ HTTP 401(?:\s|$)', result.stderr): raise RuntimeError('asr_credentials_invalid')
        if re.search(r'^❌ HTTP 402(?:\s|$)', result.stderr): raise RuntimeError('asr_balance_insufficient')
        raise RuntimeError('asr_submission_uncertain')
    def status(self, external_id):
        result = self._run(['status', external_id])
        if result.returncode: raise PodcastSubprocessError('asr_status_temporary', result.stderr[:500])
        try: data = json.loads(result.stdout)
        except ValueError: raise RuntimeError('asr_status_invalid')
        if not isinstance(data, dict) or data.get('id') != external_id or data.get('status') not in {'pending','processing','done','failed','abandoned'}: raise RuntimeError('asr_status_invalid')
        return data
    def result(self, external_id):
        # auralwise.py `result` prints nothing to stdout without -o; the provider
        # JSON must be fetched through a temp file under PODCAST_TEMP_ROOT.
        os.makedirs(settings.PODCAST_TEMP_ROOT, exist_ok=True)
        fd, path = tempfile.mkstemp(prefix='asr-result-', suffix='.json', dir=settings.PODCAST_TEMP_ROOT)
        os.close(fd)
        try:
            result = self._run(['result', external_id, '-o', path])
            if result.returncode: raise PodcastSubprocessError('asr_result_temporary', result.stderr[:500])
            try:
                with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
            except (OSError, ValueError): raise RuntimeError('asr_result_invalid')
        finally:
            try: os.remove(path)
            except OSError: pass
        if not isinstance(data, dict) or not isinstance(data.get('segments'), list): raise RuntimeError('asr_result_invalid')
        return data


class PodcastTranscriptFormatter:
    @staticmethod
    def format(episode):
        heading = f'# {episode.title}\n\n节目：{episode.podcast_title}\n\n'
        lines = []
        for segment in episode.transcript_segments.order_by('sequence'):
            stamp = ''
            if segment.start_seconds is not None:
                seconds = int(segment.start_seconds); stamp = f'[{seconds//3600:02d}:{seconds%3600//60:02d}:{seconds%60:02d}] '
            speaker = f'{segment.speaker}：' if segment.speaker else ''
            lines.append(f'{stamp}{speaker}{segment.text}')
        return heading + '\n\n'.join(lines)


class PodcastAnalysisService:
    @staticmethod
    def source(episode): return PodcastTranscriptFormatter.format(episode)
    @classmethod
    def prepare(cls, episode):
        source = cls.source(episode)
        if not source: raise ValueError('transcript_empty')
        size = settings.PODCAST_AI_INPUT_MAX - 300
        start = 0; sequence = 0
        while start < len(source):
            end = min(len(source), start + size)
            if end < len(source):
                split = max(source.rfind('\n', start, end), source.rfind('。', start, end), source.rfind(' ', start, end))
                if split > start: end = split + 1
            text = source[start:end]
            PodcastAnalysisChunk.objects.get_or_create(episode=episode, sequence=sequence, defaults={'source_start': start, 'source_end': end, 'input_text': text, 'checksum': hashlib.sha256(text.encode()).hexdigest()})
            start = end; sequence += 1
        chunks = list(episode.analysis_chunks.order_by('sequence'))
        if ''.join(c.input_text for c in chunks) != source: raise ValueError('analysis_coverage_invalid')
        return chunks
    @staticmethod
    def fingerprint(kind, text): return hashlib.sha256(f'{kind}|{text}'.encode()).hexdigest()


class PodcastWorker:
    def __init__(self, worker_id): self.worker_id = worker_id
    def claim(self):
        now = timezone.now()
        candidate = CollectionTask.objects.filter(task_type='podcast', is_active=True).filter(
            Q(status='pending', next_attempt_at__isnull=True) | Q(status='pending', next_attempt_at__lte=now) |
            Q(status='processing', lease_expires_at__lt=now)).exclude(status='needs_attention').order_by('created_at').first()
        if not candidate: return None
        updated = CollectionTask.objects.filter(pk=candidate.pk).filter(Q(lease_expires_at__isnull=True) | Q(lease_expires_at__lt=now)).exclude(cancel_requested=True).update(status='processing', lease_owner=self.worker_id, lease_expires_at=now + timedelta(seconds=settings.PODCAST_LEASE_SECONDS), heartbeat_at=now)
        return CollectionTask.objects.get(pk=candidate.pk) if updated else None
    def _owned(self, task): return CollectionTask.objects.filter(pk=task.pk, lease_owner=self.worker_id, status='processing')
    def _set(self, task, **values):
        self._owned(task).update(**values)
        task.refresh_from_db()
    def _finish(self, task, status_, code='', message='', retryable=False, attention=False, next_action=''):
        values = {'status': 'needs_attention' if attention else status_, 'stage': 'needs_attention' if attention else status_, 'error_code': code, 'progress_message': message, 'error_message': message, 'is_retryable': retryable, 'is_active': retryable or attention, 'lease_owner': '', 'lease_expires_at': None, 'heartbeat_at': None, 'next_action': next_action}
        self._set(task, **values); task.podcast_episode.audio_url = ''; task.podcast_episode.save(update_fields=['audio_url']); safe_event(task, code or status_, message, 'error' if status_ != 'success' else 'info')
    def process(self, task):
        if task.cancel_requested:
            self._finish(task, 'cancelled', 'cancelled', '本地处理已取消。'); return
        episode = task.podcast_episode
        try:
            if task.stage in {'queued', 'metadata'}:
                self._set(task, stage='metadata', progress=5, progress_message='正在检查播客元数据。')
                raw, code, retryable = PodcastMetadataAdapter.fetch(task.url)
                if raw is None: self._fail_retry(task, code, retryable); return
                expected = urlsplit(task.url).path.split('/')[-1]
                data = PodcastMetadataService.normalize_and_validate(raw, expected)
                for field in ('episode_id','title','author','description','shownotes','duration','pay_type','is_private','audio_url','hotwords'):
                    setattr(episode, field, data[field if field != 'episode_id' else 'eid'])
                episode.podcast_title = data['podcast']; episode.save()
                safe_event(task, 'metadata_saved', '已取得播客元数据。')
                if data['pay_type'] != 'FREE' or data['is_private']:
                    self._finish(task, 'rejected', 'restricted_episode', '该单集为付费或受限内容，未提交转写。'); return
                if not data['audio_url']:
                    self._finish(task, 'failed', 'audio_url_missing', '免费单集缺少可用音频地址，请稍后重试。'); return
                self._set(task, stage='asr_submit', progress=20, progress_message='正在提交转写。')
            if task.stage == 'asr_submit':
                attempt = episode.asr_attempts.order_by('-attempt_number').first()
                if attempt and attempt.status in {'submitting','uncertain'} and not attempt.external_task_id:
                    self._finish(task, 'failed', 'asr_submission_uncertain', '转写提交结果不确定，请管理员核实后处理。', attention=True); return
                if not attempt or not attempt.external_task_id:
                    # Owner-guarded CAS billing gate: only the lease owner may spawn a
                    # submit, and only while cancellation has not been requested.
                    if not CollectionTask.objects.filter(pk=task.pk, lease_owner=self.worker_id, cancel_requested=False).exists():
                        self._finish(task, 'cancelled', 'cancelled', '本地处理已取消。'); return
                    if attempt and attempt.status == 'not_started' and not attempt.external_task_id:
                        attempt.status='submitting'; attempt.save()  # reuse the same attempt row (review finding 1)
                    else:
                        attempt = PodcastAsrAttempt.objects.create(episode=episode, attempt_number=episode.asr_attempts.count()+1, status='submitting')
                    task.refresh_from_db()
                    if task.cancel_requested: self._finish(task, 'cancelled', 'cancelled', '本地处理已取消。'); return
                    try: external_id, external_status = PodcastAsrClient().submit(episode.audio_url, episode.hotwords)
                    except RuntimeError as exc:
                        attempt.status = 'uncertain' if str(exc) == 'asr_submission_uncertain' else 'not_started'; attempt.save()
                        self._finish(task, 'failed', str(exc), '转写提交未完成，请根据提示处理。', retryable=str(exc) == 'asr_rate_limited', attention=str(exc) == 'asr_submission_uncertain'); return
                    attempt.external_task_id=external_id; attempt.external_status=external_status; attempt.status='submitted'; attempt.save()
                    task.refresh_from_db()
                    if task.cancel_requested:
                        self._finish(task, 'cancelled', 'cancelled', '本地处理已取消；外部转写任务已提交，可能产生费用。'); return
                self._set(task, status='pending', stage='asr_poll', progress=25, progress_message='正在等待转写完成。', next_attempt_at=timezone.now()+timedelta(seconds=settings.PODCAST_ASR_POLL_SECONDS), lease_owner='', lease_expires_at=None)
                safe_event(task, 'asr_submitted', '转写任务已提交，等待转写完成。')
                return
            if task.stage == 'asr_poll':
                attempt = episode.asr_attempts.filter(external_task_id__gt='').order_by('-attempt_number').first()
                data = PodcastAsrClient().status(attempt.external_task_id)
                attempt.external_status=data['status']; billing=data.get('billing') or {}
                try: amount=Decimal(str(billing.get('amount'))) if billing.get('amount') is not None else None
                except InvalidOperation: amount=None
                if amount is not None: attempt.cost_amount=amount; attempt.cost_currency=str(billing.get('currency',''))[:8]; task.known_cost_amount=amount; task.known_cost_currency=attempt.cost_currency; task.save(update_fields=['known_cost_amount','known_cost_currency'])
                attempt.save()
                if data['status'] in {'pending','processing'}:
                    self._set(task, status='pending', stage='asr_poll', progress=35, progress_message='转写服务正在处理。', next_poll_at=timezone.now()+timedelta(seconds=settings.PODCAST_ASR_POLL_SECONDS), lease_owner='', lease_expires_at=None); return
                if data['status'] != 'done': self._finish(task, 'failed', 'asr_remote_failed', '转写服务未能完成任务，请人工核实。', attention=True); return
                self._set(task, stage='asr_result', progress=55, progress_message='正在获取文字稿。')
            if task.stage == 'asr_result':
                attempt=episode.asr_attempts.filter(external_task_id__gt='').latest('attempt_number'); data=PodcastAsrClient().result(attempt.external_task_id)
                for index, segment in enumerate(data['segments']):
                    text = segment.get('text') if isinstance(segment, dict) else None
                    if not isinstance(text, str) or not text.strip(): raise RuntimeError('asr_result_invalid')
                    PodcastTranscriptSegment.objects.update_or_create(episode=episode, sequence=index, defaults={'text':text.strip(), 'speaker':str(segment.get('speaker',''))[:100], 'start_seconds':segment.get('start'), 'end_seconds':segment.get('end')})
                self._set(task, stage='analysis_prepare', progress=65, progress_message='正在准备全文分析。')
            if task.stage == 'analysis_prepare':
                PodcastAnalysisService.prepare(episode); self._set(task, stage='analysis_chunks', progress=65, progress_message='正在分析全部文字稿。')
            if task.stage == 'analysis_chunks': self._analyze(task, episode)
        except (ValueError, RuntimeError) as exc:
            code = str(exc)
            detail = getattr(exc, 'detail', '')
            if detail:
                safe_event(task, code + '_detail', '子进程诊断: ' + detail, 'warning')
            # Transient provider/network failures back off automatically instead of
            # landing in a terminal state; deterministic errors stay non-retryable.
            self._fail_retry(task, code, code in {'asr_status_temporary', 'asr_result_temporary',
                                                  'metadata_network_timeout', 'asr_status_invalid_retryable'})
    def _fail_retry(self, task, code, retryable):
        if retryable and task.retry_count < 3:
            retries=task.retry_count+1; self._set(task, status='pending', retry_count=retries, next_attempt_at=timezone.now()+timedelta(seconds=(60,300,900)[retries-1]), lease_owner='', lease_expires_at=None, error_code=code, progress_message='临时失败，稍后自动重试。'); safe_event(task, code, '临时服务异常，已安排重试。', 'warning')
        else: self._finish(task, 'failed', code, '处理失败，请查看提示后手动重试。', retryable=retryable)
    def _analyze(self, task, episode):
        from .ai_service import PodcastAnalysisClient
        chunks=list(episode.analysis_chunks.order_by('sequence'))
        for chunk in chunks:
            if chunk.status == 'succeeded': continue
            if chunk.status in {'calling','uncertain'}: self._finish(task,'failed','analysis_uncertain','分析请求结果不确定，请管理员确认。',attention=True); return
            result=self._dispatch_ai(task,'chunk',chunk,episode.title,chunk.input_text)
            if result is None: return
            chunk.status='succeeded'; chunk.summary=result['summary']; chunk.key_points=result['key_points']; chunk.completed_at=timezone.now(); chunk.save()
            done=episode.analysis_chunks.filter(status='succeeded').count(); self._set(task, progress=65+int(25*done/len(chunks)), progress_message=f'已分析 {done}/{len(chunks)} 个片段。')
        texts=[c.summary+'\n'+'; '.join(c.key_points) for c in chunks]
        self._set(task, progress=90, progress_message='正在汇总全文分析。')
        final=self._rollups(task, episode, texts)
        if final is None: return
        transcript=PodcastTranscriptFormatter.format(episode); episode.transcript_checksum=hashlib.sha256(transcript.encode()).hexdigest(); episode.save(update_fields=['transcript_checksum'])
        # 主题分类：基于标题+最终摘要判断，失败回退 misc（不影响收藏）
        try:
            from .ai_service import DeepSeekAIService
            category=DeepSeekAIService().classify_category(episode.title, final.summary)
        except Exception:
            category='misc'
        article, _=Article.objects.get_or_create(url=episode.canonical_url,defaults={'title':episode.title,'content':transcript,'author':episode.author,'platform':'xiaoyuzhou','category':category,'ai_summary':final.summary,'ai_key_point':format_key_points(final.key_points)})
        episode.article=article; episode.audio_url=''; episode.save(update_fields=['article','audio_url'])
        self._set(task,status='success',stage='completed',progress=100,progress_message='播客已收藏并完成全文分析。',article=article,is_active=False,lease_owner='',lease_expires_at=None,error_code='',error_message='',next_action='')
        safe_event(task,'completed','播客已收藏并完成全文分析。')
    def _rollups(self, task, episode, texts):
        """Recursive bounded rollup: each level combines its inputs into groups
        that fit the AI input limit; the last surviving single rollup is final.

        Derived rows whose stored checksum no longer matches the recomputed
        group text (e.g. a stale oversized row from an earlier attempt) are
        reset to pending before dispatch. Returns None after any failure
        terminal state has been written.
        """
        limit=settings.PODCAST_AI_INPUT_MAX - 200
        level=0
        while True:
            groups=[]; current=[]; size=0
            for text in texts:
                add=len(text)+1
                if current and size+add > limit:
                    groups.append('\n'.join(current)); current=[text]; size=add
                else:
                    current.append(text); size+=add
            if current: groups.append('\n'.join(current))
            outs=[]
            for sequence, group_text in enumerate(groups):
                checksum=hashlib.sha256(group_text.encode()).hexdigest()
                rollup, _=PodcastAnalysisRollup.objects.get_or_create(episode=episode, level=level, sequence=sequence, defaults={'input_text': group_text, 'checksum': checksum, 'status': 'pending'})
                if rollup.checksum != checksum:
                    rollup.input_text=group_text; rollup.checksum=checksum; rollup.status='pending'; rollup.error_code=''; rollup.summary=''; rollup.key_points=[]; rollup.completed_at=None; rollup.save()
                if rollup.status != 'succeeded':
                    if rollup.status in {'calling','uncertain'}: self._finish(task,'failed','analysis_uncertain','分析请求结果不确定，请管理员确认。',attention=True); return None
                    result=self._dispatch_ai(task,'rollup',rollup,episode.title,group_text)
                    if result is None: return None
                    rollup.status='succeeded'; rollup.summary=result['summary']; rollup.key_points=result['key_points']; rollup.completed_at=timezone.now(); rollup.save()
                outs.append(rollup.summary+'\n'+'; '.join(rollup.key_points))
            if len(groups) == 1:
                return PodcastAnalysisRollup.objects.get(episode=episode, level=level, sequence=0)
            texts=outs; level+=1
    def _dispatch_ai(self, task, kind, item, title, text):
        """Persist dispatch state, call AI once, and classify the failure matrix.

        request_undispatched (credentials/config): item=failed, task=failed,
            is_retryable=True; manual retry resets the item to pending.
        pre-dispatch rate limited (429, confirmed not accepted): item=pending,
            task=pending with backoff; expires to failed/retryable.
        provider replied 200 with unusable content (analysis_result_invalid):
            item=pending, task=pending with backoff; a re-dispatch is safe
            because the request was confirmed answered (no billing ambiguity).
        request possibly dispatched (network error, 5xx): item=uncertain,
            task=needs_attention; only staff reconcile may requeue.
        invalid local input: terminal, not retryable.
        """
        from .ai_service import PodcastAnalysisClient
        item.status='calling'; item.dispatch_started_at=timezone.now(); item.attempt_number+=1; item.request_fingerprint=PodcastAnalysisService.fingerprint(kind,text); item.save()
        try:
            result=PodcastAnalysisClient().generate_or_raise(kind,title,text)
        except RuntimeError as exc:
            code=str(exc)
            if code == 'analysis_uncertain':
                item.status='uncertain'; item.error_code=code; item.save()
                self._finish(task,'failed','analysis_uncertain','分析请求结果不确定，请管理员确认。',attention=True)
            elif code in {'analysis_credentials_missing','analysis_configuration_error'}:
                item.status='failed'; item.error_code=code; item.save()
                self._finish(task,'failed',code,'AI 配置未就绪，配置完成后可在任务页重试。',retryable=True,next_action='配置 AI 后重试')
            elif code in {'analysis_rate_limited','analysis_result_invalid'}:
                item.status='pending'; item.error_code='' if code == 'analysis_rate_limited' else code; item.save()
                self._fail_retry(task, code, True)
            else:
                item.status='failed'; item.error_code=code; item.save()
                self._finish(task,'failed',code,'分析输入无效，无法自动恢复。',retryable=False)
            return None
        return result
