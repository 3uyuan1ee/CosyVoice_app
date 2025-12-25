"""
系统信息服务 - 获取系统硬件信息

设计模式:
- 单例模式: 全局唯一实例
- 适配器模式: 跨平台兼容性

职责:
- 获取系统硬件信息（CPU、GPU、内存等）
- 跨平台兼容（Windows、macOS、Linux）
- 提供格式化的系统信息
"""

import platform
import os
import threading
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class SystemInfo:
    """系统信息数据类"""
    # 系统基础信息
    platform: str = ""           # 操作系统平台 (Windows, macOS, Linux)
    platform_version: str = ""   # 系统版本
    architecture: str = ""       # 系统架构 (x86_64, arm64, etc.)
    hostname: str = ""           # 主机名
    python_version: str = ""     # Python版本

    # CPU信息
    cpu_brand: str = ""          # CPU品牌型号
    cpu_cores: int = 0           # CPU核心数
    cpu_freq: str = ""           # CPU频率

    # GPU信息
    gpu_type: str = ""           # GPU类型 (NVIDIA, Apple Silicon, None)
    gpu_name: str = ""           # GPU名称
    gpu_memory: str = ""         # GPU显存
    compute_backend: str = ""    # 计算后端 (CUDA, MPS, CPU)

    # 内存信息
    total_memory: str = ""       # 总内存
    available_memory: str = ""   # 可用内存
    memory_usage_percent: float = 0.0  # 内存使用率

    # 磁盘信息
    total_disk: str = ""         # 总磁盘空间
    used_disk: str = ""          # 已用磁盘空间
    free_disk: str = ""          # 可用磁盘空间
    disk_usage_percent: float = 0.0    # 磁盘使用率

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        from dataclasses import asdict
        return asdict(self)


