"""
反馈服务 - 发送用户反馈邮件
- 生成反馈邮件
- 调用系统邮件客户端发送邮件
- 收集系统信息和使用统计
"""

import os
import threading
from typing import Optional, Dict, Any
from loguru import logger


class FeedbackService:
    """
    反馈服务

    单例模式，全局唯一实例

    职责:
    - 生成反馈邮件内容
    - 调用系统邮件客户端
    - 收集系统信息
    """

    _instance: Optional['FeedbackService'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 避免重复初始化
        if hasattr(self, '_initialized'):
            return

        self._initialized = True

        # 反馈邮箱
        self.feedback_email = "1481059602@qq.com"

        logger.info("[FeedbackService] Feedback service initialized")

    def send_feedback(
        self,
        subject: str = "",
        message: str = "",
        include_logs: bool = False,
        include_stats: bool = True
    ) -> bool:
        """
        发送反馈邮件

        Args:
            subject: 邮件主题
            message: 反馈消息
            include_logs: 是否包含日志
            include_stats: 是否包含统计信息

        Returns:
            bool: 是否成功
        """
        try:
            logger.info("[FeedbackService] Preparing feedback email...")

            # 构建邮件内容
            email_body = self._build_email_body(
                subject,
                message,
                include_logs,
                include_stats
            )

            # 构建邮件URL
            mailto_url = self._build_mailto_url(
                self.feedback_email,
                subject or "CosyVoice_app Feedback",
                email_body
            )

            # 调用系统邮件客户端
            success = self._open_email_client(mailto_url)

            if success:
                logger.info("[FeedbackService] Feedback email sent successfully")
            else:
                logger.warning("[FeedbackService] Failed to open email client")

            return success

        except Exception as e:
            logger.error(f"[FeedbackService] Error sending feedback: {e}")
            return False

    def _build_email_body(
        self,
        subject: str,
        message: str,
        include_logs: bool,
        include_stats: bool
    ) -> str:
        """构建邮件正文"""
        import platform

        body_parts = []
        body_parts.append("=" * 60)
        body_parts.append("CosyVoice_app User Feedback")
        body_parts.append("=" * 60)
        body_parts.append("")

        # 反馈消息
        if message:
            body_parts.append("Feedback:")
            body_parts.append(message)
            body_parts.append("")

        # 系统信息
        body_parts.append("System Information:")
        body_parts.append(f"  Platform: {platform.system()} {platform.release()}")
        body_parts.append(f"  Python: {platform.python_version()}")
        body_parts.append(f"  Architecture: {platform.machine()}")
        body_parts.append("")

        # 应用版本
        try:
            from backend.config_manager import get_config_manager
            config = get_config_manager().get_config()
            body_parts.append("Application Info:")
            body_parts.append(f"  Version: 1.0.0")  # 当前版本
            body_parts.append(f"  Default Model: {config.default_model}")
            body_parts.append(f"  Device: {config.device}")
            body_parts.append("")
        except Exception:
            pass

        # 使用统计
        if include_stats:
            try:
                from backend.statistics_service import get_statistics_service
                stats_service = get_statistics_service()
                stats = stats_service.get_formatted_statistics()

                body_parts.append("Usage Statistics:")
                for key, value in stats.items():
                    body_parts.append(f"  {key}: {value}")
                body_parts.append("")
            except Exception:
                pass

        # 日志
        if include_logs:
            try:
                from backend.path_manager import PathManager
                path_manager = PathManager()
                log_file = os.path.join(path_manager.get_log_path(), "cosyvoice_app.log")

                if os.path.exists(log_file):
                    body_parts.append("Recent Logs:")
                    # 只读取最近100行日志
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        recent_logs = lines[-100:] if len(lines) > 100 else lines
                        body_parts.append("".join(recent_logs))
                    body_parts.append("")
            except Exception:
                pass

        body_parts.append("=" * 60)
        body_parts.append("Sent from CosyVoice_app")
        body_parts.append("Author: @3uyuan1ee")
        body_parts.append("License: MIT")
        body_parts.append("=" * 60)

        return "\n".join(body_parts)

    def _build_mailto_url(self, email: str, subject: str, body: str) -> str:
        """构建mailto URL"""
        import urllib.parse

        params = []
        if subject:
            params.append(f"subject={urllib.parse.quote(subject)}")
        if body:
            params.append(f"body={urllib.parse.quote(body)}")

        url = f"mailto:{email}"
        if params:
            url += "?" + "&".join(params)

        return url

    def _open_email_client(self, mailto_url: str) -> bool:
        """
        打开系统邮件客户端

        Args:
            mailto_url: mailto URL

        Returns:
            bool: 是否成功
        """
        try:
            import webbrowser
            webbrowser.open(mailto_url)
            return True
        except Exception as e:
            logger.error(f"[FeedbackService] Error opening email client: {e}")
            return False

    def get_feedback_email(self) -> str:
        """获取反馈邮箱"""
        return self.feedback_email


# ==================== 全局实例 ====================

_feedback_service: Optional[FeedbackService] = None


def get_feedback_service() -> FeedbackService:
    """获取全局反馈服务实例"""
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = FeedbackService()
    return _feedback_service
