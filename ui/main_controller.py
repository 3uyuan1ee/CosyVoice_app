"""
主窗口控制器
"""
from PyQt6.QtWidgets import QMainWindow, QMessageBox
from PyQt6.uic import loadUi
import os


class MainWindow(QMainWindow):
    """主窗口控制器"""

    def __init__(self):
        super().__init__()
        try:
            # 加载 UI 文件
            current_dir = os.path.dirname(os.path.abspath(__file__))
            ui_path = os.path.join(current_dir, 'main_window.ui')
            loadUi(ui_path, self)

            # 初始化
            self.init_ui()
            self.connect_signals()

        except Exception as e:
            print(f"[ERROR] 主窗口初始化失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("CosyVoice_app - 语音合成系统")
        self.statusBar().showMessage("就绪", 3000)

    def connect_signals(self):
        """连接信号和槽"""
        self.btnAudioClone.clicked.connect(self.show_audio_clone)
        self.btnModelDownload.clicked.connect(self.show_model_download)

    def show_audio_clone(self):
        """显示音频克隆页面"""
        try:
            from ui.audio_clone_controller import AudioClonePanel
            # 如果还没加载音频克隆面板
            if not hasattr(self, 'audio_clone_panel'):
                # 清空占位符布局
                layout = self.audioClonePage.layout()
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.setParent(None)

                # 创建音频克隆面板
                self.audio_clone_panel = AudioClonePanel()
                layout.addWidget(self.audio_clone_panel)

            # 切换到音频克隆页面
            self.stackedWidget.setCurrentIndex(1)
            self.statusBar().showMessage("音频克隆功能", 3000)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载音频克隆面板失败：{str(e)}")

    def show_model_download(self):
        """显示模型下载页面"""
        try:
            from ui.model_download_controller import ModelDownloadController
            # 如果还没加载模型下载面板
            if not hasattr(self, 'model_download_panel'):
                # 清空占位符布局
                layout = self.modelDownloadPage.layout()
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.setParent(None)

                # 创建模型下载面板
                self.model_download_panel = ModelDownloadController()
                layout.addWidget(self.model_download_panel)

            # 切换到模型下载页面
            self.stackedWidget.setCurrentIndex(2)
            self.statusBar().showMessage("模型下载", 3000)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载模型下载面板失败：{str(e)}")