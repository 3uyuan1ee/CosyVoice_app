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
from ui.message_box_helper import MessageBoxHelper
from backend.model_download_service import get_model_download_service, ModelInfo
from backend.path_manager import PathManager
from backend.model_download_manager import ModelDownloadManager


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

        # 创建并注入下载管理器
        self.download_manager = ModelDownloadManager()
        self.download_service.set_download_manager(self.download_manager)
        self.download_service.set_path_manager(self.path_manager)

        # 存储模型卡片
        self.model_cards: Dict[str, ModelCardWidget] = {}

        # 初始化UI
        self._init_ui()
        self._load_models()
        self._connect_signals()

        # 连接服务层信号
        self.download_service.download_progress.connect(self._on_download_progress)
        self.download_service.download_finished.connect(self._on_download_finished)
        self.download_service.download_status_update.connect(self._on_download_status_update)

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
                # 添加一个额外的固定高度空白区域，确保最底部的模型完全可见
                from PyQt6.QtWidgets import QWidget
                bottom_spacer = QWidget()
                bottom_spacer.setMinimumHeight(100)  # 100像素的额外底部空白
                container_layout.addWidget(bottom_spacer)
                # 添加弹性空间
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
            card.delete_clicked.connect(self._on_delete_requested)

            # 添加到布局
            self.modelsContainer.layout().addWidget(card)
            self.model_cards[model.id] = card

            logger.info(f"Added model card: {model.name}")

        except Exception as e:
            logger.error(f"Error adding model card for {model.name}: {e}")

    def _clear_model_cards(self):
        """清空模型卡片"""
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

            # 通过服务层启动下载
            success = self.download_service.start_download(model_id)

            if not success:
                logger.warning(f"Failed to start download for: {model_id}")
                self._show_error_message("Download failed to start",
                                        "Download may already be in progress or service not ready")
                return

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

            # 通过服务层取消下载
            success = self.download_service.cancel_download(model_id)

            if success:
                # 更新UI状态
                card = self.model_cards.get(model_id)
                if card:
                    card.update_status(ModelStatus.NOT_DOWNLOADED)

                logger.info(f"Download cancelled for: {model_id}")
            else:
                logger.warning(f"Failed to cancel download for: {model_id}")

        except Exception as e:
            logger.error(f"Error cancelling download for {model_id}: {e}")

    @pyqtSlot(str)
    def _on_delete_requested(self, model_id: str):
        """处理删除模型"""
        try:
            logger.info(f"Delete requested for model: {model_id}")

            # 确认对话框
            reply = MessageBoxHelper.question(
                self,
                "Confirm Delete",
                "Are you sure you want to delete this model? This will free up disk space but you'll need to download again."
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 通过服务层删除模型
                success = self.download_service.delete_model(model_id)

                if success:
                    # 更新UI状态
                    card = self.model_cards.get(model_id)
                    if card:
                        card.update_status(ModelStatus.NOT_DOWNLOADED)

                    self._show_info_message(f"Model deleted successfully")
                    logger.info(f"Model deleted: {model_id}")
                else:
                    self._show_error_message("Delete failed", "Failed to delete model files")
                    logger.warning(f"Failed to delete model: {model_id}")

        except Exception as e:
            logger.error(f"Error deleting model {model_id}: {e}")
            self._show_error_message("Delete error", str(e))

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
            reply = MessageBoxHelper.question(
                self,
                "Confirm Download All",
                f"Download {len(not_downloaded)} models? This may take a while."
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
        MessageBoxHelper.critical(self, title, message)

    def _show_info_message(self, message: str):
        """显示信息消息"""
        MessageBoxHelper.information(self, "Information", message)

    def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up model download controller")

        # 下载任务由服务层管理，不需要在这里清理
