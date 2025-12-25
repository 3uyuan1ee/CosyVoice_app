"""
缓存管理服务 - 管理应用缓存和临时文件

- 扫描和计算缓存大小
- 清理缓存文件
- 提供缓存管理接口
"""

import os
import shutil
import threading
import time
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger


@dataclass
class CacheInfo:
    """缓存信息数据类"""
    path: str                          # 缓存路径
    name: str                          # 缓存名称
    size_bytes: int = 0                # 大小（字节）
    size_formatted: str = ""           # 格式化大小
    file_count: int = 0                # 文件数量
    can_clear: bool = True             # 是否可清理
    description: str = ""              # 描述

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "path": self.path,
            "name": self.name,
            "size_bytes": self.size_bytes,
            "size_formatted": self.size_formatted,
            "file_count": self.file_count,
            "can_clear": self.can_clear,
            "description": self.description
        }


@dataclass
class CacheSummary:
    """缓存摘要数据类"""
    total_size_bytes: int = 0          # 总大小（字节）
    total_size_formatted: str = ""     # 格式化总大小
    total_files: int = 0               # 总文件数
    cache_items: List[CacheInfo] = field(default_factory=list)  # 缓存项列表

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "total_size_bytes": self.total_size_bytes,
            "total_size_formatted": self.total_size_formatted,
            "total_files": self.total_files,
            "cache_items": [item.to_dict() for item in self.cache_items]
        }


