"""
结果页面控制器 - 管理生成的音频文件
"""

from PyQt6.QtWidgets import (QWidget, QFileDialog, QMessageBox, QListWidgetItem)
from PyQt6.QtCore import pyqtSlot, Qt
from PyQt6.uic import loadUi
from PyQt6.QtGui import QIcon
import os
from loguru import logger
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from backend.audio_player_service import get_audio_player_service
from backend.file_service import get_file_service
from backend.path_manager import PathManager


@dataclass
class GeneratedFile:
    """生成的文件信息"""
    path: str
    name: str
    created_at: datetime
    model_used: str = ""
    text_used: str = ""

    def __str__(self):
        """用于在列表中显示"""
        time_str = self.created_at.strftime("%Y-%m-%d %H:%M")
        return f"{self.name} ({time_str})"


class ResultPanel(QWidget):
    """结果页面控制器"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 加载UI文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, 'result.ui')
        loadUi(ui_path, self)

        # 服务层
        self.audio_player = get_audio_player_service()
        self.file_service = get_file_service()
        self.path_manager = PathManager()

        # 状态变量
        self.generated_files: List[GeneratedFile] = []
        self.current_playing_path: Optional[str] = None
        self.is_playing: bool = False

        # 连接音频播放器信号
        self._connect_player_signals()

        # 连接UI信号
        self.connect_signals()

        # 加载已有的生成文件
        self._load_existing_files()

        logger.info("ResultPanel initialized")

    def _connect_player_signals(self):
        """连接音频播放器信号"""
        self.audio_player.signals.playback_state_changed.connect(self._on_playback_state_changed)
        self.audio_player.signals.error_occurred.connect(self._on_playback_error)

    def connect_signals(self):
        """连接UI信号和槽"""
        # 列表选择变化
        self.resultsList.itemSelectionChanged.connect(self._on_selection_changed)

        # 双击播放
        self.resultsList.itemDoubleClicked.connect(self._on_item_double_clicked)

        # 按钮操作
        self.btnPlay.clicked.connect(self.toggle_playback)
        self.btnSave.clicked.connect(self.save_selected_audio)
        self.btnDelete.clicked.connect(self.delete_selected_audio)

    def _load_existing_files(self):
        """加载输出目录中已存在的文件"""
        try:
            # 使用生成的音频路径
            output_dir = self.path_manager.get_res_voice_path()

            if not os.path.exists(output_dir):
                logger.info(f"Output directory does not exist: {output_dir}")
                return

            # 扫描输出目录中的音频文件
            audio_extensions = {'.wav', '.mp3', '.flac', '.ogg', '.m4a'}
            files = []

            for filename in os.listdir(output_dir):
                file_path = os.path.join(output_dir, filename)
                if os.path.isfile(file_path):
                    _, ext = os.path.splitext(filename)
                    if ext.lower() in audio_extensions:
                        # 获取文件创建时间
                        created_at = datetime.fromtimestamp(os.path.getctime(file_path))

                        gen_file = GeneratedFile(
                            path=file_path,
                            name=filename,
                            created_at=created_at
                        )
                        files.append(gen_file)

            # 按创建时间倒序排列
            files.sort(key=lambda x: x.created_at, reverse=True)

            # 添加到列表
            for gen_file in files:
                self._add_file_to_list(gen_file)

            logger.info(f"Loaded {len(files)} existing files from output directory")

        except Exception as e:
            logger.error(f"Error loading existing files: {e}")

    def _add_file_to_list(self, gen_file: GeneratedFile):
        """添加文件到列表"""
        try:
            # 创建列表项
            item = QListWidgetItem(str(gen_file))
            item.setData(Qt.ItemDataRole.UserRole, gen_file)

            # 添加到列表顶部
            self.resultsList.insertItem(0, item)

            # 添加到内部列表
            self.generated_files.insert(0, gen_file)

            logger.info(f"Added file to results list: {gen_file.name}")

        except Exception as e:
            logger.error(f"Error adding file to list: {e}")

    def add_generated_file(self, file_path: str, model_used: str = "", text_used: str = ""):
        """添加新生成的文件到结果列表

        Args:
            file_path: 生成的文件路径
            model_used: 使用的模型
            text_used: 合成的文本
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                return

            # 获取文件名
            filename = os.path.basename(file_path)

            # 创建 GeneratedFile 对象
            gen_file = GeneratedFile(
                path=file_path,
                name=filename,
                created_at=datetime.now(),
                model_used=model_used,
                text_used=text_used
            )

            # 添加到列表
            self._add_file_to_list(gen_file)

            # 选中新添加的项
            self.resultsList.setCurrentRow(0)

            logger.info(f"Added generated file: {file_path}")

        except Exception as e:
            logger.error(f"Error adding generated file: {e}")

    def _on_selection_changed(self):
        """处理列表选择变化"""
        has_selection = len(self.resultsList.selectedItems()) > 0

        # 更新按钮状态
        self.btnPlay.setEnabled(has_selection)
        self.btnSave.setEnabled(has_selection)
        self.btnDelete.setEnabled(has_selection)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击播放"""
        self.toggle_playback()

    def get_selected_file(self) -> Optional[GeneratedFile]:
        """获取当前选中的文件"""
        selected_items = self.resultsList.selectedItems()

        if not selected_items:
            return None

        item = selected_items[0]
        gen_file = item.data(Qt.ItemDataRole.UserRole)

        return gen_file

    def toggle_playback(self):
        """切换播放状态"""
        try:
            gen_file = self.get_selected_file()

            if not gen_file:
                QMessageBox.warning(self, "Warning", "Please select a file to play")
                return

            if not os.path.exists(gen_file.path):
                QMessageBox.warning(self, "Warning", f"File not found: {gen_file.name}")
                return

            # 根据当前状态决定播放或暂停
            if self.is_playing and self.audio_player.get_current_file() == gen_file.path:
                # 暂停
                self.audio_player.pause()
            else:
                # 加载并播放
                if self.audio_player.get_current_file() != gen_file.path:
                    if not self.audio_player.load_file(gen_file.path):
                        QMessageBox.critical(self, "Error", "Failed to load audio file")
                        return

                self.audio_player.play()
                self.current_playing_path = gen_file.path

            logger.info(f"Playback toggled for: {gen_file.name}")

        except Exception as e:
            logger.error(f"Error toggling playback: {e}")
            QMessageBox.critical(self, "Error", f"Playback error: {str(e)}")

    def _on_playback_state_changed(self, state: str):
        """处理播放状态变化"""
        if state == "playing":
            self.is_playing = True
            self.btnPlay.setText("PAUSE")
        else:
            self.is_playing = False
            self.btnPlay.setText("PLAY")

        logger.debug(f"Playback state: {state}")

    def _on_playback_error(self, error: str):
        """处理播放错误"""
        QMessageBox.warning(self, "Playback Error", error)
        self.is_playing = False
        self.btnPlay.setText("PLAY")

    def save_selected_audio(self):
        """保存选中的音频文件"""
        try:
            gen_file = self.get_selected_file()

            if not gen_file:
                QMessageBox.warning(self, "Warning", "Please select a file to save")
                return

            if not os.path.exists(gen_file.path):
                QMessageBox.warning(self, "Warning", f"File not found: {gen_file.name}")
                return

            # 生成默认文件名
            default_name = self.file_service.generate_unique_filename(gen_file.name)

            # 显示保存对话框
            save_path = self.file_service.save_audio_file_dialog(
                parent=self,
                default_name=default_name
            )

            if save_path:
                # 保存文件
                success, message = self.file_service.save_file(
                    source_path=gen_file.path,
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

    def delete_selected_audio(self):
        """删除选中的音频文件"""
        try:
            gen_file = self.get_selected_file()

            if not gen_file:
                QMessageBox.warning(self, "Warning", "Please select a file to delete")
                return

            # 确认删除
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to delete:\n{gen_file.name}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 从文件系统删除
                if os.path.exists(gen_file.path):
                    try:
                        os.remove(gen_file.path)
                        logger.info(f"Deleted file: {gen_file.path}")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to delete file: {str(e)}")
                        logger.error(f"Error deleting file: {e}")
                        return

                # 停止当前播放（如果正在播放该文件）
                if self.is_playing and self.audio_player.get_current_file() == gen_file.path:
                    self.audio_player.stop()
                    self.current_playing_path = None

                # 从列表中移除
                current_row = self.resultsList.currentRow()
                self.resultsList.takeItem(current_row)
                self.generated_files.pop(current_row)

                logger.info(f"Removed file from list: {gen_file.name}")

        except Exception as e:
            logger.error(f"Error deleting audio: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete audio: {str(e)}")

    def refresh_list(self):
        """刷新文件列表"""
        try:
            # 清空当前列表
            self.resultsList.clear()
            self.generated_files.clear()

            # 重新加载文件
            self._load_existing_files()

            logger.info("File list refreshed")

        except Exception as e:
            logger.error(f"Error refreshing list: {e}")

    def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up ResultPanel")

        # 停止播放
        self.audio_player.stop()

        # 清理播放器资源
        self.audio_player.cleanup()
