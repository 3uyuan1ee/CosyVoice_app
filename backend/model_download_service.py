"""
模型下载服务 - 封装模型下载业务逻辑
"""




from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import threading
from loguru import logger
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal


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


@dataclass
class DownloadProgress:
    """下载进度信息"""
    model_id: str
    current: int = 0
    total: int = 0
    percentage: int = 0
    speed: str = "0 MB/s"
    eta: str = "00:00:00"
    status_text: str = ""
    is_downloading: bool = False
    start_time: Optional[datetime] = None
    error_message: str = ""


class ModelDownloadService(QObject):
    """
    模型下载服务

    提供统一的模型下载业务逻辑接口
    单例模式，确保全局只有一个实例
    """

    # 定义信号
    download_progress = pyqtSignal(str, int, int, int)  # model_id, current, total, percentage
    download_finished = pyqtSignal(str, bool, str)      # model_id, success, error_msg
    download_status_update = pyqtSignal(str, str)        # model_id, status_text

    _instance: Optional['ModelDownloadService'] = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # 创建实例
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, *args, **kwargs):
        # 避免重复初始化
        if ModelDownloadService._initialized:
            return

        # 先调用父类初始化（这很关键，必须在设置任何属性之前）
        super().__init__(*args, **kwargs)

        # 标记为已初始化
        ModelDownloadService._initialized = True

        self._download_manager = None
        self._path_manager = None
        self._download_tasks: Dict[str, 'ui.download_worker.ModelDownloadWorker'] = {}
        self._download_progress: Dict[str, DownloadProgress] = {}
        self._progress_lock = threading.Lock()

        # 初始化支持的模型列表
        self._available_models = self._init_available_models()

        logger.info("ModelDownloadService initialized")

    def _init_available_models(self) -> List[ModelInfo]:
        """初始化可用模型列表"""
        return [
            ModelInfo(
                id="cosyvoice3_2512",
                name="CosyVoice3-0.5B-2512",
                size="~1.2GB",
                description="Latest CosyVoice3 model with 2.5kHz sampling rate. Best quality, recommended for most use cases.",
                model_type="cosyvoice3"
            ),
            ModelInfo(
                id="cosyvoice2",
                name="CosyVoice2-0.5B",
                size="~980MB",
                description="CosyVoice2 model with balanced performance and speed.",
                model_type="cosyvoice2"
            ),
            ModelInfo(
                id="cosyvoice_300m",
                name="CosyVoice-300M",
                size="~600MB",
                description="Lightweight CosyVoice model, faster inference with good quality.",
                model_type="cosyvoice"
            ),
            ModelInfo(
                id="cosyvoice_300m_sft",
                name="CosyVoice-300M-SFT",
                size="~620MB",
                description="Fine-tuned 300M model for specific speaking styles.",
                model_type="cosyvoice"
            ),
            ModelInfo(
                id="cosyvoice_300m_instruct",
                name="CosyVoice-300M-Instruct",
                size="~620MB",
                description="Instruction-tuned model for precise control over voice characteristics.",
                model_type="cosyvoice"
            ),
            ModelInfo(
                id="cosyvoice_ttsfrd",
                name="CosyVoice-TTSFRD",
                size="~550MB",
                description="Fast response model optimized for real-time applications.",
                model_type="cosyvoice"
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
        try:
            # 检查是否已有下载任务
            if model_id in self._download_tasks:
                logger.warning(f"Download task already exists for model: {model_id}")
                return False

            # 获取模型信息
            model_info = self.get_model_info(model_id)
            if not model_info:
                logger.error(f"Unknown model ID: {model_id}")
                return False

            # 检查下载管理器是否已设置
            if not self._download_manager:
                logger.error("Download manager not set")
                return False

            # 创建下载进度对象
            with self._progress_lock:
                self._download_progress[model_id] = DownloadProgress(
                    model_id=model_id,
                    is_downloading=True,
                    start_time=datetime.now()
                )

            # 导入下载工作线程
            from ui.download_worker import ModelDownloadWorker

            # 创建下载工作线程
            worker = ModelDownloadWorker(
                model_id=model_id,
                model_name=model_info.name,
                download_manager=self._download_manager
            )

            # 连接信号
            worker.signals.progress.connect(self._on_download_progress)
            worker.signals.finished.connect(self._on_download_finished)
            worker.signals.status_update.connect(self._on_download_status_update)

            # 保存下载任务
            self._download_tasks[model_id] = worker

            # 启动下载线程
            worker.start()

            logger.info(f"Download started for model: {model_id}")
            return True

        except Exception as e:
            logger.error(f"Error starting download for {model_id}: {e}")
            # 清理进度信息
            with self._progress_lock:
                if model_id in self._download_progress:
                    del self._download_progress[model_id]
            return False

    def cancel_download(self, model_id: str) -> bool:
        """
        取消下载

        Args:
            model_id: 模型ID

        Returns:
            bool: 是否成功取消
        """
        try:
            if model_id not in self._download_tasks:
                logger.warning(f"No download task found for model: {model_id}")
                return False

            worker = self._download_tasks[model_id]

            # 取消下载
            worker.cancel()

            # 更新进度状态
            with self._progress_lock:
                if model_id in self._download_progress:
                    self._download_progress[model_id].is_downloading = False
                    self._download_progress[model_id].status_text = "Cancelling..."

            logger.info(f"Download cancelled for model: {model_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling download for {model_id}: {e}")
            return False

    def get_download_progress(self, model_id: str) -> Dict:
        """
        获取下载进度

        Args:
            model_id: 模型ID

        Returns:
            Dict: 进度信息 {current, total, percentage, speed, eta, status_text, is_downloading, error_message}
        """
        try:
            with self._progress_lock:
                if model_id not in self._download_progress:
                    return {
                        "current": 0,
                        "total": 0,
                        "percentage": 0,
                        "speed": "0 MB/s",
                        "eta": "00:00:00",
                        "status_text": "Not started",
                        "is_downloading": False,
                        "error_message": ""
                    }

                progress = self._download_progress[model_id]
                return {
                    "current": progress.current,
                    "total": progress.total,
                    "percentage": progress.percentage,
                    "speed": progress.speed,
                    "eta": progress.eta,
                    "status_text": progress.status_text,
                    "is_downloading": progress.is_downloading,
                    "error_message": progress.error_message
                }

        except Exception as e:
            logger.error(f"Error getting download progress for {model_id}: {e}")
            return {
                "current": 0,
                "total": 0,
                "percentage": 0,
                "speed": "0 MB/s",
                "eta": "00:00:00",
                "status_text": "Error",
                "is_downloading": False,
                "error_message": str(e)
            }

    def _on_download_progress(self, model_id: str, current: int, total: int, percentage: int):
        """处理下载进度更新"""
        try:
            with self._progress_lock:
                if model_id in self._download_progress:
                    progress = self._download_progress[model_id]
                    progress.current = current
                    progress.total = total
                    progress.percentage = percentage

                    # 计算速度和ETA
                    if progress.start_time and percentage > 0:
                        elapsed = (datetime.now() - progress.start_time).total_seconds()
                        if elapsed > 0:
                            # 计算速度 (MB/s)
                            speed_mb = current / (1024 * 1024) / elapsed
                            progress.speed = f"{speed_mb:.2f} MB/s"

                            # 计算ETA
                            if percentage < 100:
                                remaining_bytes = total - current
                                remaining_seconds = remaining_bytes / (speed_mb * 1024 * 1024) if speed_mb > 0 else 0
                                progress.eta = f"{int(remaining_seconds // 3600):02d}:{int((remaining_seconds % 3600) // 60):02d}:{int(remaining_seconds % 60):02d}"

            # 发出信号通知UI
            self.download_progress.emit(model_id, current, total, percentage)

            logger.debug(f"Download progress for {model_id}: {percentage}%")

        except Exception as e:
            logger.error(f"Error updating download progress: {e}")

    def _on_download_finished(self, model_id: str, success: bool, error_msg: str):
        """处理下载完成"""
        try:
            with self._progress_lock:
                if model_id in self._download_progress:
                    progress = self._download_progress[model_id]
                    progress.is_downloading = False

                    if success:
                        progress.percentage = 100
                        progress.status_text = "Download complete"
                    else:
                        progress.error_message = error_msg
                        progress.status_text = f"Error: {error_msg}"

            # 清理下载任务
            if model_id in self._download_tasks:
                worker = self._download_tasks[model_id]
                worker.wait(5000)  # PyQt6 wait() 接受毫秒作为位置参数
                del self._download_tasks[model_id]

            # 发出信号通知UI
            self.download_finished.emit(model_id, success, error_msg)

            if success:
                logger.info(f"Download completed successfully for model: {model_id}")
            else:
                logger.error(f"Download failed for model {model_id}: {error_msg}")

        except Exception as e:
            logger.error(f"Error handling download finished for {model_id}: {e}")

    def _on_download_status_update(self, model_id: str, status_text: str):
        """处理下载状态更新"""
        try:
            with self._progress_lock:
                if model_id in self._download_progress:
                    self._download_progress[model_id].status_text = status_text

            # 发出信号通知UI
            self.download_status_update.emit(model_id, status_text)

            logger.debug(f"Download status for {model_id}: {status_text}")

        except Exception as e:
            logger.error(f"Error updating download status: {e}")

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
