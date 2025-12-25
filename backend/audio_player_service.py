"""
音频播放服务 - 提供统一的音频播放接口

使用 PyQt6 的 QMediaPlayer 实现音频播放功能
"""

from typing import Optional
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl, QObject, pyqtSignal, QCoreApplication
from loguru import logger
import os


class PlayerSignals(QObject):
    """播放器信号"""
    position_changed = pyqtSignal(int)  # 播放位置变化 (ms)
    duration_changed = pyqtSignal(int)  # 音频时长变化 (ms)
    playback_state_changed = pyqtSignal(str)  # 播放状态变化
    error_occurred = pyqtSignal(str)  # 播放错误


class AudioPlayerService(QObject):
    """
    音频播放服务

    提供：
    - 播放、暂停、停止
    - 音量控制
    - 进度控制
    - 状态查询
    """

    _instance: Optional['AudioPlayerService'] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            # 创建实例时，不需要传递parent参数
            # QObject单例不应该有parent，以避免父子对象生命周期冲突
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, parent=None):
        # 避免重复初始化 - 必须在super().__init__之前检查
        if self._initialized:
            return

        # 先调用父类初始化（QObject需要）
        # 单例模式不使用parent，以避免生命周期冲突
        super().__init__(parent=None)

        # 标记已初始化
        self._initialized = True

        # 创建播放器组件，设置父对象防止被垃圾回收
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)

        # 创建信号对象，设置父对象防止被垃圾回收
        self.signals = PlayerSignals(self)

        # 当前状态
        self._current_file: Optional[str] = None
        self._is_playing = False

        # 连接播放器信号
        self._connect_signals()

        logger.info("AudioPlayerService initialized")

    def _connect_signals(self):
        """连接播放器内部信号"""
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.playbackStateChanged.connect(self._on_state_changed)
        self.media_player.errorChanged.connect(self._on_error)

    def _on_position_changed(self, position: int):
        """播放位置变化"""
        self.signals.position_changed.emit(position)

    def _on_duration_changed(self, duration: int):
        """音频时长变化"""
        self.signals.duration_changed.emit(duration)

    def _on_state_changed(self, state):
        """播放状态变化"""
        from PyQt6.QtMultimedia import QMediaPlayer

        state_map = {
            QMediaPlayer.PlaybackState.StoppedState: "stopped",
            QMediaPlayer.PlaybackState.PlayingState: "playing",
            QMediaPlayer.PlaybackState.PausedState: "paused",
        }

        state_str = state_map.get(state, "unknown")
        self._is_playing = (state == QMediaPlayer.PlaybackState.PlayingState)
        self.signals.playback_state_changed.emit(state_str)

        logger.debug(f"Playback state changed to: {state_str}")

    def _on_error(self):
        """处理播放错误"""
        error = self.media_player.errorString()
        logger.error(f"Playback error: {error}")
        self.signals.error_occurred.emit(error)

    def load_file(self, file_path: str) -> bool:
        """
        加载音频文件

        Args:
            file_path: 音频文件路径

        Returns:
            bool: 是否加载成功
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False

            # 检查文件格式
            valid_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in valid_extensions:
                logger.error(f"Unsupported audio format: {ext}")
                return False

            # 加载文件
            url = QUrl.fromLocalFile(file_path)
            self.media_player.setSource(url)

            self._current_file = file_path
            logger.info(f"Loaded audio file: {file_path}")

            return True

        except Exception as e:
            logger.error(f"Error loading audio file: {e}")
            return False

    def play(self) -> bool:
        """
        开始播放

        Returns:
            bool: 是否成功开始播放
        """
        try:
            if not self._current_file:
                logger.warning("No audio file loaded")
                return False

            self.media_player.play()
            logger.info("Playback started")
            return True

        except Exception as e:
            logger.error(f"Error starting playback: {e}")
            return False

    def pause(self) -> bool:
        """
        暂停播放

        Returns:
            bool: 是否成功暂停
        """
        try:
            self.media_player.pause()
            logger.info("Playback paused")
            return True

        except Exception as e:
            logger.error(f"Error pausing playback: {e}")
            return False

    def stop(self) -> bool:
        """
        停止播放

        Returns:
            bool: 是否成功停止
        """
        try:
            self.media_player.stop()
            logger.info("Playback stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping playback: {e}")
            return False

    def set_position(self, position_ms: int) -> bool:
        """
        设置播放位置

        Args:
            position_ms: 位置（毫秒）

        Returns:
            bool: 是否成功设置
        """
        try:
            self.media_player.setPosition(position_ms)
            logger.debug(f"Position set to {position_ms}ms")
            return True

        except Exception as e:
            logger.error(f"Error setting position: {e}")
            return False

    def set_volume(self, volume: int) -> bool:
        """
        设置音量

        Args:
            volume: 音量 (0-100)

        Returns:
            bool: 是否成功设置
        """
        try:
            volume = max(0, min(100, volume))  # 限制在0-100范围
            self.audio_output.setVolume(volume / 100.0)
            logger.debug(f"Volume set to {volume}")
            return True

        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False

    def get_position(self) -> int:
        """
        获取当前播放位置

        Returns:
            int: 位置（毫秒）
        """
        return self.media_player.position()

    def get_duration(self) -> int:
        """
        获取音频总时长

        Returns:
            int: 时长（毫秒）
        """
        return self.media_player.duration()

    def is_playing(self) -> bool:
        """
        是否正在播放

        Returns:
            bool: 是否正在播放
        """
        return self._is_playing

    def get_current_file(self) -> Optional[str]:
        """
        获取当前加载的文件

        Returns:
            文件路径或None
        """
        return self._current_file

    def get_state(self) -> str:
        """
        获取播放状态

        Returns:
            状态字符串: "stopped", "playing", "paused"
        """
        from PyQt6.QtMultimedia import QMediaPlayer

        state = self.media_player.playbackState()
        state_map = {
            QMediaPlayer.PlaybackState.StoppedState: "stopped",
            QMediaPlayer.PlaybackState.PlayingState: "playing",
            QMediaPlayer.PlaybackState.PausedState: "paused",
        }

        return state_map.get(state, "unknown")

    def cleanup(self):
        """清理资源"""
        try:
            self.stop()
            self.media_player.setSource(QUrl())
            logger.info("AudioPlayerService cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# 全局服务实例
_audio_player_service: Optional[AudioPlayerService] = None


def get_audio_player_service() -> AudioPlayerService:
    """获取音频播放服务实例"""
    global _audio_player_service
    if _audio_player_service is None:
        _audio_player_service = AudioPlayerService()
    return _audio_player_service