class SystemInfoService:
    """
    系统信息服务

    单例模式，全局唯一实例

    职责:
    - 获取系统硬件信息
    - 跨平台兼容性处理
    - 缓存系统信息（避免频繁查询）
    """

    _instance: Optional['SystemInfoService'] = None
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
        self._info_cache: Optional[SystemInfo] = None
        self._cache_lock = threading.Lock()
        self._cache_timestamp: float = 0
        self._cache_ttl: float = 30.0  # 缓存有效期30秒

        logger.info("[SystemInfoService] System info service initialized")

    def get_system_info(self, force_refresh: bool = False) -> SystemInfo:
        """
        获取系统信息

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            SystemInfo: 系统信息对象
        """
        import time

        with self._cache_lock:
            current_time = time.time()

            # 检查缓存
            if (not force_refresh and
                self._info_cache is not None and
                (current_time - self._cache_timestamp) < self._cache_ttl):
                return self._info_cache

            # 重新获取系统信息
            self._info_cache = self._collect_system_info()
            self._cache_timestamp = current_time

            return self._info_cache

    def _collect_system_info(self) -> SystemInfo:
        """收集系统信息"""
        try:
            info = SystemInfo()

            # 获取基础系统信息
            info.platform = platform.system()
            info.platform_version = platform.version()
            info.architecture = platform.machine()
            info.hostname = platform.node()
            info.python_version = platform.python_version()

            # 获取CPU信息
            info.cpu_brand = self._get_cpu_brand()
            info.cpu_cores = self._get_cpu_cores()
            info.cpu_freq = self._get_cpu_frequency()

            # 获取GPU信息
            info.gpu_type, info.gpu_name, info.gpu_memory = self._get_gpu_info()
            info.compute_backend = self._get_compute_backend()

            # 获取内存信息
            mem_total, mem_avail, mem_percent = self._get_memory_info()
            info.total_memory = self._format_size(mem_total)
            info.available_memory = self._format_size(mem_avail)
            info.memory_usage_percent = mem_percent

            # 获取磁盘信息
            disk_total, disk_used, disk_free, disk_percent = self._get_disk_info()
            info.total_disk = self._format_size(disk_total)
            info.used_disk = self._format_size(disk_used)
            info.free_disk = self._format_size(disk_free)
            info.disk_usage_percent = disk_percent

            logger.debug("[SystemInfoService] System info collected successfully")
            return info

        except Exception as e:
            logger.error(f"[SystemInfoService] Error collecting system info: {e}")
            return SystemInfo()

    def _get_cpu_brand(self) -> str:
        """获取CPU品牌型号"""
        try:
            if platform.system() == "Darwin":  # macOS
                import subprocess
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return result.stdout.strip()

            elif platform.system() == "Linux":
                try:
                    with open("/proc/cpuinfo", "r") as f:
                        for line in f:
                            if line.startswith("model name"):
                                return line.split(":", 1)[1].strip()
                except Exception:
                    pass

            elif platform.system() == "Windows":
                import subprocess
                result = subprocess.run(
                    ["wmic", "cpu", "get", "name"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    if len(lines) > 1:
                        return lines[1].strip()

            return platform.processor() or "Unknown CPU"

        except Exception as e:
            logger.warning(f"[SystemInfoService] Error getting CPU brand: {e}")
            return "Unknown CPU"

    def _get_cpu_cores(self) -> int:
        """获取CPU核心数"""
        try:
            return os.cpu_count() or 1
        except Exception:
            return 1

    def _get_cpu_frequency(self) -> str:
        """获取CPU频率"""
        try:
            import psutil
            freq = psutil.cpu_freq()
            if freq:
                return f"{freq.current:.2f} MHz"
            return "Unknown"
        except ImportError:
            # psutil未安装，尝试其他方法
            try:
                if platform.system() == "Linux":
                    with open("/proc/cpuinfo", "r") as f:
                        for line in f:
                            if line.startswith("cpu MHz"):
                                return f"{float(line.split(':', 1)[1].strip()):.2f} MHz"
                return "Unknown"
            except Exception:
                return "Unknown"

    def _get_gpu_info(self) -> Tuple[str, str, str]:
        """
        获取GPU信息

        Returns:
            Tuple: (gpu_type, gpu_name, gpu_memory)
        """
        gpu_type = "None"
        gpu_name = "None"
        gpu_memory = "N/A"

        try:
            # 检测NVIDIA GPU (CUDA)
            try:
                import pynvml
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()

                if device_count > 0:
                    gpu_type = "NVIDIA"
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    gpu_name = pynvml.nvmlDeviceGetName(handle)

                    try:
                        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        gpu_memory = self._format_size(mem_info.total)
                    except Exception:
                        gpu_memory = "N/A"

                pynvml.nvmlShutdown()

            except (ImportError, Exception):
                # NVIDIA GPU未检测到，尝试其他GPU
                pass

            # 如果没有NVIDIA，检查Apple Silicon (macOS)
            if gpu_type == "None" and platform.system() == "Darwin":
                try:
                    import subprocess
                    result = subprocess.run(
                        ["sysctl", "-n", "machdep.cpu.brand_string"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 and "Apple" in result.stdout:
                        gpu_type = "Apple Silicon"
                        gpu_name = result.stdout.strip()
                        # Apple Silicon的GPU是统一内存，不单独计算显存
                        gpu_memory = "Unified Memory"

                except Exception:
                    pass

            # 如果没有GPU，检查是否有torch支持
            if gpu_type == "None":
                try:
                    import torch
                    if torch.cuda.is_available():
                        gpu_type = "NVIDIA (PyTorch)"
                        gpu_name = torch.cuda.get_device_name(0)
                        gpu_memory = f"{torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB"
                    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                        gpu_type = "Apple Silicon (PyTorch)"
                        gpu_name = "MPS (Metal Performance Shaders)"
                        gpu_memory = "Unified Memory"
                except ImportError:
                    pass

        except Exception as e:
            logger.warning(f"[SystemInfoService] Error getting GPU info: {e}")

        return gpu_type, gpu_name, gpu_memory

    def _get_compute_backend(self) -> str:
        """获取计算后端类型"""
        try:
            import torch

            if torch.cuda.is_available():
                return "CUDA"

            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "MPS (Metal)"

            return "CPU"

        except ImportError:
            return "Not Available"

    def _get_memory_info(self) -> Tuple[int, int, float]:
        """
        获取内存信息

        Returns:
            Tuple: (total_bytes, available_bytes, usage_percent)
        """
        try:
            import psutil
            mem = psutil.virtual_memory()
            return mem.total, mem.available, mem.percent
        except ImportError:
            # psutil未安装，使用基础方法
            return 0, 0, 0.0

    def _get_disk_info(self) -> Tuple[int, int, int, float]:
        """
        获取磁盘信息

        Returns:
            Tuple: (total_bytes, used_bytes, free_bytes, usage_percent)
        """
        try:
            import psutil
            from backend.path_manager import PathManager

            path_manager = PathManager()
            disk = psutil.disk_usage(path_manager.project_root)

            return disk.total, disk.used, disk.free, disk.percent

        except ImportError:
            return 0, 0, 0, 0.0

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

    def get_formatted_info(self) -> Dict[str, str]:
        """
        获取格式化的系统信息（用于UI显示）

        Returns:
            Dict: 格式化的系统信息
        """
        info = self.get_system_info()

        return {
            "Platform": f"{info.platform} {info.platform_version}",
            "Architecture": info.architecture,
            "Hostname": info.hostname,
            "Python": info.python_version,
            "CPU": f"{info.cpu_brand} ({info.cpu_cores} cores)",
            "CPU Frequency": info.cpu_freq,
            "GPU": f"{info.gpu_type} - {info.gpu_name}" if info.gpu_type != "None" else "None",
            "GPU Memory": info.gpu_memory,
            "Compute Backend": info.compute_backend,
            "Total Memory": info.total_memory,
            "Available Memory": info.available_memory,
            "Memory Usage": f"{info.memory_usage_percent:.1f}%",
            "Total Disk": info.total_disk,
            "Used Disk": info.used_disk,
            "Free Disk": info.free_disk,
            "Disk Usage": f"{info.disk_usage_percent:.1f}%",
        }


# ==================== 全局实例 ====================

_system_info_service: Optional[SystemInfoService] = None


def get_system_info_service() -> SystemInfoService:
    """获取全局系统信息服务实例"""
    global _system_info_service
    if _system_info_service is None:
        _system_info_service = SystemInfoService()
    return _system_info_service


if __name__ == "__main__":
    # 测试系统信息服务
    print("=" * 60)
    print("系统信息服务测试")
    print("=" * 60)

    service = get_system_info_service()
    info = service.get_system_info()

    print(f"\n系统信息:")
    print(f"  平台: {info.platform} {info.platform_version}")
    print(f"  架构: {info.architecture}")
    print(f"  主机名: {info.hostname}")
    print(f"  Python版本: {info.python_version}")

    print(f"\nCPU信息:")
    print(f"  型号: {info.cpu_brand}")
    print(f"  核心数: {info.cpu_cores}")
    print(f"  频率: {info.cpu_freq}")

    print(f"\nGPU信息:")
    print(f"  类型: {info.gpu_type}")
    print(f"  名称: {info.gpu_name}")
    print(f"  显存: {info.gpu_memory}")
    print(f"  计算后端: {info.compute_backend}")

    print(f"\n内存信息:")
    print(f"  总内存: {info.total_memory}")
    print(f"  可用内存: {info.available_memory}")
    print(f"  使用率: {info.memory_usage_percent:.1f}%")

    print(f"\n磁盘信息:")
    print(f"  总空间: {info.total_disk}")
    print(f"  已用: {info.used_disk}")
    print(f"  可用: {info.free_disk}")
    print(f"  使用率: {info.disk_usage_percent:.1f}%")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
