"""
音频克隆面板控制器 - 连接所有后端服务
"""

from PyQt6.QtWidgets import (QWidget, QFileDialog, QMessageBox,
                             QApplication, QStyle)
from PyQt6.QtCore import QThread, pyqtSlot, Qt
from PyQt6.uic import loadUi
from PyQt6.QtMultimedia import QMediaPlayer
import os
from loguru import logger
from typing import Optional

from ui.audio_generation_worker import AudioGenerationWorker
from backend.audio_player_service import get_audio_player_service
from backend.file_service import get_file_service
from backend.path_manager import PathManager


class AudioClonePanel(QWidget):
    """音频克隆面板控制器"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 加载UI文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, 'audio_clone.ui')
        loadUi(ui_path, self)

        # 服务层
        self.audio_player = get_audio_player_service()
        self.file_service = get_file_service()
        self.path_manager = PathManager()

        # 状态变量
        self.ref_audio_path: Optional[str] = None
        self.generated_audio_path: Optional[str] = None
        self.generation_worker: Optional[AudioGenerationWorker] = None
        self.is_playing: bool = False

        # 音调调整值
        self.pitch_value = 0

        # 连接音频播放器信号
        self._connect_player_signals()

        # 连接UI信号
        self.connect_signals()

        logger.info("AudioClonePanel initialized")

    def _connect_player_signals(self):
        """连接音频播放器信号"""
        self.audio_player.signals.position_changed.connect(self._on_playback_position_changed)
        self.audio_player.signals.duration_changed.connect(self._on_playback_duration_changed)
        self.audio_player.signals.playback_state_changed.connect(self._on_playback_state_changed)
        self.audio_player.signals.error_occurred.connect(self._on_playback_error)

    def connect_signals(self):
        """连接UI信号和槽"""
        # 文件选择
        self.btnSelectRefAudio.clicked.connect(self.select_reference_audio)

        # 生成控制
        self.btnGenerate.clicked.connect(self.generate_audio)

        # 播放控制
        self.btnPlay.clicked.connect(self.toggle_playback)

        # 保存控制
        self.btnSave.clicked.connect(self.save_audio)

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
        is_not_generating = (self.generation_worker is None or
                             not self.generation_worker.isRunning())

        self.btnGenerate.setEnabled(has_text and has_ref_audio and is_not_generating)

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

            # 禁用生成按钮
            self.btnGenerate.setEnabled(False)
            self.progressBar.setValue(0)
            self.btnPlay.setEnabled(False)
            self.btnSave.setEnabled(False)

            # 停止当前播放
            if self.is_playing:
                self.audio_player.stop()

            # 创建生成工作线程
            self.generation_worker = AudioGenerationWorker(
                reference_audio=self.ref_audio_path,
                text=text,
                pitch_shift=self.pitch_value,
                parent=self
            )

            # 连接信号
            self.generation_worker.signals.progress.connect(self._on_generation_progress)
            self.generation_worker.signals.finished.connect(self._on_generation_finished)
            self.generation_worker.signals.error.connect(self._on_generation_error)
            self.generation_worker.signals.started.connect(self._on_generation_started)

            # 启动生成
            self.generation_worker.start()

            logger.info("Audio generation started")

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

            # 启用播放和保存按钮
            self.btnPlay.setEnabled(True)
            self.btnSave.setEnabled(True)

            # 更新进度条
            self.progressBar.setValue(100)

            # 显示成功消息
            QMessageBox.information(self, "Success", message)

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

    def toggle_playback(self):
        """切换播放状态"""
        try:
            if not self.generated_audio_path:
                QMessageBox.warning(self, "Warning", "No audio to play")
                return

            if not os.path.exists(self.generated_audio_path):
                QMessageBox.warning(self, "Warning", "Generated audio file not found")
                return

            # 根据当前状态决定播放或暂停
            if self.is_playing and self.audio_player.get_current_file() == self.generated_audio_path:
                # 暂停
                self.audio_player.pause()
            else:
                # 加载并播放
                if self.audio_player.get_current_file() != self.generated_audio_path:
                    if not self.audio_player.load_file(self.generated_audio_path):
                        QMessageBox.critical(self, "Error", "Failed to load audio file")
                        return

                self.audio_player.play()

            logger.info(f"Playback toggled: current state = {self.is_playing}")

        except Exception as e:
            logger.error(f"Error toggling playback: {e}")
            QMessageBox.critical(self, "Error", f"Playback error: {str(e)}")

    def _on_playback_position_changed(self, position: int):
        """处理播放位置变化"""
        # 可以在这里更新进度条或其他UI元素
        pass

    def _on_playback_duration_changed(self, duration: int):
        """处理音频时长变化"""
        logger.debug(f"Audio duration: {duration}ms")

    def _on_playback_state_changed(self, state: str):
        """处理播放状态变化"""
        if state == "playing":
            self.is_playing = True
            # 设置暂停图标
            self.btnPlay.setText("PAUSE")
        else:
            self.is_playing = False
            # 设置播放图标
            self.btnPlay.setText("PLAY")

        logger.debug(f"Playback state: {state}")

    def _on_playback_error(self, error: str):
        """处理播放错误"""
        QMessageBox.warning(self, "Playback Error", error)
        self.is_playing = False
        self.btnPlay.setText("PLAY")

    def save_audio(self):
        """保存音频文件"""
        try:
            if not self.generated_audio_path:
                QMessageBox.warning(self, "Warning", "No audio to save")
                return

            if not os.path.exists(self.generated_audio_path):
                QMessageBox.warning(self, "Warning", "Generated audio file not found")
                return

            # 生成默认文件名
            base_name = os.path.basename(self.generated_audio_path)
            default_name = self.file_service.generate_unique_filename(base_name)

            # 显示保存对话框
            save_path = self.file_service.save_audio_file_dialog(
                parent=self,
                default_name=default_name
            )

            if save_path:
                # 保存文件
                success, message = self.file_service.save_file(
                    source_path=self.generated_audio_path,
                    target_path=save_path,
                    overwrite=False
                )

                if success:
                    QMessageBox.information(self, "Success", message)
                    logger.info(f"Audio saved to: {save_path}")
                else:
                    QMessageBox.warning(self, "Save Failed", message)
                    logger.warning(f"Failed to save audio: {message}")

        except Exception as e:
            logger.error(f"Error saving audio: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save audio: {str(e)}")

    def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up AudioClonePanel")

        # 停止播放
        self.audio_player.stop()

        # 停止生成任务
        if self.generation_worker and self.generation_worker.isRunning():
            self.generation_worker.cancel()
            self.generation_worker.wait()

        # 清理播放器资源
        self.audio_player.cleanup()
