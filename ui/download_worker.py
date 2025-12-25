"""
异步下载工作线程 - 在后台线程执行模型下载任务
"""

from PyQt6.QtCore import QThread, pyqtSignal, QObject, QTimer
from typing import Optional
from loguru import logger
import time


class DownloadSignals(QObject):
    """下载信号集合"""
    progress = pyqtSignal(str, int, int, int)  # model_id, current, total, percentage
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
        self._download_error = None  # 存储下载错误信息

        # 模拟进度条
        self._fake_progress_timer = None
        self._current_fake_progress = 0
        self._fake_progress_step = 2  # 每次增加2%

    def run(self):
        """执行下载任务"""
        try:
            logger.info(f"Starting download for model: {self.model_name}")

            # 发送开始状态
            self.signals.status_update.emit(self.model_id, "Initializing download...")

            # 启动模拟进度定时器
            self._start_fake_progress()

            # 创建进度回调函数（用于实际进度，如果有的话）
            def progress_callback(current: int, total: int, model_id: str = None):
                if not self._is_running or self._is_cancelled:
                    return False  # 取消下载

                # 如果收到真实进度，更新模拟进度
                if total > 0:
                    real_percentage = int((current / total) * 100)
                    # 确保真实进度不低于模拟进度
                    if real_percentage > self._current_fake_progress:
                        self._current_fake_progress = real_percentage
                    self._update_fake_progress(real_percentage)
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
            success = self._download_with_progress(
                model_type, progress_callback
            )

            # 停止模拟进度
            self._stop_fake_progress()

            # 根据结果发送信号
            if success:
                # 设置进度为100%
                self.signals.progress.emit(self.model_id, 100, 100, 100)
                self.signals.finished.emit(self.model_id, True, "")
                self.signals.status_update.emit(self.model_id, "Download complete")
                logger.info(f"Download finished successfully for {self.model_name}")
            else:
                # 下载失败或被取消
                if self._is_cancelled:
                    self.signals.finished.emit(self.model_id, False, "Download cancelled")
                    logger.info(f"Download was cancelled for {self.model_name}")
                else:
                    error_msg = self._download_error if self._download_error else "Download failed"
                    self.signals.finished.emit(self.model_id, False, error_msg)
                    logger.error(f"Download failed for {self.model_name}: {error_msg}")

        except Exception as e:
            self._stop_fake_progress()
            logger.error(f"Download error for {self.model_name}: {str(e)}")
            self.signals.finished.emit(self.model_id, False, str(e))
            self.signals.status_update.emit(self.model_id, f"Error: {str(e)}")

    def _start_fake_progress(self):
        """启动模拟进度定时器"""
        self._current_fake_progress = 0
        self._fake_progress_timer = QTimer()
        self._fake_progress_timer.timeout.connect(self._update_fake_progress_step)
        self._fake_progress_timer.start(500)  # 每500毫秒更新一次
        logger.info("Started fake progress timer")

    def _stop_fake_progress(self):
        """停止模拟进度定时器"""
        if self._fake_progress_timer:
            self._fake_progress_timer.stop()
            self._fake_progress_timer = None
            logger.info("Stopped fake progress timer")

    def _update_fake_progress_step(self):
        """定时器回调：更新模拟进度"""
        if self._current_fake_progress < 90:
            # 每次增加2%，最多到90%（预留10%给最后的验证步骤）
            self._current_fake_progress = min(90, self._current_fake_progress + self._fake_progress_step)

            # 计算模拟的当前值和总值（假设最大1GB）
            fake_current = int(self._current_fake_progress * 10 * 1024 * 1024)  # 10MB * percentage
            fake_total = 1024 * 1024 * 1024  # 1GB

            self.signals.progress.emit(
                self.model_id,
                fake_current,
                fake_total,
                self._current_fake_progress
            )

            logger.debug(f"Fake progress: {self._current_fake_progress}%")

    def _update_fake_progress(self, percentage: int):
        """更新进度到指定值"""
        self._current_fake_progress = percentage
        fake_current = int(percentage * 10 * 1024 * 1024)
        fake_total = 1024 * 1024 * 1024

        self.signals.progress.emit(
            self.model_id,
            fake_current,
            fake_total,
            percentage
        )

    def _download_with_progress(self, model_type, progress_callback) -> bool:
        """
        带进度的下载实现

        使用轮询方式获取下载进度并更新UI
        """
        try:
            from backend.model_download_manager import DownloadSource, DownloadCancelledError

            self.signals.status_update.emit(self.model_id, "Connecting to server...")

            # 由于model_download_manager的download_model是阻塞的
            # 我们使用轮询方式来获取进度

            # 先启动一个后台线程来执行实际下载
            import threading
            download_result = {"success": False, "error": None}
            download_complete = threading.Event()

            def download_thread():
                """后台下载线程"""
                try:
                    logger.info(f"Starting actual download for {model_type.value}")
                    success = self.download_manager.download_model(
                        model_type,
                        source=DownloadSource.AUTO,
                        force=False,
                        install_deps=True
                    )
                    download_result["success"] = success
                    logger.info(f"Download thread completed with success={success}")
                except DownloadCancelledError:
                    logger.info("Download was cancelled (caught in download thread)")
                    download_result["success"] = False
                    download_result["error"] = "Cancelled"
                except Exception as e:
                    logger.error(f"Download thread error: {e}")
                    download_result["success"] = False
                    download_result["error"] = str(e)
                finally:
                    download_complete.set()

            # 启动下载线程
            thread = threading.Thread(target=download_thread, daemon=True)
            thread.start()

            # 轮询进度并更新UI（使用模拟进度）
            poll_count = 0
            max_polls = 1200  # 最多轮询20分钟 (1200次 * 1秒)

            while not download_complete.is_set() and not self._is_cancelled:
                poll_count += 1

                # 这里可以尝试获取真实进度，如果没有则使用模拟进度
                status = self.download_manager.get_download_status(model_type)

                if status and hasattr(status, 'progress'):
                    real_progress = int(status.progress * 100)
                    # 如果真实进度大于模拟进度，更新模拟进度
                    if real_progress > self._current_fake_progress and real_progress < 100:
                        self._update_fake_progress(real_progress)

                # 等待一段时间再轮询
                download_complete.wait(timeout=1.0)

                # 超时检查
                if poll_count >= max_polls:
                    logger.warning("Download polling timeout")
                    break

            # 检查是否被用户取消
            user_cancelled = False
            if self._is_cancelled:
                user_cancelled = True
                logger.info("Download was cancelled by user, waiting for background thread to complete...")
                self.signals.status_update.emit(self.model_id, "Cancelling...")

            # 等待下载线程完成
            thread.join(timeout=5.0)

            # 检查下载结果
            if download_result.get("success"):
                logger.info(f"Download completed successfully for {model_type.value}")
                # 即使之前被取消，如果下载成功，也返回成功
                if user_cancelled:
                    logger.info("Download completed despite user cancellation")
                    self.signals.status_update.emit(self.model_id, "Download completed")
                self._download_error = None
                return True
            else:
                error = download_result.get("error", "Unknown error")
                logger.error(f"Download failed: {error}")
                self._download_error = error
                return False

        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            raise

    def cancel(self):
        """取消下载"""
        logger.info(f"Cancelling download for: {self.model_name}")
        self._is_cancelled = True
        self._is_running = False

        # 停止模拟进度
        self._stop_fake_progress()

        # 调用下载管理器的取消方法
        try:
            from backend.model_download_manager import ModelType

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
            if model_type and self.download_manager:
                self.download_manager.cancel_download(model_type)
                logger.info(f"Called download_manager.cancel_download for {self.model_id}")
        except Exception as e:
            logger.error(f"Error calling download_manager.cancel_download: {e}")

    def stop(self):
        """停止线程"""
        self._is_running = False
        self._stop_fake_progress()
