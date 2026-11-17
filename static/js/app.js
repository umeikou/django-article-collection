/**
 * Reader - 文章收藏系统前端增强脚本
 */

// 全局配置
const ReaderApp = {
    config: {
        animationDuration: 300,
        toastDuration: 3000,
        apiBaseUrl: '/api/articles/',
    },
    
    // 初始化
    init() {
        this.setupEventListeners();
        this.setupAnimations();
        this.setupPlatformBadges();
        this.setupScrollEffects();
    },
    
    // 设置事件监听器
    setupEventListeners() {
        // 平滑滚动
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
        
        // 表单增强
        this.enhanceForms();
        
        // 键盘快捷键
        this.setupKeyboardShortcuts();
    },
    
    // 设置动画
    setupAnimations() {
        // 页面加载动画
        const animatedElements = document.querySelectorAll('.animate-enter');
        animatedElements.forEach((el, index) => {
            el.style.animationDelay = `${index * 0.1}s`;
        });
        
        // 悬停效果
        this.setupHoverEffects();
    },
    
    // 设置平台标签样式
    setupPlatformBadges() {
        document.querySelectorAll('.platform-badge').forEach(badge => {
            const platform = badge.textContent.toLowerCase().trim();
            
            // 添加对应的CSS类
            if (platform.includes('微信') || platform.includes('wechat')) {
                badge.classList.add('weixin');
            } else if (platform.includes('知乎') || platform.includes('zhihu')) {
                badge.classList.add('zhihu');
            } else if (platform.includes('小红书') || platform.includes('xiaohongshu')) {
                badge.classList.add('xiaohongshu');
            } else if (platform.includes('即刻') || platform.includes('jike')) {
                badge.classList.add('jike');
            } else if (platform.includes('掘金') || platform.includes('juejin')) {
                badge.classList.add('juejin');
            } else if (platform.includes('csdn')) {
                badge.classList.add('csdn');
            }
        });
    },
    
    // 设置滚动效果
    setupScrollEffects() {
        let ticking = false;
        
        function updateScrollEffects() {
            const scrolled = window.pageYOffset;
            const navbar = document.querySelector('.navbar');
            
            if (navbar) {
                if (scrolled > 50) {
                    navbar.style.background = 'rgba(250, 250, 249, 0.95)';
                    navbar.style.boxShadow = '0 8px 32px 0 rgba(28, 25, 23, 0.1)';
                } else {
                    navbar.style.background = 'rgba(250, 250, 249, 0.8)';
                    navbar.style.boxShadow = '0 8px 32px 0 rgba(28, 25, 23, 0.05)';
                }
            }
            
            ticking = false;
        }
        
        function requestTick() {
            if (!ticking) {
                requestAnimationFrame(updateScrollEffects);
                ticking = true;
            }
        }
        
        window.addEventListener('scroll', requestTick);
    },
    
    // 悬停效果
    setupHoverEffects() {
        // 卡片悬停效果
        document.querySelectorAll('.card, .article-item, .liquid-glass-panel').forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-2px)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
            });
        });
        
        // 按钮点击效果
        document.querySelectorAll('.btn').forEach(btn => {
            btn.addEventListener('mousedown', function() {
                this.style.transform = 'scale(0.98)';
            });
            
            btn.addEventListener('mouseup', function() {
                this.style.transform = 'scale(1)';
            });
            
            btn.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1)';
            });
        });
    },
    
    // 表单增强
    enhanceForms() {
        // 自动聚焦第一个输入框
        const firstInput = document.querySelector('input[type="url"], input[type="text"], textarea');
        if (firstInput && !window.location.hash) {
            setTimeout(() => firstInput.focus(), 500);
        }
        
        // 表单验证增强
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', function(e) {
                const submitBtn = this.querySelector('button[type="submit"]');
                if (submitBtn && !submitBtn.disabled) {
                    // 添加加载状态
                    const originalText = submitBtn.innerHTML;
                    submitBtn.innerHTML = '<span class="loading-spinner me-2"></span>处理中...';
                    submitBtn.disabled = true;
                    
                    // 如果表单验证失败，恢复按钮状态
                    setTimeout(() => {
                        if (!this.checkValidity()) {
                            submitBtn.innerHTML = originalText;
                            submitBtn.disabled = false;
                        }
                    }, 100);
                }
            });
        });
    },
    
    // 键盘快捷键
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + K: 聚焦搜索框
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.querySelector('input[name="search"]');
                if (searchInput) {
                    searchInput.focus();
                    searchInput.select();
                }
            }
            
            // Ctrl/Cmd + N: 新建收藏
            if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                e.preventDefault();
                window.location.href = '/collect/';
            }
            
            // ESC: 关闭模态框
            if (e.key === 'Escape') {
                const openModal = document.querySelector('.modal.show');
                if (openModal) {
                    bootstrap.Modal.getInstance(openModal).hide();
                }
            }
        });
    },
    
    // 工具函数
    utils: {
        // 显示Toast通知
        showToast(message, type = 'info', duration = 3000) {
            const toastContainer = document.getElementById('toast-container') || this.createToastContainer();
            
            const toast = document.createElement('div');
            toast.className = `toast align-items-center border-0 ${this.getToastClass(type)}`;
            toast.setAttribute('role', 'alert');
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="bi bi-${this.getToastIcon(type)} me-2"></i>
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            `;
            
            toastContainer.appendChild(toast);
            const bsToast = new bootstrap.Toast(toast, { delay: duration });
            bsToast.show();
            
            // 自动清理
            toast.addEventListener('hidden.bs.toast', () => {
                if (toastContainer.contains(toast)) {
                    toastContainer.removeChild(toast);
                }
            });
            
            return bsToast;
        },
        
        createToastContainer() {
            const container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
            return container;
        },
        
        getToastClass(type) {
            const classes = {
                'success': 'text-bg-success',
                'error': 'text-bg-danger',
                'warning': 'text-bg-warning',
                'info': 'text-bg-primary'
            };
            return classes[type] || classes.info;
        },
        
        getToastIcon(type) {
            const icons = {
                'success': 'check-circle-fill',
                'error': 'x-circle-fill',
                'warning': 'exclamation-triangle-fill',
                'info': 'info-circle-fill'
            };
            return icons[type] || icons.info;
        },
        
        // 获取CSRF Token
        getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        },
        
        // API请求封装
        async apiRequest(url, options = {}) {
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken'),
                },
            };
            
            const mergedOptions = {
                ...defaultOptions,
                ...options,
                headers: {
                    ...defaultOptions.headers,
                    ...options.headers,
                },
            };
            
            try {
                const response = await fetch(url, mergedOptions);
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.message || `HTTP ${response.status}`);
                }
                
                return data;
            } catch (error) {
                console.error('API Request failed:', error);
                throw error;
            }
        },
        
        // 防抖函数
        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
        
        // 节流函数
        throttle(func, limit) {
            let inThrottle;
            return function() {
                const args = arguments;
                const context = this;
                if (!inThrottle) {
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            };
        },
        
        // 格式化时间
        formatTime(date) {
            const now = new Date();
            const diff = now - new Date(date);
            const minutes = Math.floor(diff / 60000);
            const hours = Math.floor(diff / 3600000);
            const days = Math.floor(diff / 86400000);
            
            if (minutes < 1) return '刚刚';
            if (minutes < 60) return `${minutes}分钟前`;
            if (hours < 24) return `${hours}小时前`;
            if (days < 7) return `${days}天前`;
            
            return new Date(date).toLocaleDateString('zh-CN');
        }
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    ReaderApp.init();
});

// 导出到全局作用域
window.ReaderApp = ReaderApp;