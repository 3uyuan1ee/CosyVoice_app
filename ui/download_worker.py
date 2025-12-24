"""
异步下载工作线程 - 在后台线程执行模型下载任务
"""

from PyQt6.QtCore import QThread, pyqtSignal, QObject
from typing import Optional
from loguru import logger
import time


class DownloadSignals(QObject):
    """下载信号集合"""
    progress = pyqtSignal(str, int, str, int)  # model_id, current, total, percentage
    finished = pyqtSignal(str, bool, str)      # model_id, success, error_msg
    status_update = pyqtSignal(str, str)        # model_id, status_text


class ModelDownloadWorker(QThread):
    """
    模型下载工作线程

    在独立线程中执行下载任务，避免阻塞UI
    """

    def __init__(self, model_id: str, model_name: str, download_manager,
                 parent=None):
        super().__init__(parent)
        self.model_id = model_id
        self.model_name = model_name
        self.download_manager = download_manager
        self.signals = DownloadSignals()
        self._is_running = True
        self._is_cancelled = False

    def run(self):
        """执行下载任务"""
        try:
            logger.info(f"Starting download for model: {self.model_name}")

            # 发送开始状态
            self.signals.status_update.emit(self.model_id, "Initializing download...")

            # 创建进度回调函数
            def progress_callback(current: int, total: int, model_id: str = None):
                if not self._is_running or self._is_cancelled:
                    return False  # 取消下载

                if total > 0:
                    percentage = int((current / total) * 100)
                else:
                    percentage = 0

                # 格式化大小显示
                current_mb = current / (1024 * 1024)
                total_mb = total / (1024 * 1024)

                status_text = f"{current_mb:.1f}MB / {total_mb:.1f}MB"
                self.signals.progress.emit(
                    self.model_id, current, total, percentage
                )
                self.signals.status_update.emit(self.model_id, status_text)

                return True  # 继续下载

            # 执行下载（这里需要适配实际的下载管理器接口）
            # 注意：需要根据后端实际接口调整
            from backend.model_download_manager import ModelType, DownloadSource

            # 映射model_id到ModelType枚举
            model_type_map = {
                "cosyvoice3_2512": ModelType.COSYVOICE3_2512,
                "cosyvoice2": ModelType.COSYVOICE2,
                "cosyvoice_300m": ModelType.COSYVOICE_300M,
                "cosyvoice_300m_sft": ModelType.COSYVOICE_300M_SFT,
                "cosyvoice_300m_instruct": ModelType.COSYVOICE_300M_INSTRUCT,
                "cosyvoice_ttsfrd": ModelType.COSYVOICE_TTSFRD,
            }

            model_type = model_type_map.get(self.model_id)
            if not model_type:
                raise ValueError(f"Unknown model type: {self.model_id}")

            # 使用下载管理器下载模型
            # 注意：这里假设download_manager支持进度回调
            # 如果不支持，需要轮询状态
            success = self._download_with_progress(
                model_type, progress_callback
            )

            if self._is_cancelled:
                self.signals.finished.emit(self.model_id, False, "Download cancelled")
                self.signals.status_update.emit(self.model_id, "Cancelled")
            elif success:
                self.signals.finished.emit(self.model_id, True, "")
                self.signals.status_update.emit(self.model_id, "Download complete")
            else:
                self.signals.finished.emit(self.model_id, False, "Download failed")
                self.signals.status_update.emit(self.model_id, "Download failed")

        except Exception as e:
            logger.error(f"Download error for {self.model_name}: {str(e)}")
            self.signals.finished.emit(self.model_id, False, str(e))
            self.signals.status_update.emit(self.model_id, f"Error: {str(e)}")

    def _download_with_progress(self, model_type, progress_callback) -> bool:
        """
        带进度的下载实现

        由于后端的download_model可能是阻塞的，我们需要适配它
        """
        try:
            # 方案1：如果download_manager支持回调，直接使用
            # result = self.download_manager.download_model(
            #     model_type,
            #     progress_callback=progress_callback
            # )

            # 方案2：如果不支持，使用轮询状态
            # 这里我们使用模拟的方式，实际需要根据后端接口调整

            # 先启动下载（后台）
            # 注意：这里需要实际的下载实现
            # 目前用模拟代码

            self.signals.status_update.emit(self.model_id, "Connecting to server...")

            # 模拟下载过程
            total_size = 500 * 1024 * 1024  # 假设500MB
            chunk_size = 10 * 1024 * 1024    # 每次处理10MB

            for current in range(0, total_size + 1, chunk_size):
                if not self._is_running or self._is_cancelled:
                    return False

                # 模拟网络延迟
                time.sleep(0.1)

                # 调用进度回调
                should_continue = progress_callback(
                    min(current, total_size),
                    total_size,
                    self.model_id
                )

                if not should_continue:
                    return False

            # 实际实现时，这里应该调用真实的下载方法
            # 例如：
            # result = self.download_manager.download_model(model_type)
            # return result

            return True

        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            raise

    def cancel(self):
        """取消下载"""
        logger.info(f"Cancelling download for: {self.model_name}")
        self._is_cancelled = True
        self._is_running = False

    def stop(self):
        """停止线程"""
        self._is_running = False
