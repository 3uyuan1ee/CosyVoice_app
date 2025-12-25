"""
Status页面控制器 - 管理系统状态界面

职责:
- 显示系统硬件信息
- 显示使用统计数据
- 提供缓存管理功能
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHeaderView, QTableWidgetItem, QMessageBox
from PyQt6.QtCore import Qt, pyqtSlot, QThread, pyqtSignal
from PyQt6.uic import loadUi
import os
from loguru import logger
from typing import Optional

from backend.system_info_service import get_system_info_service
from backend.statistics_service import get_statistics_service
from backend.cache_manager import get_cache_manager, CacheInfo
from ui.message_box_helper import MessageBoxHelper


class CacheScanWorker(QThread):
    """缓存扫描工作线程"""

    finished = pyqtSignal(object)  # CacheSummary
    error = pyqtSignal(str)

    def __init__(self, cache_manager, parent=None):
        super().__init__(parent)
        self.cache_manager = cache_manager

    def run(self):
        """执行缓存扫描"""
        try:
            summary = self.cache_manager.scan_cache()
            self.finished.emit(summary)
        except Exception as e:
            logger.error(f"Cache scan error: {e}")
            self.error.emit(str(e))


class StatusPanel(QWidget):
    """Status页面控制器"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 加载UI文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, 'status.ui')
        loadUi(ui_path, self)

        # 服务层
        self.system_info_service = get_system_info_service()
        self.statistics_service = get_statistics_service()
        self.cache_manager = get_cache_manager()

        # 缓存数据
        self._cache_items: list = []
        self._cache_summary = None

        # 初始化
        self._init_ui()
        self._connect_signals()

        # 加载数据
        self._load_system_info()
        self._load_statistics()
        self._start_cache_scan()

        logger.info("StatusPanel initialized")

    def _init_ui(self):
        """初始化UI"""
        # 配置表格
        self._setup_table(self.systemInfoTable)
        self._setup_table(self.statisticsTable)
        self._setup_table(self.cacheTable)

        # 隐藏缓存表格的表头
        self.cacheTable.horizontalHeader().setStretchLastSection(True)

    def _setup_table(self, table):
        """配置表格"""
        # 禁止编辑
        table.setEditTriggers(table.editTriggers().NoEditTriggers)

        # 设置列宽
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # 设置样式
        table.setVerticalScrollMode(table.ScrollMode.ScrollPerPixel)
        table.setHorizontalScrollMode(table.ScrollMode.ScrollPerPixel)

    def _connect_signals(self):
        """连接信号槽"""
        self.btnRefreshCache.clicked.connect(self._start_cache_scan)
        self.btnClearSelected.clicked.connect(self._clear_selected_cache)
        self.btnClearAll.clicked.connect(self._clear_all_cache)

    def _load_system_info(self):
        """加载系统信息"""
        try:
            logger.info("Loading system information...")

            # 获取系统信息
            info = self.system_info_service.get_formatted_info()

            # 填充表格
            self._populate_table(self.systemInfoTable, info)

            logger.info("System information loaded successfully")

        except Exception as e:
            logger.error(f"Error loading system info: {e}")
            MessageBoxHelper.critical(self, "Error", f"Failed to load system information: {str(e)}")

    def _load_statistics(self):
        """加载统计数据"""
        try:
            logger.info("Loading usage statistics...")

            # 获取统计数据
            stats = self.statistics_service.get_formatted_statistics()

            # 填充表格
            self._populate_table(self.statisticsTable, stats)

            logger.info("Usage statistics loaded successfully")

        except Exception as e:
            logger.error(f"Error loading statistics: {e}")
            MessageBoxHelper.critical(self, "Error", f"Failed to load statistics: {str(e)}")

    def _populate_table(self, table, data: dict):
        """填充表格数据"""
        try:
            # 清空表格
            table.setRowCount(0)

            # 填充数据
            for key, value in data.items():
                row = table.rowCount()
                table.insertRow(row)

                # 创建表格项
                key_item = QTableWidgetItem(key)
                value_item = QTableWidgetItem(str(value))

                # 设置对齐
                key_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                value_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

                # 添加到表格
                table.setItem(row, 0, key_item)
                table.setItem(row, 1, value_item)

        except Exception as e:
            logger.error(f"Error populating table: {e}")

    def _start_cache_scan(self):
        """开始缓存扫描"""
        try:
            logger.info("Starting cache scan...")

            # 禁用按钮
            self.btnRefreshCache.setEnabled(False)
            self.btnClearSelected.setEnabled(False)
            self.btnClearAll.setEnabled(False)
            self.cacheSizeLabel.setText("Total Cache Size: Scanning...")

            # 启动工作线程
            self._scan_worker = CacheScanWorker(self.cache_manager)
            self._scan_worker.finished.connect(self._on_cache_scan_finished)
            self._scan_worker.error.connect(self._on_cache_scan_error)
            self._scan_worker.start()

        except Exception as e:
            logger.error(f"Error starting cache scan: {e}")
            self._on_cache_scan_error(str(e))

    @pyqtSlot(object)
    def _on_cache_scan_finished(self, summary):
        """缓存扫描完成"""
        try:
            self._cache_summary = summary
            self._cache_items = summary.cache_items

            # 更新UI
            self.cacheSizeLabel.setText(f"Total Cache Size: {summary.total_size_formatted} ({summary.total_files} files)")

            # 填充缓存表格
            self._populate_cache_table(summary.cache_items)

            # 启用按钮
            self.btnRefreshCache.setEnabled(True)
            self.btnClearSelected.setEnabled(True)
            self.btnClearAll.setEnabled(True)

            logger.info(f"Cache scan completed: {summary.total_size_formatted}")

        except Exception as e:
            logger.error(f"Error handling cache scan finished: {e}")
            self._on_cache_scan_error(str(e))

    @pyqtSlot(str)
    def _on_cache_scan_error(self, error_msg: str):
        """缓存扫描错误"""
        logger.error(f"Cache scan error: {error_msg}")

        # 显示错误
        self.cacheSizeLabel.setText("Total Cache Size: Error")
        MessageBoxHelper.critical(self, "Error", f"Failed to scan cache: {error_msg}")

        # 启用按钮
        self.btnRefreshCache.setEnabled(True)
        self.btnClearSelected.setEnabled(False)
        self.btnClearAll.setEnabled(False)

    def _populate_cache_table(self, cache_items: list):
        """填充缓存表格"""
        try:
            # 清空表格
            self.cacheTable.setRowCount(0)

            # 填充数据
            for item in cache_items:
                row = self.cacheTable.rowCount()
                self.cacheTable.insertRow(row)

                # 创建表格项
                name_item = QTableWidgetItem(item.name)
                size_item = QTableWidgetItem(item.size_formatted)
                files_item = QTableWidgetItem(str(item.file_count))
                desc_item = QTableWidgetItem(item.description)

                # 设置对齐
                name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                files_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                desc_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

                # 设置数据（用于后续获取）
                name_item.setData(Qt.ItemDataRole.UserRole, item)

                # 如果不可清理，显示为灰色
                if not item.can_clear:
                    name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                    name_item.setForeground(Qt.GlobalColor.gray)

                # 添加到表格
                self.cacheTable.setItem(row, 0, name_item)
                self.cacheTable.setItem(row, 1, size_item)
                self.cacheTable.setItem(row, 2, files_item)
                self.cacheTable.setItem(row, 3, desc_item)

        except Exception as e:
            logger.error(f"Error populating cache table: {e}")

    def _get_selected_cache_item(self) -> Optional[CacheInfo]:
        """获取选中的缓存项"""
        try:
            selected_items = self.cacheTable.selectedItems()

            if not selected_items:
                return None

            # 获取第一个选中项的数据
            first_item = selected_items[0]
            cache_info = first_item.data(Qt.ItemDataRole.UserRole)

            return cache_info

        except Exception as e:
            logger.error(f"Error getting selected cache item: {e}")
            return None

    def _clear_selected_cache(self):
        """清理选中的缓存"""
        try:
            cache_item = self._get_selected_cache_item()

            if not cache_item:
                MessageBoxHelper.warning(self, "Warning", "Please select a cache item to clear")
                return

            if not cache_item.can_clear:
                MessageBoxHelper.warning(self, "Warning", f"Cache '{cache_item.name}' cannot be cleared")
                return

            # 确认对话框
            reply = MessageBoxHelper.question(
                self,
                "Confirm Clear Cache",
                f"Are you sure you want to clear '{cache_item.name}' cache?\n\n"
                f"This will free up {cache_item.size_formatted} of disk space."
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 禁用按钮
                self.btnClearSelected.setEnabled(False)
                self.btnClearAll.setEnabled(False)

                # 执行清理
                success = self.cache_manager.clear_cache(cache_item.name)

                # 重新扫描
                self._start_cache_scan()

                if success:
                    MessageBoxHelper.information(self, "Success", f"Cache '{cache_item.name}' cleared successfully")
                else:
                    MessageBoxHelper.warning(self, "Warning", f"Failed to clear cache '{cache_item.name}'")

        except Exception as e:
            logger.error(f"Error clearing selected cache: {e}")
            MessageBoxHelper.critical(self, "Error", f"Failed to clear cache: {str(e)}")

    def _clear_all_cache(self):
        """清理所有缓存"""
        try:
            # 计算可清理的缓存
            clearable_items = [item for item in self._cache_items if item.can_clear]

            if not clearable_items:
                MessageBoxHelper.information(self, "Information", "No clearable cache found")
                return

            # 计算总大小
            total_size = sum(item.size_bytes for item in clearable_items)

            # 确认对话框
            reply = MessageBoxHelper.question(
                self,
                "Confirm Clear All Cache",
                f"Are you sure you want to clear all cache?\n\n"
                f"This will delete {len(clearable_items)} cache items and free up "
                f"{self._format_size(total_size)} of disk space.\n\n"
                f"This action cannot be undone."
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 禁用按钮
                self.btnRefreshCache.setEnabled(False)
                self.btnClearSelected.setEnabled(False)
                self.btnClearAll.setEnabled(False)

                # 执行清理
                success_count, failed_count = self.cache_manager.clear_all_cache()

                # 重新扫描
                self._start_cache_scan()

                if success_count > 0:
                    MessageBoxHelper.information(
                        self,
                        "Success",
                        f"Cleared {success_count} cache items successfully"
                    )
                else:
                    MessageBoxHelper.warning(self, "Warning", "Failed to clear any cache")

        except Exception as e:
            logger.error(f"Error clearing all cache: {e}")
            MessageBoxHelper.critical(self, "Error", f"Failed to clear cache: {str(e)}")

    def _format_size(self, size_bytes: int) -> str:
        """格式化字节大小"""
        if size_bytes == 0:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        size = float(size_bytes)

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.2f} {units[unit_index]}"

    def refresh_all(self):
        """刷新所有数据"""
        try:
            logger.info("Refreshing all data...")

            # 刷新系统信息
            self._load_system_info()

            # 刷新统计数据
            self._load_statistics()

            # 刷新缓存
            self._start_cache_scan()

            logger.info("All data refreshed successfully")

        except Exception as e:
            logger.error(f"Error refreshing data: {e}")
            MessageBoxHelper.critical(self, "Error", f"Failed to refresh data: {str(e)}")

    def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up StatusPanel")
        # 记录应用关闭
        self.statistics_service.record_shutdown()
