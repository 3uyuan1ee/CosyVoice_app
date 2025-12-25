"""
统一错误处理模块

提供完整的异常类层次结构、错误处理装饰器和UI错误对话框
"""

import sys
import traceback
from typing import Optional, Callable, TypeVar, Any
from enum import Enum
from loguru import logger
from PyQt6.QtWidgets import QMessageBox, QWidget
from PyQt6.QtCore import QObject, pyqtSignal
from ui.message_box_helper import MessageBoxHelper


# ==================== 异常类层次结构 ====================

class AppError(Exception):
    """应用基础异常类"""

    def __init__(self, message: str, details: Optional[str] = None,
                 recovery_hint: Optional[str] = None):
        self.message = message
        self.details = details
        self.recovery_hint = recovery_hint
        super().__init__(self.message)

    def __str__(self):
        msg = self.message
        if self.details:
            msg += f"\n详情: {self.details}"
        if self.recovery_hint:
            msg += f"\n建议: {self.recovery_hint}"
        return msg


# 服务层异常
class ServiceError(AppError):
    """服务层异常基类"""
    pass


class AudioServiceError(ServiceError):
    """音频服务异常"""
    pass


class FileServiceError(ServiceError):
    """文件服务异常"""
    pass


class ModelDownloadError(ServiceError):
    """模型下载异常"""
    pass


class ConfigError(ServiceError):
    """配置异常"""
    pass


# UI层异常
class UIError(AppError):
    """UI层异常基类"""
    pass


class AudioGenerationError(UIError):
    """音频生成异常"""
    pass


class ModelLoadError(ServiceError):
    """模型加载异常"""
    pass


class AudioValidationError(ServiceError):
    """音频验证异常"""
    pass


# 资源异常
class ResourceError(AppError):
    """资源异常基类"""
    pass


class GPUResourceError(ResourceError):
    """GPU资源异常"""
    pass


class MemoryError(ResourceError):
    """内存异常"""
    pass


class DiskSpaceError(ResourceError):
    """磁盘空间异常"""
    pass


# ==================== 错误级别枚举 ====================

class ErrorLevel(Enum):
    """错误级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


# ==================== 错误处理器 ====================

class ErrorHandler(QObject):
    """
    统一错误处理器

    职责:
    - 捕获和记录异常
    - 显示用户友好的错误消息
    - 提供恢复建议
    - 错误统计
    """

    error_occurred = pyqtSignal(str, ErrorLevel)  # message, level

    def __init__(self):
        super().__init__()
        self._error_counts = {}
        self._parent_widget = None

    def set_parent_widget(self, widget: QWidget):
        """设置父窗口，用于显示对话框"""
        self._parent_widget = widget

    def handle_exception(self, exc: Exception, context: str = "",
                        show_dialog: bool = True) -> None:
        """
        处理异常

        Args:
            exc: 异常对象
            context: 异常上下文信息
            show_dialog: 是否显示错误对话框
        """
        # 确定错误级别
        if isinstance(exc, (GPUResourceError, MemoryError, DiskSpaceError)):
            level = ErrorLevel.CRITICAL
        elif isinstance(exc, ModelLoadError):
            level = ErrorLevel.ERROR
        elif isinstance(exc, (AudioServiceError, FileServiceError)):
            level = ErrorLevel.ERROR
        elif isinstance(exc, UIError):
            level = ErrorLevel.WARNING
        else:
            level = ErrorLevel.ERROR

        # 记录异常
        self._log_exception(exc, context, level)

        # 更新统计
        exc_type = type(exc).__name__
        self._error_counts[exc_type] = self._error_counts.get(exc_type, 0) + 1

        # 发送信号
        self.error_occurred.emit(str(exc), level)

        # 显示对话框
        if show_dialog and self._parent_widget:
            self._show_error_dialog(exc, level)

    def _log_exception(self, exc: Exception, context: str, level: ErrorLevel):
        """记录异常到日志"""
        log_msg = f"[{context}] {type(exc).__name__}: {exc}"

        if level == ErrorLevel.CRITICAL or level == ErrorLevel.FATAL:
            logger.critical(log_msg, exc_info=True)
        elif level == ErrorLevel.ERROR:
            logger.error(log_msg, exc_info=True)
        elif level == ErrorLevel.WARNING:
            logger.warning(log_msg, exc_info=True)
        else:
            logger.info(log_msg)

    def _show_error_dialog(self, exc: Exception, level: ErrorLevel):
        """显示错误对话框（无图标）"""
        # 确定对话框类型
        if level == ErrorLevel.CRITICAL or level == ErrorLevel.FATAL:
            title = "严重错误"
        elif level == ErrorLevel.ERROR:
            title = "错误"
        elif level == ErrorLevel.WARNING:
            title = "警告"
        else:
            title = "提示"

        # 构建消息
        message = str(exc.message) if hasattr(exc, 'message') else str(exc)

        # 添加详细信息和恢复建议
        details_text = ""
        if hasattr(exc, 'details') and exc.details:
            details_text += f"详情:\n{exc.details}\n\n"
        if hasattr(exc, 'recovery_hint') and exc.recovery_hint:
            details_text += f"建议:\n{exc.recovery_hint}"

        # 使用 MessageBoxHelper 显示对话框（不传递icon参数）
        MessageBoxHelper.with_details(
            self._parent_widget,
            title,
            message,
            icon=None,  # 不使用图标
            details=details_text if details_text else None
        )

    def get_error_statistics(self) -> dict:
        """获取错误统计"""
        return self._error_counts.copy()

    def reset_statistics(self):
        """重置错误统计"""
        self._error_counts.clear()


# ==================== 错误处理装饰器 ====================

T = TypeVar('T')


def handle_errors(context: str = "", show_dialog: bool = True,
                  reraise: bool = False):
    """
    错误处理装饰器

    Args:
        context: 操作上下文描述
        show_dialog: 是否显示错误对话框
        reraise: 是否重新抛出异常
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 获取错误处理器
                error_handler = get_error_handler()

                # 处理异常
                error_handler.handle_exception(e, context, show_dialog)

                # 如果需要重新抛出
                if reraise:
                    raise

                # 根据函数类型返回默认值
                # 如果是协程函数
                if hasattr(func, '__annotations__') and 'return' in func.__annotations__:
                    return None  # type: ignore

                return None  # type: ignore

        return wrapper
    return decorator


