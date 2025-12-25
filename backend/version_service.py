"""
版本更新检查服务

设计模式:
- 单例模式: 全局唯一实例

职责:
- 检查GitHub最新版本
- 比较版本号
- 提供更新信息
"""

import threading
from typing import Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class UpdateInfo:
    """更新信息"""
    has_update: bool                   # 是否有更新
    current_version: str               # 当前版本
    latest_version: str                # 最新版本
    download_url: str                  # 下载链接
    release_notes: str                 # 发布说明


class VersionService:
    """
    版本更新检查服务

    单例模式，全局唯一实例

    职责:
    - 检查GitHub最新版本
    - 比较版本号
    - 提供更新信息
    """

    _instance: Optional['VersionService'] = None
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

        # GitHub仓库信息（需要用户设置）
        self.github_owner = "3uyuan1ee"
        self.github_repo = "CosyVoice_app"
        self.current_version = "1.0.0"

        logger.info("[VersionService] Version service initialized")

    def set_github_repo(self, owner: str, repo: str):
        """设置GitHub仓库信息"""
        self.github_owner = owner
        self.github_repo = repo
        logger.info(f"[VersionService] GitHub repo set to {owner}/{repo}")

    def set_current_version(self, version: str):
        """设置当前版本"""
        self.current_version = version
        logger.info(f"[VersionService] Current version: {version}")

    def check_for_updates(self) -> UpdateInfo:
        """
        检查更新

        Returns:
            UpdateInfo: 更新信息
        """
        try:
            logger.info("[VersionService] Checking for updates...")

            if not self.github_owner or not self.github_repo:
                logger.warning("[VersionService] GitHub repo not configured")
                return self._get_no_update_info()

            # 尝试获取最新版本
            latest_version = self._fetch_latest_version()

            if not latest_version:
                logger.info("[VersionService] Could not fetch latest version")
                return self._get_no_update_info()

            # 比较版本
            has_update = self._compare_versions(self.current_version, latest_version)

            logger.info(f"[VersionService] Update check: current={self.current_version}, latest={latest_version}, has_update={has_update}")

            return UpdateInfo(
                has_update=has_update,
                current_version=self.current_version,
                latest_version=latest_version,
                download_url=f"https://github.com/{self.github_owner}/{self.github_repo}/releases/latest",
                release_notes="Please visit GitHub for release notes"
            )

        except Exception as e:
            logger.error(f"[VersionService] Error checking for updates: {e}")
            return self._get_no_update_info()

    def _fetch_latest_version(self) -> Optional[str]:
        """获取最新版本号"""
        try:
            import requests

            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/releases/latest"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            tag_name = data.get("tag_name", "")

            # 移除 'v' 前缀
            if tag_name.startswith('v'):
                tag_name = tag_name[1:]

            return tag_name

        except ImportError:
            logger.warning("[VersionService] requests library not available")
            return None
        except Exception as e:
            logger.error(f"[VersionService] Error fetching version: {e}")
            return None

    def _compare_versions(self, current: str, latest: str) -> bool:
        """比较版本号"""
        try:
            current_parts = [int(x) for x in current.split('.')]
            latest_parts = [int(x) for x in latest.split('.')]

            # 补齐长度
            max_len = max(len(current_parts), len(latest_parts))
            current_parts += [0] * (max_len - len(current_parts))
            latest_parts += [0] * (max_len - len(latest_parts))

            return latest_parts > current_parts

        except Exception:
            logger.warning(f"[VersionService] Failed to compare versions: {current} vs {latest}")
            return False

    def _get_no_update_info(self) -> UpdateInfo:
        """获取无更新信息"""
        return UpdateInfo(
            has_update=False,
            current_version=self.current_version,
            latest_version=self.current_version,
            download_url="",
            release_notes=""
        )


# ==================== 全局实例 ====================

_version_service: Optional[VersionService] = None


def get_version_service() -> VersionService:
    """获取全局版本服务实例"""
    global _version_service
    if _version_service is None:
        _version_service = VersionService()
    return _version_service
