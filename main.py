#!/usr/bin/env python3
"""
CosyVoice_app - PyQt6 主程序入口
"""

import sys
import signal
import os
import multiprocessing
from pathlib import Path
from loguru import logger
from PyQt6.QtWidgets import QApplication, QMessageBox

# 修复macOS上soundfile与PyQt6的多进程冲突
# 必须在创建QApplication之前设置
try:
    if sys.platform == 'darwin':
        # 设置multiprocessing使用spawn方式，避免fork方式与PyQt6冲突
        multiprocessing.set_start_method('spawn', force=False)
        # 设置环境变量，防止libsndfile使用多进程
        os.environ['SF_ALLOW_MULTIPROCESSING'] = '0'
except RuntimeError:
    pass  # 已经设置过

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入应用模块
from ui.main_controller import MainWindow
from ui.message_box_helper import MessageBoxHelper

# 导入错误处理
from backend.error_handler import (
    setup_error_handler,
    check_startup_requirements,
    StartupError
)


# ==================== 全局变量 ====================

application = None
main_window = None
error_handler = None


# ==================== 日志配置 ====================

def setup_logging():
    """配置日志系统"""
    from backend.path_manager import PathManager

    path_manager = PathManager()
    log_dir = path_manager.get_log_path()
    log_file = Path(log_dir) / "cosyvoice_app.log"

    # 移除默认处理器
    logger.remove()

    # 添加控制台处理器（带颜色）
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )

    # 添加文件处理器（按天轮转）
    logger.add(
        log_file,
        rotation="1 day",
        retention="7 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG"
    )

    logger.info("=" * 60)
    logger.info("CosyVoice_app 启动")
    logger.info(f"日志文件: {log_file}")
    logger.info("=" * 60)


# ==================== 启动检查 ====================

def perform_startup_checks():
    """执行启动检查"""
    logger.info("执行启动检查...")

    # 检查必需的条件
    errors = check_startup_requirements()

    if errors:
        logger.error("启动检查失败!")
        for error in errors:
            logger.error(f"  - {error}")

        # 显示错误对话框
        from PyQt6.QtWidgets import QMessageBox
        app = QApplication.instance()
        if app:
            msg = "启动检查失败，请检查以下问题:\n\n"
            for error in errors:
                msg += f"{error.message}\n"
                if error.recovery_hint:
                    msg += f"   {error.recovery_hint}\n"

            MessageBoxHelper.critical(None, "启动失败", msg)

        sys.exit(1)

    logger.info("启动检查通过")


# ==================== 优雅退出 ====================

def setup_signal_handlers():
    """设置信号处理器"""
    def signal_handler(signum, frame):
        """信号处理函数"""
        logger.info(f"收到信号 {signum}，准备退出...")
        cleanup_and_exit(0)

    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("信号处理器已配置")


def cleanup_and_exit(exit_code: int = 0):
    """清理资源并退出"""
    logger.info("开始清理资源...")

    try:
        # 清理主窗口
        if main_window:
            try:
                # 清理音频播放器
                if hasattr(main_window, 'audio_player'):
                    main_window.audio_player.cleanup()

                # 清理音频克隆面板
                if hasattr(main_window, 'audio_clone_panel'):
                    main_window.audio_clone_panel.cleanup()

                # 清理模型下载面板
                if hasattr(main_window, 'model_download_panel'):
                    if hasattr(main_window.model_download_panel, 'cleanup'):
                        main_window.model_download_panel.cleanup()

                # 清理Status面板
                if hasattr(main_window, 'status_panel'):
                    main_window.status_panel.cleanup()

                logger.info("主窗口资源已清理")
            except Exception as e:
                logger.error(f"清理主窗口失败: {e}")

        # 清理配置管理器
        try:
            from backend.config_manager import get_config_manager
            config_mgr = get_config_manager()
            config_mgr.save_user_config()
            logger.info("配置已保存")
        except Exception as e:
            logger.warning(f"保存配置失败: {e}")

        logger.info("资源清理完成")

    except Exception as e:
        logger.error(f"清理过程出错: {e}")

    logger.info("程序退出")
    sys.exit(exit_code)


# ==================== 性能监控 ====================