def safe_execute(default_return: Any = None):
    """
    安全执行装饰器 - 捕获所有异常并返回默认值

    Args:
        default_return: 发生异常时的默认返回值
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"[{func.__name__}] Error: {e}")
                return default_return  # type: ignore

        return wrapper
    return decorator


# ==================== 全局错误处理器 ====================

_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器实例"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def setup_error_handler(parent_widget: Optional[QWidget] = None) -> ErrorHandler:
    """
    设置全局错误处理器

    Args:
        parent_widget: 父窗口，用于显示对话框

    Returns:
        ErrorHandler: 错误处理器实例
    """
    global _error_handler
    _error_handler = ErrorHandler()
    if parent_widget:
        _error_handler.set_parent_widget(parent_widget)
    return _error_handler


# ==================== 异常上下文管理器 ====================

class ErrorContext:
    """
    错误上下文管理器

    用法:
        with ErrorContext("音频生成", show_dialog=True):
            generate_audio(...)
    """

    def __init__(self, context: str, show_dialog: bool = True,
                 reraise: bool = True):
        self.context = context
        self.show_dialog = show_dialog
        self.reraise = reraise
        self.error_handler = get_error_handler()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # 发生异常，处理它
            self.error_handler.handle_exception(
                exc_val,  # type: ignore
                self.context,
                self.show_dialog
            )
            # 如果不需要重新抛出，返回True抑制异常
            return not self.reraise
        return False


# ==================== 便捷函数 ====================

def show_error(message: str, details: Optional[str] = None,
               recovery_hint: Optional[str] = None,
               parent: Optional[QWidget] = None):
    """
    显示错误对话框

    Args:
        message: 错误消息
        details: 详细信息
        recovery_hint: 恢复建议
        parent: 父窗口
    """
    error = AppError(message, details, recovery_hint)
    get_error_handler().handle_exception(error, "用户操作", True)


def show_warning(message: str, parent: Optional[QWidget] = None):
    """
    显示警告对话框

    Args:
        message: 警告消息
        parent: 父窗口
    """
    MessageBoxHelper.warning(parent, "警告", message)


def show_info(message: str, parent: Optional[QWidget] = None):
    """
    显示信息对话框

    Args:
        message: 信息消息
        parent: 父窗口
    """
    MessageBoxHelper.information(parent, "提示", message)


def log_and_raise_error(exc_class: type, message: str,
                       details: Optional[str] = None,
                       recovery_hint: Optional[str] = None):
    """
    记录并抛出异常

    Args:
        exc_class: 异常类
        message: 错误消息
        details: 详细信息
        recovery_hint: 恢复建议
    """
    exc = exc_class(message, details, recovery_hint)
    logger.error(f"{exc_class.__name__}: {exc}")
    raise exc


# ==================== 启动时异常处理 ====================

class StartupError(AppError):
    """启动时异常"""
    pass


def check_startup_requirements() -> list:
    """
    检查启动时必需的条件

    Returns:
        list: 错误列表，为空表示所有检查通过
    """
    errors = []

    try:
        import PyQt6
    except ImportError:
        errors.append(StartupError(
            "PyQt6未安装",
            "请运行: pip install PyQt6",
            "或者: pip install -r requirements.txt"
        ))

    try:
        import torch
    except ImportError:
        errors.append(StartupError(
            "PyTorch未安装",
            "请运行: pip install torch torchaudio",
            "或者: pip install -r requirements.txt"
        ))

    try:
        import librosa
    except ImportError:
        errors.append(StartupError(
            "librosa未安装",
            "请运行: pip install librosa soundfile",
            "或者: pip install -r requirements.txt"
        ))

    # 检查GPU可用性（仅警告，不阻止启动）
    try:
        import torch
        if torch.cuda.is_available():
            logger.info("CUDA GPU可用")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            logger.info("Apple MPS (Metal)可用")
        else:
            logger.warning("未检测到GPU加速，将使用CPU模式（速度较慢）")
    except Exception as e:
        logger.warning(f"GPU检测失败: {e}")

    return errors


if __name__ == "__main__":
    # 测试错误处理器
    print("测试错误处理器...")

    # 测试异常
    try:
        raise AudioServiceError(
            "音频服务错误",
            "无法加载音频文件",
            "请检查文件格式是否支持"
        )
    except AudioServiceError as e:
        print(f"\n捕获异常: {e}")
        print(f"异常类型: {type(e).__name__}")
        print(f"消息: {e.message}")
        print(f"详情: {e.details}")
        print(f"建议: {e.recovery_hint}")
