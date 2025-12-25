"""
统计服务 - 管理应用使用统计数据

设计模式:
- 单例模式: 全局唯一实例
- 观察者模式: 统计数据变更通知

职责:
- 记录和追踪应用使用统计
- 持久化统计数据
- 提供统计查询接口
"""

import os
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
from loguru import logger


@dataclass
class UsageStatistics:
    """使用统计数据类"""
    # 基础统计
    first_launch_date: str = ""      # 首次启动日期
    last_launch_date: str = ""       # 最后启动日期
    total_launches: int = 0          # 总启动次数
    total_usage_days: int = 0        # 总使用天数

    # 音频生成统计
    total_audio_generated: int = 0   # 总生成音频数量
    total_audio_duration: float = 0.0  # 总音频时长（秒）

    # 模型使用统计
    model_usage_count: Dict[str, int] = field(default_factory=dict)  # 各模型使用次数

    # 时间统计
    total_usage_time: float = 0.0    # 总使用时长（秒）
    last_session_duration: float = 0.0  # 上次会话时长（秒）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UsageStatistics':
        """从字典创建"""
        return cls(**data)


class StatisticsService:
    """
    统计服务

    单例模式，全局唯一实例

    职责:
    - 记录应用启动和使用
    - 追踪音频生成统计
    - 持久化统计数据
    - 提供统计查询和重置功能
    """

    _instance: Optional['StatisticsService'] = None
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

        # 配置
        from backend.path_manager import PathManager
        self.path_manager = PathManager()
        self.stats_file = os.path.join(
            self.path_manager.get_config_path(),
            "statistics.json"
        )

        # 数据
        self._stats: Optional[UsageStatistics] = None
        self._stats_lock = threading.RLock()

        # 会话追踪
        self._session_start_time: Optional[float] = None
        self._session_date: Optional[str] = None

        # 加载统计数据
        self._load_statistics()

        logger.info("[StatisticsService] Statistics service initialized")

    def _load_statistics(self):
        """加载统计数据"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._stats = UsageStatistics.from_dict(data)
                logger.info("[StatisticsService] Statistics loaded from file")
            else:
                # 首次启动，初始化统计数据
                self._stats = UsageStatistics()
                self._save_statistics()
                logger.info("[StatisticsService] Initialized new statistics")
        except Exception as e:
            logger.error(f"[StatisticsService] Error loading statistics: {e}")
            self._stats = UsageStatistics()

    def _save_statistics(self) -> bool:
        """保存统计数据"""
        try:
            with self._stats_lock:
                # 确保目录存在
                os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)

                # 保存到文件
                with open(self.stats_file, 'w', encoding='utf-8') as f:
                    json.dump(self._stats.to_dict(), f, indent=2, ensure_ascii=False)

                logger.debug("[StatisticsService] Statistics saved")
                return True

        except Exception as e:
            logger.error(f"[StatisticsService] Error saving statistics: {e}")
            return False

    def record_launch(self):
        """记录应用启动"""
        try:
            with self._stats_lock:
                now = datetime.now()
                now_str = now.strftime("%Y-%m-%d %H:%M:%S")
                now_date = now.strftime("%Y-%m-%d")

                # 首次启动
                if not self._stats.first_launch_date:
                    self._stats.first_launch_date = now_str
                    self._stats.total_usage_days = 1
                else:
                    # 检查是否是新的一天
                    last_date = datetime.strptime(
                        self._stats.last_launch_date.split()[0],
                        "%Y-%m-%d"
                    ).strftime("%Y-%m-%d")

                    if now_date != last_date:
                        self._stats.total_usage_days += 1

                # 更新最后启动时间
                self._stats.last_launch_date = now_str

                # 增加启动次数
                self._stats.total_launches += 1

                # 记录会话开始时间
                self._session_start_time = time.time()
                self._session_date = now_date

                # 保存
                self._save_statistics()

                logger.info(f"[StatisticsService] Application launch recorded (total: {self._stats.total_launches})")

        except Exception as e:
            logger.error(f"[StatisticsService] Error recording launch: {e}")

    def record_shutdown(self):
        """记录应用关闭"""
        try:
            with self._stats_lock:
                if self._session_start_time is None:
                    return

                # 计算本次会话时长
                session_duration = time.time() - self._session_start_time

                # 更新会话时长
                self._stats.last_session_duration = session_duration
                self._stats.total_usage_time += session_duration

                # 保存
                self._save_statistics()

                logger.info(f"[StatisticsService] Application shutdown recorded (session: {session_duration:.1f}s)")

                # 重置会话
                self._session_start_time = None
                self._session_date = None

        except Exception as e:
            logger.error(f"[StatisticsService] Error recording shutdown: {e}")

    def record_audio_generation(self, duration: float, model_id: str = ""):
        """
        记录音频生成

        Args:
            duration: 音频时长（秒）
            model_id: 使用的模型ID
        """
        try:
            with self._stats_lock:
                # 更新音频生成统计
                self._stats.total_audio_generated += 1
                self._stats.total_audio_duration += duration

                # 更新模型使用统计
                if model_id:
                    if model_id not in self._stats.model_usage_count:
                        self._stats.model_usage_count[model_id] = 0
                    self._stats.model_usage_count[model_id] += 1

                # 保存
                self._save_statistics()

                logger.debug(f"[StatisticsService] Audio generation recorded (duration: {duration:.1f}s, model: {model_id})")

        except Exception as e:
            logger.error(f"[StatisticsService] Error recording audio generation: {e}")

    def get_statistics(self) -> UsageStatistics:
        """获取当前统计数据"""
        with self._stats_lock:
            return self._stats

    def get_formatted_statistics(self) -> Dict[str, str]:
        """
        获取格式化的统计数据（用于UI显示）

        Returns:
            Dict: 格式化的统计数据
        """
        with self._stats_lock:
            stats = self._stats

            # 计算使用天数（从首次启动到今天）
            usage_days = stats.total_usage_days

            # 格式化使用时长
            total_hours = stats.total_usage_time / 3600
            usage_time_str = f"{total_hours:.1f} hours"

            # 格式化音频时长
            audio_minutes = stats.total_audio_duration / 60
            if audio_minutes >= 60:
                audio_duration_str = f"{audio_minutes / 60:.1f} hours"
            else:
                audio_duration_str = f"{audio_minutes:.1f} minutes"

            # 找出最常用的模型
            most_used_model = "None"
            if stats.model_usage_count:
                most_used_model = max(stats.model_usage_count, key=stats.model_usage_count.get)

            return {
                "First Launch": stats.first_launch_date,
                "Last Launch": stats.last_launch_date,
                "Total Launches": str(stats.total_launches),
                "Usage Days": str(usage_days),
                "Total Usage Time": usage_time_str,
                "Last Session Duration": f"{stats.last_session_duration / 60:.1f} minutes",
                "Total Audio Generated": str(stats.total_audio_generated),
                "Total Audio Duration": audio_duration_str,
                "Most Used Model": most_used_model,
                "Average Audio Duration": f"{stats.total_audio_duration / max(stats.total_audio_generated, 1):.1f} seconds" if stats.total_audio_generated > 0 else "N/A",
            }

    def reset_statistics(self) -> bool:
        """
        重置所有统计数据

        Returns:
            bool: 是否成功
        """
        try:
            with self._stats_lock:
                # 备份旧统计
                backup_file = self.stats_file + ".backup"
                if os.path.exists(self.stats_file):
                    import shutil
                    shutil.copy2(self.stats_file, backup_file)
                    logger.info(f"[StatisticsService] Statistics backed up to {backup_file}")

                # 重置统计
                self._stats = UsageStatistics()
                self._save_statistics()

                logger.info("[StatisticsService] Statistics reset successfully")
                return True

        except Exception as e:
            logger.error(f"[StatisticsService] Error resetting statistics: {e}")
            return False

    def export_statistics(self, export_path: str) -> bool:
        """
        导出统计数据

        Args:
            export_path: 导出文件路径

        Returns:
            bool: 是否成功
        """
        try:
            with self._stats_lock:
                export_file = Path(export_path)
                export_file.parent.mkdir(parents=True, exist_ok=True)

                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(self._stats.to_dict(), f, indent=2, ensure_ascii=False)

                logger.info(f"[StatisticsService] Statistics exported to {export_path}")
                return True

        except Exception as e:
            logger.error(f"[StatisticsService] Error exporting statistics: {e}")
            return False

    def get_model_usage_stats(self) -> Dict[str, int]:
        """获取模型使用统计"""
        with self._stats_lock:
            return self._stats.model_usage_count.copy()


# ==================== 全局实例 ====================

_statistics_service: Optional[StatisticsService] = None


def get_statistics_service() -> StatisticsService:
    """获取全局统计服务实例"""
    global _statistics_service
    if _statistics_service is None:
        _statistics_service = StatisticsService()
    return _statistics_service


if __name__ == "__main__":
    # 测试统计服务
    print("=" * 60)
    print("统计服务测试")
    print("=" * 60)

    service = get_statistics_service()

    # 记录启动
    service.record_launch()

    # 获取统计
    formatted = service.get_formatted_statistics()

    print(f"\n使用统计:")
    for key, value in formatted.items():
        print(f"  {key}: {value}")

    # 记录一些音频生成
    service.record_audio_generation(15.5, "cosyvoice3_2512")
    service.record_audio_generation(22.3, "cosyvoice2")
    service.record_audio_generation(18.7, "cosyvoice3_2512")

    # 再次获取统计
    formatted = service.get_formatted_statistics()

    print(f"\n更新后的统计:")
    for key, value in formatted.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
