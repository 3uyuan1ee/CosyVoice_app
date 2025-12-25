"""
音频克隆面板控制器 - 连接所有后端服务
"""

from PyQt6.QtWidgets import (QWidget, QFileDialog, QMessageBox,
                             QApplication, QStyle)
from PyQt6.QtCore import QThread, pyqtSlot, Qt, pyqtSignal
from PyQt6.uic import loadUi
import os
from loguru import logger
from typing import Optional

from ui.audio_generation_worker import AudioGenerationWorker
from backend.file_service import get_file_service
from backend.path_manager import PathManager
from backend.model_download_service import get_model_download_service, ModelDownloadStatus


class AudioClonePanel(QWidget):
    """音频克隆面板控制器"""

    # 定义信号：生成完成时通知
    generation_completed = pyqtSignal(str, str, str)  # file_path, model_id, text

    def __init__(self, parent=None):
        super().__init__(parent)

        # 加载UI文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, 'audio_clone.ui')
        loadUi(ui_path, self)

        # 服务层
        self.file_service = get_file_service()
        self.path_manager = PathManager()
        self.model_download_service = get_model_download_service()

        # 设置 path_manager 到 download_service（关键！）
        self.model_download_service.set_path_manager(self.path_manager)

        # 状态变量
        self.ref_audio_path: Optional[str] = None
        self.generated_audio_path: Optional[str] = None
        self.generation_worker: Optional[AudioGenerationWorker] = None

        # 音调调整值
        self.pitch_value = 0

        # 选中的模型
        self.selected_model_id: Optional[str] = None

        # 初始化模型选择
        self._init_model_selection()

        # 连接UI信号
        self.connect_signals()

        # 初始化按钮状态
        self.update_generate_button()

        logger.info("AudioClonePanel initialized")

    def _init_model_selection(self):
        """初始化模型选择下拉框"""
        try:
            available_models = self.model_download_service.get_available_models()

            # 清空下拉框
            self.modelComboBox.clear()

            # 添加模型到下拉框
            for model in available_models:
                self.modelComboBox.addItem(model.name, model.id)

            # 默认选择第一个已下载的模型
            for i, model in enumerate(available_models):
                status = self.model_download_service.check_model_status(model.id)
                if status == ModelDownloadStatus.DOWNLOADED:
                    self.modelComboBox.setCurrentIndex(i)
                    self.selected_model_id = model.id
                    logger.info(f"Selected default model: {model.name}")
                    break

            # 如果没有已下载的模型，选择第一个
            if self.selected_model_id is None and available_models:
                self.selected_model_id = available_models[0].id

            # 连接信号
            self.modelComboBox.currentIndexChanged.connect(self._on_model_changed)

            logger.info(f"Model selection initialized with {len(available_models)} models")
            logger.info(f"Selected model: {self.selected_model_id}")

            # 初始化完成后更新按钮状态
            self.update_generate_button()

        except Exception as e:
            logger.error(f"Error initializing model selection: {e}")

    def _on_model_changed(self, index: int):
        """模型选择变化"""
        try:
            if index >= 0:
                model_id = self.modelComboBox.itemData(index)
                self.selected_model_id = model_id
                logger.info(f"Model changed to: {model_id}")

                # 更新生成按钮状态
                self.update_generate_button()

        except Exception as e:
            logger.error(f"Error on model changed: {e}")

    def connect_signals(self):
        """连接UI信号和槽"""
        # 文件选择
        self.btnSelectRefAudio.clicked.connect(self.select_reference_audio)

        # 生成控制
        self.btnGenerate.clicked.connect(self.generate_audio)

        # 音调调整
        self.pitchSlider.valueChanged.connect(self.update_pitch_value)

        # 文本输入
        self.textInput.textChanged.connect(self.update_generate_button)

    def select_reference_audio(self):
        """选择参考音频文件"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Reference Audio",
                "",
                "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a);;All Files (*)"
            )

            if file_path:
                # 验证文件
                if not os.path.exists(file_path):
                    QMessageBox.warning(self, "Warning", "File does not exist")
                    return

                # 更新状态
                self.ref_audio_path = file_path
                self.refAudioPath.setText(file_path)

                # 启用生成按钮
                self.update_generate_button()

                logger.info(f"Reference audio selected: {file_path}")

        except Exception as e:
            logger.error(f"Error selecting reference audio: {e}")
            QMessageBox.critical(self, "Error", f"Failed to select audio: {str(e)}")

    def update_pitch_value(self, value):
        """更新音调显示值"""
        self.pitch_value = value
        self.pitchValue.setText(str(value))
        logger.debug(f"Pitch value: {value}")

    def update_generate_button(self):
        """更新生成按钮状态"""
        has_text = bool(self.textInput.toPlainText().strip())
        has_ref_audio = bool(self.ref_audio_path)
        has_model = bool(self.selected_model_id)
        is_not_generating = (self.generation_worker is None or
                             not self.generation_worker.isRunning())

        # 检查选中的模型是否已下载
        model_available = False
        model_status = None
        if has_model:
            try:
                model_status = self.model_download_service.check_model_status(self.selected_model_id)
                model_available = (model_status == ModelDownloadStatus.DOWNLOADED)
                logger.info(f"[Button Check] Model: {self.selected_model_id}, Status: {model_status}, Available: {model_available}")

                # 额外诊断：检查模型路径
                if self.model_download_service._path_manager:
                    path_methods = {
                        "cosyvoice3_2512": self.model_download_service._path_manager.get_cosyvoice3_2512_model_path,
                        "cosyvoice2": self.model_download_service._path_manager.get_cosyvoice2_model_path,
                        "cosyvoice_300m": self.model_download_service._path_manager.get_cosyvoice_300m_model_path,
                        "cosyvoice_300m_sft": self.model_download_service._path_manager.get_cosyvoice_300m_sft_model_path,
                        "cosyvoice_300m_instruct": self.model_download_service._path_manager.get_cosyvoice_300m_instruct_model_path,
                        "cosyvoice_ttsfrd": self.model_download_service._path_manager.get_cosyvoice_ttsfrd_model_path,
                    }
                    path_method = path_methods.get(self.selected_model_id)
                    if path_method:
                        model_path = path_method()
                        import os
                        exists = os.path.exists(model_path)
                        logger.info(f"[Button Check] Model path: {model_path}, Exists: {exists}")
            except Exception as e:
                logger.error(f"[Button Check] Error checking model status: {e}")

        # 启用生成按钮
        should_enable = has_text and has_ref_audio and has_model and model_available and is_not_generating
        self.btnGenerate.setEnabled(should_enable)

        # 记录状态
        logger.info(f"[Button Check] Text: {has_text}, Audio: {has_ref_audio}, Model: {has_model}, Available: {model_available}, NotGenerating: {is_not_generating}")
        logger.info(f"[Button Check] Button enabled: {should_enable}")

        # 添加工具提示，说明为什么按钮不可用
        if not should_enable:
            reasons = []
            if not has_text:
                reasons.append("请输入要合成的文本")
            if not has_ref_audio:
                reasons.append("请选择参考音频文件")
            if not has_model:
                reasons.append("请选择模型")
            if has_model and not model_available:
                reasons.append(f"选择的模型未下载（当前状态: {model_status}），请先在模型下载页面下载")
            if not is_not_generating:
                reasons.append("正在生成音频，请等待")

            if reasons:
                tooltip = " | ".join(reasons)
                self.btnGenerate.setToolTip(tooltip)
                logger.info(f"[Button Check] Tooltip: {tooltip}")
            else:
                self.btnGenerate.setToolTip("")
        else:
            self.btnGenerate.setToolTip("点击开始生成音频")

    def generate_audio(self):
        """生成音频"""
        try:
            # 验证输入
            if not self.ref_audio_path:
                QMessageBox.warning(self, "Warning", "Please select reference audio first")
                return

            text = self.textInput.toPlainText().strip()
            if not text:
                QMessageBox.warning(self, "Warning", "Please enter text to synthesize")
                return

            if not self.selected_model_id:
                QMessageBox.warning(self, "Warning", "Please select a model")
                return

            # 检查模型是否已下载
            model_status = self.model_download_service.check_model_status(self.selected_model_id)
            if model_status != ModelDownloadStatus.DOWNLOADED:
                QMessageBox.warning(self, "Warning", "Selected model is not downloaded. Please download it first.")
                return

            # 禁用生成按钮
            self.btnGenerate.setEnabled(False)
            self.progressBar.setValue(0)

            # 创建生成工作线程
            self.generation_worker = AudioGenerationWorker(
                reference_audio=self.ref_audio_path,
                text=text,
                pitch_shift=self.pitch_value,
                model_type=self.selected_model_id,
                parent=self
            )

            # 连接信号
            self.generation_worker.signals.progress.connect(self._on_generation_progress)
            self.generation_worker.signals.finished.connect(self._on_generation_finished)
            self.generation_worker.signals.error.connect(self._on_generation_error)
            self.generation_worker.signals.started.connect(self._on_generation_started)

            # 启动生成
            self.generation_worker.start()

            logger.info(f"Audio generation started with model: {self.selected_model_id}")

        except Exception as e:
            logger.error(f"Error starting audio generation: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start generation: {str(e)}")
            self.btnGenerate.setEnabled(True)

    @pyqtSlot()
    def _on_generation_started(self):
        """生成开始"""
        logger.info("Generation started signal received")
        # 更新UI状态
        self.btnGenerate.setText("GENERATING...")
        self.statusBar().showMessage("Generating audio...") if hasattr(self, 'statusBar') else None

    @pyqtSlot(int, str)
    def _on_generation_progress(self, percentage: int, status_text: str):
        """处理生成进度"""
        self.progressBar.setValue(percentage)
        logger.debug(f"Generation progress: {percentage}% - {status_text}")

        # 更新状态栏（如果可用）
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(f"{status_text} ({percentage}%)")

    @pyqtSlot(bool, str, str)
    def _on_generation_finished(self, success: bool, message: str, output_path: str):
        """处理生成完成"""
        # 恢复生成按钮
        self.btnGenerate.setEnabled(True)
        self.btnGenerate.setText("GENERATE")

        if success:
            self.generated_audio_path = output_path

            # 更新进度条
            self.progressBar.setValue(100)

            # 获取合成文本
            text = self.textInput.toPlainText().strip()

            # 发送生成完成信号
            self.generation_completed.emit(output_path, self.selected_model_id or "", text)

            # 显示成功消息
            QMessageBox.information(
                self,
                "Success",
                f"{message}\n\nThe file has been added to the Results page."
            )

            logger.info(f"Audio generation completed: {output_path}")
        else:
            # 显示失败消息
            QMessageBox.warning(self, "Generation Failed", message)
            logger.warning(f"Audio generation failed: {message}")

        # 清理工作线程
        if self.generation_worker:
            self.generation_worker.wait()
            self.generation_worker = None

    @pyqtSlot(str)
    def _on_generation_error(self, error_msg: str):
        """处理生成错误"""
        # 恢复UI状态
        self.btnGenerate.setEnabled(True)
        self.btnGenerate.setText("GENERATE")
        self.progressBar.setValue(0)

        # 显示错误消息
        QMessageBox.critical(self, "Generation Error", error_msg)

        logger.error(f"Generation error: {error_msg}")

        # 清理工作线程
        if self.generation_worker:
            self.generation_worker.wait()
            self.generation_worker = None

    def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up AudioClonePanel")

        # 停止生成任务
        if self.generation_worker and self.generation_worker.isRunning():
            self.generation_worker.cancel()
            self.generation_worker.wait()
