"""
启动页面控制器 - 显示封面并延迟后进入主界面
"""

from PyQt6.QtWidgets import QWidget, QSplashScreen
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.uic import loadUi
import os
from loguru import logger
from pathlib import Path


class SplashScreen(QWidget):
    """启动页面 - 显示封面并延迟进入主界面"""

    # 信号：启动页面完成
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # 版本和作者信息
        self.version = "1.0.0"
        self.author = "@3uyuan1ee"

        # 封面图片路径
        self.cover_path = None

        # 初始化UI
        self._init_ui()
        self._load_cover()

        # 设置定时器（3秒后自动关闭）
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timeout)
        self.timer.setSingleShot(True)

        logger.info("SplashScreen initialized")

    def _init_ui(self):
        """初始化UI"""
        # 加载UI文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, 'splash.ui')
        loadUi(ui_path, self)

        # 设置版本和作者信息
        self.versionLabel.setText(f"Version {self.version}")
        self.authorLabel.setText(self.author)

        # 窗口属性
        self.setWindowFlags(
            Qt.WindowType.SplashScreen |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        # 设置窗口大小
        self.setFixedSize(400, 240)

    def _load_cover(self):
        """加载封面图片"""
        try:
            # 尝试从resources/icons/cover.png加载
            project_root = Path(__file__).parent.parent
            cover_path = project_root / "resources" / "icons" / "cover.png"

            if cover_path.exists():
                # 加载图片并设置到label
                pixmap = QPixmap(str(cover_path))
                if not pixmap.isNull():
                    # 缩放图片以适应400x216（240-24底部信息栏）
                    scaled_pixmap = pixmap.scaled(
                        400,
                        216,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.coverLabel.setPixmap(scaled_pixmap)
                    self.coverLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    logger.info(f"封面图片加载成功: {cover_path}")
                else:
                    logger.warning(f"封面图片加载失败: {cover_path}")
                    self._set_default_cover()
            else:
                logger.warning(f"封面图片不存在: {cover_path}")
                self._set_default_cover()

        except Exception as e:
            logger.error(f"加载封面图片时出错: {e}")
            self._set_default_cover()

    def _set_default_cover(self):
        """设置默认封面（纯色背景）"""
        self.coverLabel.setText("")
        self.coverLabel.setStyleSheet("""
            QLabel#coverLabel {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1412, stop:1 #2a1d19
                );
                border: none;
            }
        """)

    def start(self):
        """启动倒计时"""
        logger.info("启动页面显示，3秒后进入主界面")
        self.show()
        self.center_on_screen()
        self.timer.start(3000)  # 3秒

    def center_on_screen(self):
        """将窗口居中显示"""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.geometry()
            x = (screen_geometry.width() - window_geometry.width()) // 2
            y = (screen_geometry.height() - window_geometry.height()) // 2
            self.move(x, y)

    def _on_timeout(self):
        """定时器超时处理"""
        logger.info("启动页面倒计时结束")
        self.finished.emit()
        self.close()

    def closeEvent(self, event):
        """关闭事件处理"""
        if self.timer.isActive():
            self.timer.stop()
        event.accept()

    def cleanup(self):
        """清理资源"""
        if self.timer.isActive():
            self.timer.stop()
        logger.info("SplashScreen cleanup completed")
