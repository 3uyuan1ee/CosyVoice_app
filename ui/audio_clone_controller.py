"""
音频克隆面板控制器
"""
from PyQt6.QtWidgets import QWidget, QFileDialog, QMessageBox, QApplication
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.uic import loadUi
import os


class AudioClonePanel(QWidget):
    """音频克隆面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # 加载 UI 文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, 'audio_clone.ui')
        loadUi(ui_path, self)

        # 状态变量
        self.ref_audio_path = None
        self.generated_audio_path = None
        self.worker = None

        # 连接信号
        self.connect_signals()

    def connect_signals(self):
        """连接信号和槽"""
        self.btnSelectRefAudio.clicked.connect(self.select_reference_audio)
        self.btnGenerate.clicked.connect(self.generate_audio)
        self.btnPlay.clicked.connect(self.play_audio)
        self.btnSave.clicked.connect(self.save_audio)
        self.pitchSlider.valueChanged.connect(self.update_pitch_value)
        self.textInput.textChanged.connect(self.update_generate_button)

    def select_reference_audio(self):
        """选择参考音频"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择参考音频",
            "",
            "Audio Files (*.wav *.mp3 *.flac);;All Files (*)"
        )

        if file_path:
            self.ref_audio_path = file_path
            self.refAudioPath.setText(file_path)
            self.update_generate_button()

    def update_pitch_value(self, value):
        """更新音调显示值"""
        self.pitchValue.setText(str(value))

    def update_generate_button(self):
        """更新生成按钮状态"""
        has_text = bool(self.textInput.toPlainText().strip())
        has_ref_audio = bool(self.ref_audio_path)

        self.btnGenerate.setEnabled(has_text and has_ref_audio)

    def generate_audio(self):
        """生成音频"""
        if not self.ref_audio_path:
            QMessageBox.warning(self, "警告", "请先选择参考音频！")
            return

        text = self.textInput.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请输入要合成的文本！")
            return

        # 禁用按钮
        self.btnGenerate.setEnabled(False)
        self.progressBar.setValue(0)

        try:
            # TODO: 这里调用实际的语音生成代码
            # from backend.voice_generator import get_voice_service
            # voice_service = get_voice_service()

            # 模拟生成过程
            import time
            for i in range(101):
                self.progressBar.setValue(i)
                QApplication.processEvents()  # 更新界面
                time.sleep(0.02)

            # 生成完成（示例路径）
            self.generated_audio_path = "/path/to/generated/audio.wav"
            self.btnPlay.setEnabled(True)
            self.btnSave.setEnabled(True)

            QMessageBox.information(self, "成功", "音频生成成功！")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成失败：{str(e)}")
        finally:
            self.btnGenerate.setEnabled(True)

    def play_audio(self):
        """播放音频"""
        if self.generated_audio_path:
            # TODO: 实现音频播放
            QMessageBox.information(self, "提示", "播放功能待实现")

    def save_audio(self):
        """保存音频"""
        if self.generated_audio_path:
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存音频",
                self.generated_audio_path,
                "Audio Files (*.wav *.mp3)"
            )
            if save_path:
                # TODO: 实现保存功能
                QMessageBox.information(self, "提示", f"保存到：{save_path}")