"""
模型下载控制器 - 础理模型下载页面的UI逻辑
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.uic import loadUi
import os
from loguru import logger
from typing import Dict, Optional

from ui.model_card_widget import ModelCardWidget, ModelStatus
from ui.download_worker import ModelDownloadWorker
from backend.model_download_service import get_model_download_service, ModelInfo
from backend.path_manager import PathManager


class ModelDownloadController(QWidget):
    """模型下载控制器"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 加载UI文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, 'model_download.ui')
        loadUi(ui_path, self)

        # 服务层
        self.download_service = get_model_download_service()
        self.path_manager = PathManager()

        # 初始化服务
        self.download_service.set_path_manager(self.path_manager)

        # 存储模型卡片和下载任务
        self.model_cards: Dict[str, ModelCardWidget] = {}
        self.download_workers: Dict[str, ModelDownloadWorker] = {}

        # 初始化UI
        self._init_ui()
        self._load_models()
        self._connect_signals()

    def _init_ui(self):
        """初始化UI"""
        # 容器布局已在UI文件中定义，这里不需要额外设置
        pass

    def _load_models(self):
        """加载模型列表"""
        try:
            # 清空现有模型卡片
            self._clear_model_cards()

            # 获取可用模型
            models = self.download_service.get_available_models()

            # 为每个模型创建卡片
            for model in models:
                self._add_model_card(model)

            # 在最后添加弹性空间，确保滚动能到底部
            container_layout = self.modelsContainer.layout()
            if container_layout:
                container_layout.addStretch()

            logger.info(f"Loaded {len(models)} models")

        except Exception as e:
            logger.error(f"Error loading models: {e}")
            self._show_error_message("Failed to load models", str(e))

    def _add_model_card(self, model: ModelInfo):
        """添加模型卡片"""
        try:
            # 创建模型卡片
            card = ModelCardWidget(
                model_id=model.id,
                model_name=model.name,
                model_size=model.size,
                model_description=model.description,
                parent=self.modelsContainer
            )

            # 检查模型状态
            status = self.download_service.check_model_status(model.id)
            model_status = self._map_service_status(status)
            card.update_status(model_status)

            # 连接信号
            card.download_clicked.connect(self._on_download_requested)
            card.cancel_clicked.connect(self._on_download_cancelled)

            # 添加到布局
            self.modelsContainer.layout().addWidget(card)
            self.model_cards[model.id] = card

            logger.info(f"Added model card: {model.name}")

        except Exception as e:
            logger.error(f"Error adding model card for {model.name}: {e}")

    def _clear_model_cards(self):
        """清空模型卡片"""
        # 停止所有下载任务
        for worker in self.download_workers.values():
            worker.stop()
            worker.wait()
        self.download_workers.clear()

        # 清空布局
        layout = self.modelsContainer.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.model_cards.clear()

    def _connect_signals(self):
        """连接信号槽"""
        self.btnDownloadAll.clicked.connect(self._on_download_all_clicked)
        self.btnRefresh.clicked.connect(self._on_refresh_clicked)

    def _map_service_status(self, service_status) -> ModelStatus:
        """映射服务状态到UI状态"""
        from backend.model_download_service import ModelDownloadStatus

        status_map = {
            ModelDownloadStatus.NOT_DOWNLOADED: ModelStatus.NOT_DOWNLOADED,
            ModelDownloadStatus.DOWNLOADING: ModelStatus.DOWNLOADING,
            ModelDownloadStatus.DOWNLOADED: ModelStatus.DOWNLOADED,
            ModelDownloadStatus.ERROR: ModelStatus.ERROR,
        }
        return status_map.get(service_status, ModelStatus.NOT_DOWNLOADED)

    @pyqtSlot(str)
    def _on_download_requested(self, model_id: str):
        """处理下载请求"""
        try:
            logger.info(f"Download requested for model: {model_id}")

            # 检查是否已在下载
            if model_id in self.download_workers:
                logger.warning(f"Download already in progress for: {model_id}")
                return

            # 获取模型信息
            model_info = self.download_service.get_model_info(model_id)
            if not model_info:
                raise ValueError(f"Model not found: {model_id}")

            # 创建下载工作线程
            worker = ModelDownloadWorker(
                model_id=model_id,
                model_name=model_info.name,
                download_manager=None,  # TODO: 传入实际的下载管理器
                parent=self
            )

            # 连接信号
            worker.signals.progress.connect(self._on_download_progress)
            worker.signals.finished.connect(self._on_download_finished)
            worker.signals.status_update.connect(self._on_download_status_update)

            # 启动下载
            self.download_workers[model_id] = worker
            worker.start()

            # 更新UI状态
            card = self.model_cards.get(model_id)
            if card:
                card.update_status(ModelStatus.DOWNLOADING)

            logger.info(f"Download started for: {model_id}")

        except Exception as e:
            logger.error(f"Error starting download for {model_id}: {e}")
            self._show_error_message("Download failed to start", str(e))

    @pyqtSlot(str)
    def _on_download_cancelled(self, model_id: str):
        """处理取消下载"""
        try:
            logger.info(f"Cancelling download for: {model_id}")

            worker = self.download_workers.get(model_id)
            if worker:
                worker.cancel()
                worker.wait()
                del self.download_workers[model_id]

            # 更新UI状态
            card = self.model_cards.get(model_id)
            if card:
                card.update_status(ModelStatus.NOT_DOWNLOADED)

            logger.info(f"Download cancelled for: {model_id}")

        except Exception as e:
            logger.error(f"Error cancelling download for {model_id}: {e}")

    @pyqtSlot(str, int, int, int)
    def _on_download_progress(self, model_id: str, current: int, total: int, percentage: int):
        """处理下载进度更新"""
        card = self.model_cards.get(model_id)
        if card:
            card.update_status(ModelStatus.DOWNLOADING, percentage)

    @pyqtSlot(str, bool, str)
    def _on_download_finished(self, model_id: str, success: bool, error_msg: str):
        """处理下载完成"""
        try:
            # 清理工作线程
            if model_id in self.download_workers:
                del self.download_workers[model_id]

            # 更新UI状态
            card = self.model_cards.get(model_id)
            if card:
                if success:
                    card.update_status(ModelStatus.DOWNLOADED)
                    logger.info(f"Download completed for: {model_id}")
                else:
                    card.update_status(ModelStatus.ERROR, 0, error_msg)
                    logger.error(f"Download failed for {model_id}: {error_msg}")

        except Exception as e:
            logger.error(f"Error handling download finished for {model_id}: {e}")

    @pyqtSlot(str, str)
    def _on_download_status_update(self, model_id: str, status_text: str):
        """处理下载状态更新"""
        # 可以在状态栏显示当前状态
        logger.debug(f"Download status for {model_id}: {status_text}")

    def _on_download_all_clicked(self):
        """处理下载全部按钮"""
        try:
            logger.info("Download all requested")

            # 获取未下载的模型
            not_downloaded = []
            for model in self.download_service.get_available_models():
                status = self.download_service.check_model_status(model.id)
                if status != "downloaded":
                    not_downloaded.append(model.id)

            if not not_downloaded:
                self._show_info_message("All models already downloaded")
                return

            # 确认对话框
            reply = QMessageBox.question(
                self,
                "Confirm Download All",
                f"Download {len(not_downloaded)} models? This may take a while.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 依次启动下载
                for model_id in not_downloaded:
                    self._on_download_requested(model_id)

        except Exception as e:
            logger.error(f"Error in download all: {e}")
            self._show_error_message("Download all failed", str(e))

    def _on_refresh_clicked(self):
        """处理刷新按钮"""
        try:
            logger.info("Refreshing model status")
            self._load_models()
            self._show_info_message("Model list refreshed")

        except Exception as e:
            logger.error(f"Error refreshing models: {e}")
            self._show_error_message("Refresh failed", str(e))

    def _show_error_message(self, title: str, message: str):
        """显示错误消息"""
        QMessageBox.critical(self, title, message)

    def _show_info_message(self, message: str):
        """显示信息消息"""
        QMessageBox.information(self, "Information", message)

    def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up model download controller")

        # 停止所有下载任务
        for worker in self.download_workers.values():
            worker.stop()
            worker.wait()

        self.download_workers.clear()
