"""
文件服务 - 提供统一的文件保存和管理接口
"""

from typing import Optional, Tuple
from PyQt6.QtWidgets import QFileDialog, QWidget
from loguru import logger
import os
import shutil
from datetime import datetime

from backend.path_manager import PathManager


class FileService:
    """
    文件服务

    提供：
    - 文件保存对话框
    - 文件复制和移动
    - 默认路径管理
    - 文件名生成
    """

    _instance: Optional['FileService'] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 避免重复初始化
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.path_manager = PathManager()

        # 默认保存目录
        self.default_save_dir = self.path_manager.get_res_voice_path()

        logger.info("FileService initialized")

    def save_audio_file_dialog(self, parent: QWidget, default_name: str = "",
                               file_filter: str = None) -> Optional[str]:
        """
        显示保存音频文件对话框

        Args:
            parent: 父窗口
            default_name: 默认文件名
            file_filter: 文件过滤器

        Returns:
            选择的文件路径，取消则返回None
        """
        try:
            if file_filter is None:
                file_filter = "Audio Files (*.wav *.mp3 *.m4a *.flac *.ogg);;All Files (*)"

            # 生成默认文件名
            if not default_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                default_name = f"voice_{timestamp}.wav"

            # 确保扩展名是.wav
            if not default_name.endswith('.wav'):
                default_name = os.path.splitext(default_name)[0] + '.wav'

            # 确保保存目录存在
            self.path_manager.ensure_directory(self.default_save_dir)

            # 显示对话框
            file_path, _ = QFileDialog.getSaveFileName(
                parent,
                "Save Audio File",
                os.path.join(self.default_save_dir, default_name),
                file_filter
            )

            if file_path:
                logger.info(f"User selected save path: {file_path}")
                return file_path
            else:
                logger.info("User cancelled save dialog")
                return None

        except Exception as e:
            logger.error(f"Error showing save dialog: {e}")
            return None

    def save_file(self, source_path: str, target_path: str,
                 overwrite: bool = False) -> Tuple[bool, str]:
        """
        保存文件

        Args:
            source_path: 源文件路径
            target_path: 目标文件路径
            overwrite: 是否覆盖已存在文件

        Returns:
            (success, message): 是否成功及消息
        """
        try:
            # 检查源文件
            if not os.path.exists(source_path):
                return False, f"Source file not found: {source_path}"

            # 检查目标文件
            if os.path.exists(target_path) and not overwrite:
                return False, f"Target file already exists: {target_path}"

            # 确保目标目录存在
            target_dir = os.path.dirname(target_path)
            self.path_manager.ensure_directory(target_dir)

            # 复制文件
            shutil.copy2(source_path, target_path)

            logger.info(f"File saved: {source_path} -> {target_path}")
            return True, "File saved successfully"

        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return False, f"Error saving file: {str(e)}"

    def generate_unique_filename(self, base_name: str,
                                 extension: str = ".wav") -> str:
        """
        生成唯一文件名

        Args:
            base_name: 基础文件名
            extension: 文件扩展名

        Returns:
            唯一的文件名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_name = os.path.splitext(base_name)[0]
        clean_name = ''.join(c for c in clean_name if c.isalnum() or c in '._-')

        unique_name = f"{clean_name}_{timestamp}{extension}"

        # 确保文件名唯一
        counter = 1
        while os.path.exists(os.path.join(self.default_save_dir, unique_name)):
            unique_name = f"{clean_name}_{timestamp}_{counter}{extension}"
            counter += 1

        return unique_name

    def get_relative_path(self, absolute_path: str) -> str:
        """
        获取相对路径

        Args:
            absolute_path: 绝对路径

        Returns:
            相对于项目根目录的路径
        """
        try:
            if absolute_path.startswith(self.path_manager.project_root):
                relative_path = absolute_path[len(self.path_manager.project_root):].lstrip('/\\')
                return relative_path
            return absolute_path

        except Exception as e:
            logger.error(f"Error getting relative path: {e}")
            return absolute_path

    def format_file_size(self, size_bytes: int) -> str:
        """
        格式化文件大小

        Args:
            size_bytes: 文件大小（字节）

        Returns:
            格式化后的大小字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        获取文件信息

        Args:
            file_path: 文件路径

        Returns:
            文件信息字典或None
        """
        try:
            if not os.path.exists(file_path):
                return None

            stat = os.stat(file_path)

            return {
                'path': file_path,
                'name': os.path.basename(file_path),
                'size': stat.st_size,
                'size_formatted': self.format_file_size(stat.st_size),
                'created_time': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                'modified_time': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'extension': os.path.splitext(file_path)[1].lower(),
            }

        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None

    def create_output_path(self, model_name: str = "cosyvoice",
                          prefix: str = "output") -> str:
        """
        创建输出文件路径

        Args:
            model_name: 模型名称
            prefix: 文件名前缀

        Returns:
            完整的输出文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{model_name}_{timestamp}.wav"
        return os.path.join(self.default_save_dir, filename)


# 全局服务实例
_file_service: Optional[FileService] = None


def get_file_service() -> FileService:
    """获取文件服务实例"""
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service
