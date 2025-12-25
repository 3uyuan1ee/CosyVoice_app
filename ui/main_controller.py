"""
主窗口控制器
"""
from PyQt6.QtWidgets import QMainWindow
from ui.message_box_helper import MessageBoxHelper
from PyQt6.uic import loadUi
import os
from loguru import logger


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
        self.setWindowTitle("CosyVoice_app")
        self.statusBar().showMessage("Ready", 3000)

    def connect_signals(self):
        """连接信号和槽"""
        self.btnAudioClone.clicked.connect(self.show_audio_clone)
        self.btnModelDownload.clicked.connect(self.show_model_download)
        self.btnResults.clicked.connect(self.show_results)
        self.btnStatus.clicked.connect(self.show_status)
        self.btnSettings.clicked.connect(self.show_settings)

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

                # 连接生成完成信号
                self.audio_clone_panel.generation_completed.connect(self._on_audio_generated)

                layout.addWidget(self.audio_clone_panel)

            # 切换到音频克隆页面
            self.stackedWidget.setCurrentIndex(1)
            self.statusBar().showMessage("Audio_Clone", 3000)

        except Exception as e:
            MessageBoxHelper.critical(self, "Error", f"Fail to load clone interface：{str(e)}")

    def _on_audio_generated(self, file_path: str, model_id: str, text: str):
        """音频生成完成时的处理"""
        try:
            # 计算音频时长
            duration = 0.0
            try:
                import librosa
                audio, sr = librosa.load(file_path, sr=None)
                duration = float(librosa.get_duration(y=audio, sr=sr))
            except Exception as e:
                logger.warning(f"Failed to calculate audio duration: {e}")

            # 记录音频生成统计
            try:
                from backend.statistics_service import get_statistics_service
                stats_service = get_statistics_service()
                stats_service.record_audio_generation(duration, model_id)
                logger.info(f"Audio generation recorded: {duration:.1f}s, model={model_id}")
            except Exception as e:
                logger.warning(f"Failed to record audio generation: {e}")

            # 确保结果面板已加载
            if not hasattr(self, 'result_panel'):
                from ui.result_controller import ResultPanel
                # 清空占位符布局
                layout = self.resultsPage.layout()
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.setParent(None)

                # 创建结果面板
                self.result_panel = ResultPanel()
                layout.addWidget(self.result_panel)

            # 添加生成的文件到结果面板
            self.result_panel.add_generated_file(file_path, model_id, text)

            # 显示提示消息
            self.statusBar().showMessage("Check cloned audio in result interface", 5000)

        except Exception as e:
            logger.error(f"Error handling audio generation: {e}")

    def show_results(self):
        """显示结果页面"""
        try:
            from ui.result_controller import ResultPanel
            # 如果还没加载结果面板
            if not hasattr(self, 'result_panel'):
                # 清空占位符布局
                layout = self.resultsPage.layout()
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.setParent(None)

                # 创建结果面板
                self.result_panel = ResultPanel()
                layout.addWidget(self.result_panel)

            # 切换到结果页面
            self.stackedWidget.setCurrentIndex(3)
            self.statusBar().showMessage("Result interface", 3000)

        except Exception as e:
            MessageBoxHelper.critical(self, "Error", f"Fail to load result interface：{str(e)}")

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
            self.statusBar().showMessage("Model download", 3000)

        except Exception as e:
            MessageBoxHelper.critical(self, "Error", f"Fail to load download interface：{str(e)}")

    def show_status(self):
        """显示Status页面"""
        try:
            from ui.status_controller import StatusPanel
            # 如果还没加载Status面板
            if not hasattr(self, 'status_panel'):
                # 清空占位符布局
                layout = self.statusPage.layout()
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.setParent(None)

                # 创建Status面板
                self.status_panel = StatusPanel()
                layout.addWidget(self.status_panel)

            # 切换到Status页面
            self.stackedWidget.setCurrentIndex(4)
            self.statusBar().showMessage("System Status", 3000)

        except Exception as e:
            MessageBoxHelper.critical(self, "Error", f"Fail to load status interface：{str(e)}")

    def show_settings(self):
        """显示Settings页面"""
        try:
            from ui.settings_controller import SettingsPanel
            # 如果还没加载Settings面板
            if not hasattr(self, 'settings_panel'):
                # 清空占位符布局
                layout = self.settingsPage.layout()
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.setParent(None)

                # 创建Settings面板
                self.settings_panel = SettingsPanel()
                layout.addWidget(self.settings_panel)

            # 切换到Settings页面
            self.stackedWidget.setCurrentIndex(5)
            self.statusBar().showMessage("Settings", 3000)

        except Exception as e:
            MessageBoxHelper.critical(self, "Error", f"Fail to load settings interface：{str(e)}")