"""
配置管理模块 - 统一管理应用配置
- YAML格式配置文件
- 分层配置(默认配置 + 用户配置)
- 配置验证和类型检查
- 热重载支持
- 环境变量覆盖
"""

import os
import yaml
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, TypeVar, Type
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class ConfigSource(Enum):
    """配置来源"""
    DEFAULT = "default"      # 默认配置
    USER = "user"            # 用户配置
    ENV = "environment"      # 环境变量
    CLI = "cli"             # 命令行参数


@dataclass
class AppConfig:
    """应用配置类"""

    # 音频处理配置
    audio_sample_rate: int = 24000
    audio_channels: int = 1
    audio_bitrate: int = 128

    # 模型配置
    default_model: str = "cosyvoice3_2512"
    model_cache_dir: Optional[str] = None
    enable_vllm: bool = False
    enable_fp16: bool = False
    device: str = "auto"  # auto, cuda, mps, cpu

    # 音频预处理配置
    enable_preprocessing: bool = True
    enable_denoise: bool = True
    enable_normalize: bool = True
    enable_trim_silence: bool = True
    target_sample_rate: int = 24000

    # 音调调整配置
    enable_pitch_shift: bool = True
    default_pitch_shift: float = 0.0
    pitch_shift_quality: str = "balanced"  # fast, balanced, high_quality

    # UI配置
    ui_theme: str = "pixel_dark"
    ui_language: str = "en"
    window_width: int = 800
    window_height: int = 550

    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None
    log_max_size: int = 10  # MB
    log_backup_count: int = 5

    # 性能配置
    max_concurrent_generations: int = 1
    max_concurrent_downloads: int = 3
    generation_timeout: int = 300  # seconds
    download_timeout: int = 600  # seconds

    # 路径配置
    output_dir: Optional[str] = None
    temp_dir: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """从字典创建配置"""
        # 过滤掉不存在的字段
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)

    def validate(self) -> List[str]:
        """验证配置"""
        errors = []

        # 验证音频采样率
        if self.audio_sample_rate not in [8000, 16000, 22050, 24000, 44100, 48000]:
            errors.append(f"Invalid audio_sample_rate: {self.audio_sample_rate}")

        # 验证模型设备
        if self.device not in ["auto", "cuda", "mps", "cpu"]:
            errors.append(f"Invalid device: {self.device}")

        # 验证音调质量
        if self.pitch_shift_quality not in ["fast", "balanced", "high_quality"]:
            errors.append(f"Invalid pitch_shift_quality: {self.pitch_shift_quality}")

        # 验证日志级别
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            errors.append(f"Invalid log_level: {self.log_level}")

        # 验证数值范围
        if not (0 <= self.default_pitch_shift <= 12):
            errors.append(f"default_pitch_shift must be between 0 and 12")

        if self.max_concurrent_generations < 1:
            errors.append("max_concurrent_generations must be >= 1")

        if self.max_concurrent_downloads < 1:
            errors.append("max_concurrent_downloads must be >= 1")

        return errors


class ConfigChangeObserver:
    """配置变更观察者基类"""

    def on_config_changed(self, config: AppConfig, changed_keys: List[str]):
        """配置变更回调"""
        pass


