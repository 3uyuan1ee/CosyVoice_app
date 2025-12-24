"""
文件管理器 - 处理音频文件上传、列表和管理功能
"""

import os
from datetime import datetime
from .path_manager import PathManager


class FileManager:
    """文件管理器类，处理音频文件的上传、列表和管理"""

    def __init__(self):
        self.path_manager = PathManager()
        # 确保必要目录存在
        self._ensure_directories()

    def _ensure_directories(self):
        """确保必要的目录结构存在"""
        directories = [
            self.path_manager.get_ref_voice_path(),
            self.path_manager.get_res_voice_path(),
        ]

        for directory in directories:
            self.path_manager.ensure_directory(directory)

    def get_supported_audio_extensions(self):
        """获取支持的音频文件扩展名"""
        return {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}

    def _generate_safe_filename(self, original_filename):
        """生成安全的文件名"""
        # 获取文件名和扩展名
        base_name = os.path.splitext(original_filename)[0]
        extension = os.path.splitext(original_filename)[1].lower()

        # 清理文件名（移除特殊字符）
        safe_base_name = ''.join(c for c in base_name if c.isalnum() or c in '._-')

        # 生成唯一文件名（添加时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{safe_base_name}_{timestamp}{extension}"

        return safe_filename

    def _validate_file(self, file, allowed_extensions, max_size_mb=100):
        """验证上传的文件"""
        # 检查文件类型
        filename = file.filename
        if not filename:
            return False, "没有选择文件"

        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in allowed_extensions:
            return False, f"不支持的文件格式。支持的格式: {', '.join(allowed_extensions)}"

        # 检查文件大小
        max_size = max_size_mb * 1024 * 1024
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0, os.SEEK_SET)

        if file_size > max_size:
            return False, f"文件大小超过限制。最大支持{max_size_mb}MB，当前文件大小: {file_size / (1024*1024):.2f}MB"

        return True, "文件验证通过"

    def _get_file_info(self, file_path):
        """获取文件信息"""
        if not os.path.exists(file_path):
            return None

        stat = os.stat(file_path)
        return {
            'filename': os.path.basename(file_path),
            'size': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'created_time': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
            'modified_time': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'file_type': os.path.splitext(file_path)[1][1:].upper()  # 去掉点号，转为大写
        }

    def _get_relative_path(self, absolute_path):
        """将绝对路径转换为相对路径"""
        if absolute_path.startswith(self.path_manager.project_root):
            relative_path = absolute_path[len(self.path_manager.project_root):].lstrip('/\\')
            return relative_path
        return absolute_path

# 全局实例
file_manager = FileManager()