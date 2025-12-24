"""
模型下载服务 - 封装模型下载业务逻辑
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import threading


class ModelDownloadStatus(Enum):
    """模型下载状态"""
    NOT_DOWNLOADED = "not_downloaded"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    ERROR = "error"


@dataclass
class ModelInfo:
    """模型信息"""
    id: str
    name: str
    size: str
    description: str
    model_type: str  # 用于映射到后端的ModelType枚举


class ModelDownloadService:
    """
    模型下载服务

    提供统一的模型下载业务逻辑接口
    单例模式，确保全局只有一个实例
    """

    _instance: Optional['ModelDownloadService'] = None
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
        self._download_manager = None
        self._path_manager = None
        self._download_tasks: Dict[str, object] = {}  # model_id -> download_task

        # 初始化支持的模型列表
        self._available_models = self._init_available_models()

    def _init_available_models(self) -> List[ModelInfo]:
        """初始化可用模型列表"""
        return [
            ModelInfo(
                id="cosyvoice3_2512",
                name="CosyVoice3-0.5B-2512",
                size="~1.2GB",
                description="Latest CosyVoice3 model with 2.5kHz sampling rate. Best quality, recommended for most use cases."
            ),
            ModelInfo(
                id="cosyvoice2",
                name="CosyVoice2-0.5B",
                size="~980MB",
                description="CosyVoice2 model with balanced performance and speed."
            ),
            ModelInfo(
                id="cosyvoice_300m",
                name="CosyVoice-300M",
                size="~600MB",
                description="Lightweight CosyVoice model, faster inference with good quality."
            ),
            ModelInfo(
                id="cosyvoice_300m_sft",
                name="CosyVoice-300M-SFT",
                size="~620MB",
                description="Fine-tuned 300M model for specific speaking styles."
            ),
            ModelInfo(
                id="cosyvoice_300m_instruct",
                name="CosyVoice-300M-Instruct",
                size="~620MB",
                description="Instruction-tuned model for precise control over voice characteristics."
            ),
            ModelInfo(
                id="cosyvoice_ttsfrd",
                name="CosyVoice-TTSFRD",
                size="~550MB",
                description="Fast response model optimized for real-time applications."
            ),
        ]

    def set_download_manager(self, download_manager):
        """设置下载管理器"""
        self._download_manager = download_manager

    def set_path_manager(self, path_manager):
        """设置路径管理器"""
        self._path_manager = path_manager

    def get_available_models(self) -> List[ModelInfo]:
        """获取可用模型列表"""
        return self._available_models

    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """获取指定模型信息"""
        for model in self._available_models:
            if model.id == model_id:
                return model
        return None

    def check_model_status(self, model_id: str) -> ModelDownloadStatus:
        """
        检查模型下载状态

        Returns:
            ModelDownloadStatus: 模型状态
        """
        if not self._path_manager:
            return ModelDownloadStatus.NOT_DOWNLOADED

        try:
            # 映射model_id到路径检查方法
            path_checks = {
                "cosyvoice3_2512": self._path_manager.get_cosyvoice3_2512_model_path,
                "cosyvoice2": self._path_manager.get_cosyvoice2_model_path,
                "cosyvoice_300m": self._path_manager.get_cosyvoice_300m_model_path,
                "cosyvoice_300m_sft": self._path_manager.get_cosyvoice_300m_sft_model_path,
                "cosyvoice_300m_instruct": self._path_manager.get_cosyvoice_300m_instruct_model_path,
                "cosyvoice_ttsfrd": self._path_manager.get_cosyvoice_ttsfrd_model_path,
            }

            check_func = path_checks.get(model_id)
            if not check_func:
                return ModelDownloadStatus.NOT_DOWNLOADED

            model_path = check_func()

            # 检查模型完整性
            if model_id == "cosyvoice3_2512":
                is_complete, _, _ = self._path_manager.check_cosyvoice3_model_integrity(model_path)
                if is_complete:
                    return ModelDownloadStatus.DOWNLOADED
            else:
                # 简单检查目录是否存在
                import os
                if os.path.exists(model_path):
                    return ModelDownloadStatus.DOWNLOADED

            return ModelDownloadStatus.NOT_DOWNLOADED

        except Exception as e:
            print(f"Error checking model status: {e}")
            return ModelDownloadStatus.ERROR

    def start_download(self, model_id: str) -> bool:
        """
        开始下载模型

        Args:
            model_id: 模型ID

        Returns:
            bool: 是否成功启动下载
        """
        # 检查是否已有下载任务
        if model_id in self._download_tasks:
            return False

        # TODO: 启动下载任务
        # 这里应该创建并启动下载线程
        return True

    def cancel_download(self, model_id: str) -> bool:
        """
        取消下载

        Args:
            model_id: 模型ID

        Returns:
            bool: 是否成功取消
        """
        # TODO: 实现取消逻辑
        return True

    def get_download_progress(self, model_id: str) -> Dict:
        """
        获取下载进度

        Args:
            model_id: 模型ID

        Returns:
            Dict: 进度信息 {current, total, percentage, speed, eta}
        """
        # TODO: 实现进度查询
        return {
            "current": 0,
            "total": 100,
            "percentage": 0,
            "speed": "0 MB/s",
            "eta": "00:00:00"
        }

    def get_downloaded_models(self) -> List[str]:
        """获取已下载的模型ID列表"""
        downloaded = []
        for model in self._available_models:
            if self.check_model_status(model.id) == ModelDownloadStatus.DOWNLOADED:
                downloaded.append(model.id)
        return downloaded

    def cleanup_cache(self) -> bool:
        """清理下载缓存"""
        if not self._download_manager:
            return False

        try:
            self._download_manager.cleanup_incomplete_downloads()
            return True
        except Exception as e:
            print(f"Cleanup error: {e}")
            return False


# 全局服务实例
_model_download_service: Optional[ModelDownloadService] = None


def get_model_download_service() -> ModelDownloadService:
    """获取模型下载服务实例"""
    global _model_download_service
    if _model_download_service is None:
        _model_download_service = ModelDownloadService()
    return _model_download_service