class CacheManager:
    """
    缓存管理器
    - 扫描缓存目录
    - 计算缓存大小
    - 清理缓存文件
    - 提供缓存查询和管理接口
    """

    _instance: Optional['CacheManager'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 避免重复初始化
        if hasattr(self, '_initialized'):
            return

        self._initialized = True

        # 依赖
        from backend.path_manager import PathManager
        self.path_manager = PathManager()

        # 缓存配置
        self._cache_directories = self._init_cache_directories()

        logger.info("[CacheManager] Cache manager initialized")

    def _init_cache_directories(self) -> List[Dict[str, any]]:
        """初始化缓存目录配置"""
        return [
            {
                "name": "Logs",
                "path": self.path_manager.get_log_path(),
                "description": "Application log files",
                "can_clear": True,
            },
            {
                "name": "Temp",
                "path": self.path_manager.get_temp_path(),
                "description": "Temporary files",
                "can_clear": True,
            },
            {
                "name": "Download Cache",
                "path": self.path_manager.get_download_cache_path(),
                "description": "Model download cache",
                "can_clear": True,
            },
            {
                "name": "Generated Audio",
                "path": self.path_manager.get_res_voice_path(),
                "description": "Generated audio files",
                "can_clear": False,  # 用户可能想保留
            },
            {
                "name": "ModelScope Cache",
                "path": self.path_manager.get_modelscope_cache_path(),
                "description": "ModelScope model download cache",
                "can_clear": True,
            },
        ]

    def scan_cache(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> CacheSummary:
        """
        扫描所有缓存目录

        Args:
            progress_callback: 进度回调 (current, total)

        Returns:
            CacheSummary: 缓存摘要
        """
        try:
            logger.info("[CacheManager] Scanning cache directories...")

            summary = CacheSummary()
            total_dirs = len(self._cache_directories)

            for idx, cache_config in enumerate(self._cache_directories):
                # 进度回调
                if progress_callback:
                    progress_callback(idx + 1, total_dirs)

                cache_path = cache_config["path"]

                # 检查路径是否存在
                if not os.path.exists(cache_path):
                    logger.debug(f"[CacheManager] Cache path does not exist: {cache_path}")
                    continue

                # 计算缓存大小
                size_bytes, file_count = self._calculate_directory_size(cache_path)

                # 创建缓存信息
                cache_info = CacheInfo(
                    path=cache_path,
                    name=cache_config["name"],
                    size_bytes=size_bytes,
                    size_formatted=self._format_size(size_bytes),
                    file_count=file_count,
                    can_clear=cache_config["can_clear"],
                    description=cache_config["description"]
                )

                summary.cache_items.append(cache_info)
                summary.total_size_bytes += size_bytes
                summary.total_files += file_count

            summary.total_size_formatted = self._format_size(summary.total_size_bytes)

            logger.info(f"[CacheManager] Cache scan completed: {summary.total_size_formatted} ({summary.total_files} files)")
            return summary

        except Exception as e:
            logger.error(f"[CacheManager] Error scanning cache: {e}")
            return CacheSummary()

    def _calculate_directory_size(self, directory: str) -> Tuple[int, int]:
        """
        计算目录大小

        Args:
            directory: 目录路径

        Returns:
            Tuple: (size_bytes, file_count)
        """
        total_size = 0
        file_count = 0

        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)

                    try:
                        if os.path.isfile(file_path):
                            total_size += os.path.getsize(file_path)
                            file_count += 1
                    except (OSError, PermissionError):
                        # 跳过无法访问的文件
                        continue

        except Exception as e:
            logger.warning(f"[CacheManager] Error calculating directory size for {directory}: {e}")

        return total_size, file_count

    def clear_cache(self, cache_name: str, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        清理指定缓存

        Args:
            cache_name: 缓存名称（如 "Logs", "Temp"）
            progress_callback: 进度回调 (message)

        Returns:
            bool: 是否成功
        """
        try:
            logger.info(f"[CacheManager] Clearing cache: {cache_name}")

            # 查找缓存配置
            cache_config = None
            for config in self._cache_directories:
                if config["name"] == cache_name:
                    cache_config = config
                    break

            if not cache_config:
                logger.error(f"[CacheManager] Unknown cache: {cache_name}")
                return False

            if not cache_config["can_clear"]:
                logger.warning(f"[CacheManager] Cache cannot be cleared: {cache_name}")
                return False

            cache_path = cache_config["path"]

            if progress_callback:
                progress_callback(f"Clearing {cache_name}...")

            # 检查路径是否存在
            if not os.path.exists(cache_path):
                logger.info(f"[CacheManager] Cache path does not exist: {cache_path}")
                return True

            # 删除目录内容
            self._clear_directory_contents(cache_path)

            # 重新创建目录
            os.makedirs(cache_path, exist_ok=True)

            logger.info(f"[CacheManager] Cache cleared: {cache_name}")
            return True

        except Exception as e:
            logger.error(f"[CacheManager] Error clearing cache {cache_name}: {e}")
            return False

    def clear_all_cache(
        self,
        exclude: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Tuple[int, int]:
        """
        清理所有可清理的缓存

        Args:
            exclude: 排除的缓存名称列表
            progress_callback: 进度回调 (message, current, total)

        Returns:
            Tuple: (success_count, failed_count)
        """
        try:
            logger.info("[CacheManager] Clearing all caches...")

            if exclude is None:
                exclude = []

            success_count = 0
            failed_count = 0
            total = sum(1 for config in self._cache_directories if config["can_clear"])
            current = 0

            for cache_config in self._cache_directories:
                cache_name = cache_config["name"]

                # 跳过不可清理或排除的缓存
                if not cache_config["can_clear"] or cache_name in exclude:
                    continue

                current += 1

                if progress_callback:
                    progress_callback(f"Clearing {cache_name}...", current, total)

                # 清理缓存
                if self.clear_cache(cache_name):
                    success_count += 1
                else:
                    failed_count += 1

            logger.info(f"[CacheManager] Cache clearing completed: {success_count} success, {failed_count} failed")
            return success_count, failed_count

        except Exception as e:
            logger.error(f"[CacheManager] Error clearing all caches: {e}")
            return 0, 0

    def _clear_directory_contents(self, directory: str):
        """清理目录内容（保留目录本身）"""
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)

                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except (OSError, PermissionError) as e:
                    logger.warning(f"[CacheManager] Failed to delete {item_path}: {e}")
                    continue

        except Exception as e:
            logger.error(f"[CacheManager] Error clearing directory contents: {e}")

    def _format_size(self, size_bytes: int) -> str:
        """格式化字节大小为可读字符串"""
        if size_bytes == 0:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        size = float(size_bytes)

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.2f} {units[unit_index]}"

    def get_cache_summary(self) -> CacheSummary:
        """
        获取缓存摘要（快速方法，使用缓存）

        Returns:
            CacheSummary: 缓存摘要
        """
        return self.scan_cache()


# ==================== 全局实例 ====================

_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


if __name__ == "__main__":
    # 测试缓存管理器
    print("=" * 60)
    print("缓存管理器测试")
    print("=" * 60)

    manager = get_cache_manager()

    # 扫描缓存
    print("\n扫描缓存...")
    summary = manager.scan_cache()

    print(f"\n总缓存大小: {summary.total_size_formatted}")
    print(f"总文件数: {summary.total_files}")
    print(f"\n缓存详情:")

    for item in summary.cache_items:
        print(f"  {item.name}:")
        print(f"    路径: {item.path}")
        print(f"    大小: {item.size_formatted}")
        print(f"    文件数: {item.file_count}")
        print(f"    可清理: {'是' if item.can_clear else '否'}")
        print(f"    描述: {item.description}")

    # 测试清理（注释掉以避免实际删除）
    # print("\n清理日志缓存...")
    # if manager.clear_cache("Logs"):
    #     print("日志缓存已清理")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
