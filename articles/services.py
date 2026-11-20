"""
文章收藏系统 - 业务逻辑服务
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
import logging
from .models import Article, CollectionTask
from .ai_service import get_ai_service

logger = logging.getLogger(__name__)


class ArticleParserService:
    """文章解析服务"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
    
    def parse_article(self, url: str) -> Dict:
        """解析文章内容"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            platform = Article.detect_platform(url)
            
            # 根据平台解析
            if platform == "weixin":
                return self._parse_weixin(soup, url, platform)
            elif platform == "xiaohongshu":
                return self._parse_xiaohongshu(soup, url, platform)
            elif platform == "jike":
                return self._parse_jike(soup, url, platform)
            elif platform == "zhihu":
                return self._parse_zhihu(soup, url, platform)
            else:
                return self._parse_generic(soup, url, platform)
                
        except Exception as e:
            return {
                'url': url,
                'title': None,
                'content': None,
                'author': None,
                'publish_time': None,
                'platform': Article.detect_platform(url),
                'error': str(e)
            }
    
    def _parse_weixin(self, soup: BeautifulSoup, url: str, platform: str) -> Dict:
        """解析微信公众号文章"""
        title = soup.find('h1', class_='rich_media_title')
        title = title.get_text(strip=True) if title else None
        
        author = soup.find('a', class_='rich_media_meta_link')
        author = author.get_text(strip=True) if author else None
        
        publish_time = soup.find('em', id='publish_time')
        publish_time = publish_time.get_text(strip=True) if publish_time else None
        
        content_div = soup.find('div', class_='rich_media_content')
        content = content_div.get_text(strip=True) if content_div else None
        
        return {
            'url': url,
            'title': title,
            'content': content,
            'author': author,
            'publish_time': publish_time,
            'platform': platform
        }
    
    def _parse_xiaohongshu(self, soup: BeautifulSoup, url: str, platform: str) -> Dict:
        """解析小红书文章"""
        title = soup.find('meta', property='og:title')
        title = title['content'] if title else None
        
        description = soup.find('meta', property='og:description')
        content = description['content'] if description else None
        
        return {
            'url': url,
            'title': title,
            'content': content,
            'author': None,
            'publish_time': None,
            'platform': platform
        }
    
    def _parse_jike(self, soup: BeautifulSoup, url: str, platform: str) -> Dict:
        """解析即刻文章"""
        title = soup.find('meta', property='og:title')
        title = title['content'] if title else None
        
        description = soup.find('meta', property='og:description')
        content = description['content'] if description else None
        
        return {
            'url': url,
            'title': title,
            'content': content,
            'author': None,
            'publish_time': None,
            'platform': platform
        }
    
    def _parse_zhihu(self, soup: BeautifulSoup, url: str, platform: str) -> Dict:
        """解析知乎文章 - 增强版"""
        # 多种方式获取标题
        title = None
        
        # 1. 文章标题
        title_element = soup.find('h1', class_='Post-Title')
        if title_element:
            title = title_element.get_text(strip=True)
        
        # 2. 问题标题
        if not title:
            question_title = soup.find('h1', class_='QuestionHeader-title')
            if question_title:
                title = question_title.get_text(strip=True)
        
        # 3. og:title
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content', '').strip()
        
        # 4. 通用 title 标签
        if not title:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
                # 移除知乎后缀
                if title.endswith(' - 知乎'):
                    title = title[:-4].strip()
        
        # 获取作者
        author = None
        
        # 1. 作者链接
        author_link = soup.find('a', class_='UserLink-link')
        if author_link:
            author = author_link.get_text(strip=True)
        
        # 2. meta author
        if not author:
            author_meta = soup.find('meta', attrs={'name': 'author'})
            if author_meta:
                author = author_meta.get('content', '').strip()
        
        # 获取内容
        content = None
        
        # 1. 文章内容
        content_div = soup.find('div', class_='RichContent-inner')
        if content_div:
            content = content_div.get_text(strip=True)[:500] + '...' if len(content_div.get_text(strip=True)) > 500 else content_div.get_text(strip=True)
        
        # 2. 回答内容
        if not content:
            answer_content = soup.find('div', class_='RichText')
            if answer_content:
                content = answer_content.get_text(strip=True)[:500] + '...' if len(answer_content.get_text(strip=True)) > 500 else answer_content.get_text(strip=True)
        
        # 3. og:description
        if not content:
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                content = og_desc.get('content', '').strip()
        
        return {
            'url': url,
            'title': title,
            'content': content,
            'author': author,
            'publish_time': None,
            'platform': platform
        }
    
    def _parse_generic(self, soup: BeautifulSoup, url: str, platform: str) -> Dict:
        """通用解析方法 - 增强版"""
        # 多种方式尝试获取标题
        title = None
        
        # 1. 尝试 og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            title = og_title['content'].strip()
        
        # 2. 尝试 twitter:title
        if not title:
            twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
            if twitter_title and twitter_title.get('content'):
                title = twitter_title['content'].strip()
        
        # 3. 尝试 title 标签
        if not title:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
        
        # 4. 尝试 h1 标签
        if not title:
            h1_tag = soup.find('h1')
            if h1_tag:
                title = h1_tag.get_text(strip=True)
        
        # 5. 尝试常见的文章标题类名
        if not title:
            title_selectors = [
                '.article-title', '.post-title', '.entry-title',
                '.title', '.headline', '.article-header h1',
                '[class*="title"]', '[id*="title"]'
            ]
            for selector in title_selectors:
                element = soup.select_one(selector)
                if element:
                    title = element.get_text(strip=True)
                    break
        
        # 清理标题
        if title:
            # 移除常见的网站后缀
            suffixes_to_remove = [
                ' - 知乎', ' - 掘金', ' - CSDN博客', ' - 博客园',
                ' | 微信公众平台', ' - 简书', ' - 开源中国',
                ' - GitHub', ' - Stack Overflow'
            ]
            for suffix in suffixes_to_remove:
                if title.endswith(suffix):
                    title = title[:-len(suffix)].strip()
                    break
        
        # 获取内容描述
        content = None
        
        # 1. 尝试 og:description
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            content = og_desc['content'].strip()
        
        # 2. 尝试 description meta
        if not content:
            desc_meta = soup.find('meta', attrs={'name': 'description'})
            if desc_meta and desc_meta.get('content'):
                content = desc_meta['content'].strip()
        
        # 3. 尝试文章内容区域
        if not content:
            content_selectors = [
                '.article-content', '.post-content', '.entry-content',
                '.content', '.article-body', 'article', 'main'
            ]
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    # 获取前200个字符作为摘要
                    text = element.get_text(strip=True)
                    if len(text) > 50:  # 确保有足够的内容
                        content = text[:200] + '...' if len(text) > 200 else text
                        break
        
        # 尝试获取作者信息
        author = None
        author_selectors = [
            'meta[name="author"]', 'meta[property="article:author"]',
            '.author', '.byline', '.post-author', '[class*="author"]'
        ]
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    author = element.get('content', '').strip()
                else:
                    author = element.get_text(strip=True)
                if author:
                    break
        
        return {
            'url': url,
            'title': title,
            'content': content,
            'author': author,
            'publish_time': None,
            'platform': platform
        }


class ArticleCollectionService:
    """文章收藏服务"""
    
    def __init__(self):
        self.parser = ArticleParserService()
    
    def collect_article(self, url: str, enable_ai: bool = True) -> tuple[bool, str, Optional[Article]]:
        """
        收藏单篇文章
        
        Args:
            url: 文章URL
            enable_ai: 是否启用AI分析（默认启用）
        """
        # 检查是否已存在
        if Article.objects.filter(url=url).exists():
            article = Article.objects.get(url=url)
            return True, "文章已存在", article
        
        # 创建收藏任务
        task = CollectionTask.objects.create(url=url, status='processing')
        
        try:
            # 解析文章
            article_data = self.parser.parse_article(url)
            
            if article_data.get('error'):
                task.status = 'failed'
                task.error_message = article_data['error']
                task.save()
                return False, f"解析失败: {article_data['error']}", None
            
            # AI分析（如果启用且有内容）
            ai_summary = ''
            ai_key_point = ''
            category = 'misc'

            if enable_ai and article_data.get('content'):
                logger.info(f"开始AI分析文章: {article_data.get('title', 'Unknown')}")
                try:
                    ai_service = get_ai_service()
                    if ai_service.is_available():
                        ai_result = ai_service.analyze_article(
                            content=article_data.get('content', ''),
                            title=article_data.get('title', '')
                        )
                        ai_summary = ai_result.get('summary', '')
                        ai_key_point = ai_result.get('key_point', '')
                        category = ai_result.get('category', 'misc')
                        logger.info(f"AI分析完成: 核心观点={ai_key_point[:50]}... 分类={category}")
                    else:
                        logger.warning("AI服务不可用，跳过AI分析")
                except Exception as e:
                    logger.error(f"AI分析失败: {str(e)}")
                    # AI分析失败不影响文章收藏

            # 保存文章
            article = Article.objects.create(
                url=article_data['url'],
                title=article_data.get('title'),
                content=article_data.get('content'),
                author=article_data.get('author'),
                publish_time=article_data.get('publish_time'),
                platform=article_data.get('platform'),
                category=category,
                ai_summary=ai_summary,
                ai_key_point=ai_key_point
            )
            
            task.status = 'success'
            task.article = article
            task.save()
            
            return True, "收藏成功", article
            
        except Exception as e:
            task.status = 'failed'
            task.error_message = str(e)
            task.save()
            return False, f"收藏失败: {str(e)}", None
    
    def collect_batch_articles(self, urls: list) -> Dict:
        """批量收藏文章"""
        results = []
        success_count = 0
        
        for url in urls:
            success, message, article = self.collect_article(url)
            if success:
                success_count += 1
            
            results.append({
                'url': url,
                'success': success,
                'message': message,
                'article_id': article.id if article else None
            })
        
        return {
            'total': len(urls),
            'success': success_count,
            'failed': len(urls) - success_count,
            'results': results
        }