def setup_performance_monitoring():
    """设置性能监控"""
    try:
        import psutil

        # 记录系统信息
        logger.info("=" * 40)
        logger.info("系统信息:")
        logger.info(f"  CPU 核心数: {psutil.cpu_count()}")
        logger.info(f"  总内存: {psutil.virtual_memory().total / (1024**3):.2f} GB")
        logger.info(f"  可用内存: {psutil.virtual_memory().available / (1024**3):.2f} GB")

        # GPU 信息
        try:
            import torch
            if torch.cuda.is_available():
                logger.info(f"  GPU: {torch.cuda.get_device_name(0)}")
                logger.info(f"  GPU 内存: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                logger.info("  GPU: Apple MPS (Metal)")
            else:
                logger.info("  GPU: 未检测到，使用CPU模式")
        except ImportError:
            logger.warning("无法检测GPU信息（PyTorch未安装）")

        logger.info("=" * 40)

    except ImportError:
        logger.warning("psutil未安装，跳过性能监控")
    except Exception as e:
        logger.warning(f"性能监控初始化失败: {e}")


# ==================== 主函数 ====================

def main():
    """主函数"""
    global application, main_window, error_handler

    try:
        # 1. 配置日志
        setup_logging()

        # 2. 设置信号处理器
        setup_signal_handlers()

        # 3. 执行启动检查
        perform_startup_checks()

        # 4. 创建应用实例
        logger.info("创建应用实例...")
        application = QApplication(sys.argv)

        # 设置应用信息
        application.setApplicationName("CosyVoice_app")
        application.setApplicationVersion("1.0.0")
        application.setOrganizationName("CosyVoice")

        # 设置应用图标（跨平台）
        from PyQt6.QtGui import QIcon

        icon_path = None
        if sys.platform == 'darwin':  # macOS
            # macOS优先使用icns格式（系统原生格式，无边框效果）
            icon_path = PROJECT_ROOT / "resources" / "icons" / "app_icon.icns"
            if not icon_path.exists():
                icon_path = PROJECT_ROOT / "resources" / "icons" / "app_icon.png"
        elif sys.platform == 'win32':  # Windows
            # Windows优先使用ico格式
            icon_path = PROJECT_ROOT / "resources" / "icons" / "app_icon.ico"
            if not icon_path.exists():
                icon_path = PROJECT_ROOT / "resources" / "icons" / "app_icon.png"
        else:  # Linux和其他平台
            icon_path = PROJECT_ROOT / "resources" / "icons" / "app_icon.png"

        if icon_path.exists():
            application.setWindowIcon(QIcon(str(icon_path)))
            logger.info(f"应用图标已设置: {icon_path} (平台: {sys.platform})")
        else:
            logger.warning(f"应用图标不存在: {icon_path}")

        # 设置应用样式
        application.setStyle("Fusion")

        # 5. 设置错误处理器
        error_handler = setup_error_handler()

        # 6. 性能监控
        setup_performance_monitoring()

        # 7. 加载配置
        try:
            from backend.config_manager import get_config_manager
            config_mgr = get_config_manager()
            config = config_mgr.get_config()
            logger.info(f"配置加载完成: 默认模型={config.default_model}, 设备={config.device}")
        except Exception as e:
            logger.warning(f"配置加载失败，使用默认配置: {e}")

        # 8. 创建主窗口（在后台）
        logger.info("创建主窗口...")
        main_window = MainWindow()

        # 设置错误处理器的父窗口
        error_handler.set_parent_widget(main_window)

        # 9. 显示启动页面
        logger.info("显示启动页面...")
        from ui.splash_controller import SplashScreen
        splash = SplashScreen()

        # 当启动页面完成时，显示主窗口
        splash.finished.connect(
            lambda: (
                logger.info("启动页面完成，显示主窗口..."),
                main_window.show(),
                main_window.raise_(),
                main_window.activateWindow(),
                logger.info("主窗口已显示")
            )
        )

        # 启动倒计时
        splash.start()

        # 记录应用启动
        try:
            from backend.statistics_service import get_statistics_service
            stats_service = get_statistics_service()
            stats_service.record_launch()
            logger.info("应用启动已记录")
        except Exception as e:
            logger.warning(f"记录应用启动失败: {e}")

        # 确保窗口在屏幕中央
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = main_window.geometry()
            x = (screen_geometry.width() - window_geometry.width()) // 2
            y = (screen_geometry.height() - window_geometry.height()) // 2
            main_window.move(x, y)

        # 10. 打印启动信息
        logger.info("=" * 60)
        logger.info("CosyVoice_app 启动完成!")
        logger.info("=" * 60)
        logger.info("=" * 60)

        # 11. 进入事件循环
        logger.info("进入事件循环...")
        exit_code = application.exec()

        # 12. 清理并退出
        logger.info(f"应用退出，退出码: {exit_code}")
        cleanup_and_exit(exit_code)

    except StartupError as e:
        logger.critical(f"启动失败: {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("用户中断")
        cleanup_and_exit(0)

    except Exception as e:
        logger.exception("未捕获的异常!")
        cleanup_and_exit(1)


if __name__ == "__main__":
    main()