class ConfigManager:
    """
    配置管理器

    单例模式,全局唯一配置实例

    职责:
    - 加载和保存配置
    - 配置验证
    - 配置变更通知
    - 热重载
    """

    _instance: Optional['ConfigManager'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_dir: Optional[str] = None):
        # 避免重复初始化
        if hasattr(self, '_initialized'):
            return

        self._initialized = True

        # 配置目录
        if config_dir is None:
            from backend.path_manager import PathManager
            path_manager = PathManager()
            config_dir = path_manager.get_config_path()

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 配置文件路径
        self.default_config_file = self.config_dir / "config.default.yaml"
        self.user_config_file = self.config_dir / "config.yaml"

        # 当前配置
        self._config: Optional[AppConfig] = None
        self._config_lock = threading.RLock()

        # 观察者
        self._observers: List[ConfigChangeObserver] = []

        # 加载配置
        self._load_config()

    def _load_config(self):
        """加载配置"""
        logger.info("[ConfigManager] Loading configuration...")

        # 1. 加载默认配置
        default_config = self._load_default_config()

        # 2. 加载用户配置(如果存在)
        user_config = self._load_user_config()

        # 3. 合并配置(用户配置覆盖默认配置)
        merged_dict = {**default_config, **user_config}

        # 4. 应用环境变量覆盖
        env_config = self._load_env_config()
        merged_dict.update(env_config)

        # 5. 创建配置对象
        self._config = AppConfig.from_dict(merged_dict)

        # 6. 验证配置
        errors = self._config.validate()
        if errors:
            logger.warning(f"[ConfigManager] Configuration validation errors:")
            for error in errors:
                logger.warning(f"  - {error}")

        logger.info("[ConfigManager] Configuration loaded successfully")

    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        # 如果默认配置文件存在,从文件加载
        if self.default_config_file.exists():
            try:
                with open(self.default_config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    logger.info(f"[ConfigManager] Loaded default config from {self.default_config_file}")
                    return config or {}
            except Exception as e:
                logger.error(f"[ConfigManager] Failed to load default config: {e}")

        # 否则使用硬编码的默认配置
        default_config = AppConfig().to_dict()
        self._save_default_config(default_config)
        return default_config

    def _load_user_config(self) -> Dict[str, Any]:
        """加载用户配置"""
        if not self.user_config_file.exists():
            logger.info("[ConfigManager] No user config file found")
            return {}

        try:
            with open(self.user_config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"[ConfigManager] Loaded user config from {self.user_config_file}")
                return config or {}
        except Exception as e:
            logger.error(f"[ConfigManager] Failed to load user config: {e}")
            return {}

    def _load_env_config(self) -> Dict[str, Any]:
        """加载环境变量配置"""
        env_config = {}

        # 支持的环境变量映射
        env_mappings = {
            "COSYVOICE_MODEL_DIR": "model_cache_dir",
            "COSYVOICE_DEVICE": "device",
            "COSYVOICE_LOG_LEVEL": "log_level",
            "COSYVOICE_OUTPUT_DIR": "output_dir",
            "COSYVOICE_ENABLE_VLLM": "enable_vllm",
        }

        for env_var, config_key in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                # 类型转换
                if config_key == "enable_vllm":
                    value = value.lower() in ("true", "1", "yes", "on")
                env_config[config_key] = value
                logger.info(f"[ConfigManager] Env override: {config_key}={value}")

        return env_config

    def _save_default_config(self, config: Dict[str, Any]):
        """保存默认配置"""
        try:
            with open(self.default_config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"[ConfigManager] Saved default config to {self.default_config_file}")
        except Exception as e:
            logger.error(f"[ConfigManager] Failed to save default config: {e}")

    def save_user_config(self) -> bool:
        """保存用户配置"""
        try:
            with self._config_lock:
                if self._config is None:
                    return False

                with open(self.user_config_file, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(
                        self._config.to_dict(),
                        f,
                        default_flow_style=False,
                        allow_unicode=True
                    )

                logger.info(f"[ConfigManager] Saved user config to {self.user_config_file}")
                return True

        except Exception as e:
            logger.error(f"[ConfigManager] Failed to save user config: {e}")
            return False

    def reload(self) -> bool:
        """重新加载配置"""
        try:
            logger.info("[ConfigManager] Reloading configuration...")
            old_config = self._config

            self._load_config()

            # 检查变更
            if old_config:
                changed_keys = self._get_changed_keys(old_config, self._config)
                if changed_keys:
                    logger.info(f"[ConfigManager] Configuration changed: {changed_keys}")
                    self._notify_observers(changed_keys)
                else:
                    logger.info("[ConfigManager] No configuration changes detected")

            return True

        except Exception as e:
            logger.error(f"[ConfigManager] Failed to reload config: {e}")
            return False

    def _get_changed_keys(self, old_config: AppConfig, new_config: AppConfig) -> List[str]:
        """获取变更的配置键"""
        changed = []
        old_dict = old_config.to_dict()
        new_dict = new_config.to_dict()

        for key in old_dict.keys():
            if old_dict[key] != new_dict.get(key):
                changed.append(key)

        return changed

    def register_observer(self, observer: ConfigChangeObserver):
        """注册配置变更观察者"""
        if observer not in self._observers:
            self._observers.append(observer)
            logger.debug(f"[ConfigManager] Registered observer: {observer.__class__.__name__}")

    def unregister_observer(self, observer: ConfigChangeObserver):
        """注销配置变更观察者"""
        if observer in self._observers:
            self._observers.remove(observer)
            logger.debug(f"[ConfigManager] Unregistered observer: {observer.__class__.__name__}")

    def _notify_observers(self, changed_keys: List[str]):
        """通知观察者配置变更"""
        for observer in self._observers:
            try:
                observer.on_config_changed(self._config, changed_keys)
            except Exception as e:
                logger.error(f"[ConfigManager] Observer notification failed: {e}")

    # ==================== 配置访问接口 ====================

    def get_config(self) -> AppConfig:
        """获取当前配置"""
        with self._config_lock:
            return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        with self._config_lock:
            if self._config is None:
                return default
            return getattr(self._config, key, default)

    def set(self, key: str, value: Any, notify: bool = True) -> bool:
        """设置配置项"""
        try:
            with self._config_lock:
                if self._config is None:
                    return False

                # 检查字段是否存在
                if not hasattr(self._config, key):
                    logger.warning(f"[ConfigManager] Unknown config key: {key}")
                    return False

                # 记录旧值
                old_value = getattr(self._config, key)

                # 设置新值
                setattr(self._config, key, value)

                # 通知观察者
                if notify and old_value != value:
                    self._notify_observers([key])

                logger.debug(f"[ConfigManager] Config updated: {key}={value}")
                return True

        except Exception as e:
            logger.error(f"[ConfigManager] Failed to set config: {e}")
            return False

    def update(self, updates: Dict[str, Any], notify: bool = True) -> bool:
        """批量更新配置"""
        try:
            with self._config_lock:
                if self._config is None:
                    return False

                changed_keys = []

                for key, value in updates.items():
                    if hasattr(self._config, key):
                        old_value = getattr(self._config, key)
                        setattr(self._config, key, value)
                        if old_value != value:
                            changed_keys.append(key)
                    else:
                        logger.warning(f"[ConfigManager] Unknown config key: {key}")

                # 验证更新后的配置
                errors = self._config.validate()
                if errors:
                    logger.error(f"[ConfigManager] Configuration validation failed after update:")
                    for error in errors:
                        logger.error(f"  - {error}")
                    return False

                # 通知观察者
                if notify and changed_keys:
                    self._notify_observers(changed_keys)

                if changed_keys:
                    logger.info(f"[ConfigManager] Config updated: {changed_keys}")

                return True

        except Exception as e:
            logger.error(f"[ConfigManager] Failed to update config: {e}")
            return False

    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        try:
            logger.info("[ConfigManager] Resetting to default configuration...")

            # 删除用户配置文件
            if self.user_config_file.exists():
                self.user_config_file.unlink()
                logger.info(f"[ConfigManager] Removed user config file")

            # 重新加载配置
            self._load_config()

            # 通知观察者
            self._notify_observers(list(self._config.to_dict().keys()))

            return True

        except Exception as e:
            logger.error(f"[ConfigManager] Failed to reset config: {e}")
            return False

    def export_config(self, export_path: str) -> bool:
        """导出配置到文件"""
        try:
            with self._config_lock:
                if self._config is None:
                    return False

                export_file = Path(export_path)
                export_file.parent.mkdir(parents=True, exist_ok=True)

                with open(export_file, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(
                        self._config.to_dict(),
                        f,
                        default_flow_style=False,
                        allow_unicode=True
                    )

                logger.info(f"[ConfigManager] Exported config to {export_path}")
                return True

        except Exception as e:
            logger.error(f"[ConfigManager] Failed to export config: {e}")
            return False

    def import_config(self, import_path: str, merge: bool = True) -> bool:
        """从文件导入配置"""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                logger.error(f"[ConfigManager] Import file not found: {import_path}")
                return False

            with open(import_file, 'r', encoding='utf-8') as f:
                imported_config = yaml.safe_load(f)

            if merge:
                # 合并模式: 更新现有配置
                return self.update(imported_config)
            else:
                # 替换模式: 完全替换配置
                with self._config_lock:
                    self._config = AppConfig.from_dict(imported_config)

                    # 验证配置
                    errors = self._config.validate()
                    if errors:
                        logger.error(f"[ConfigManager] Imported config validation failed:")
                        for error in errors:
                            logger.error(f"  - {error}")
                        return False

                    # 通知观察者
                    self._notify_observers(list(self._config.to_dict().keys()))

                    logger.info(f"[ConfigManager] Imported config from {import_path}")
                    return True

        except Exception as e:
            logger.error(f"[ConfigManager] Failed to import config: {e}")
            return False


# ==================== 全局配置实例 ====================

_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> AppConfig:
    """便捷函数: 获取当前配置"""
    return get_config_manager().get_config()


if __name__ == "__main__":
    # 测试配置管理器
    print("=" * 60)
    print("配置管理器测试")
    print("=" * 60)

    # 创建配置管理器
    config_mgr = get_config_manager()

    # 打印当前配置
    config = config_mgr.get_config()
    print(f"\n当前配置:")
    print(f"  音频采样率: {config.audio_sample_rate}")
    print(f"  默认模型: {config.default_model}")
    print(f"  设备: {config.device}")
    print(f"  日志级别: {config.log_level}")

    # 测试配置更新
    print("\n测试配置更新...")
    config_mgr.set("log_level", "DEBUG")
    print(f"更新后的日志级别: {config_mgr.get('log_level')}")

    # 测试配置验证
    errors = config.validate()
    if errors:
        print("\n配置验证错误:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✓ 配置验证通过")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
