![illustrator.png](resources/png/illustrator.png)
# CosyVoice Desktop Application

A **PyQt6-based** cross-platform desktop interface for **CosyVoice3** intelligent voice synthesis, featuring a unique **pixel-art** aesthetic.

---

## System Requirements

* **OS**: macOS 11+, Windows 10+, or Ubuntu 20.04+
* **Python**: 3.10
* **RAM**: 8GB (16GB Recommended)
* **GPU**: Optional (Supports NVIDIA CUDA & Apple Silicon MPS)

---

## Architecture

The application follows a clean layered structure to ensure stability and performance:

1. **Presentation**: PyQt6 UI with retro pixel-art styling.
2. **Controller**: Event handling and UI logic.
3. **Service**: Business logic encapsulation.
4. **Worker**: Asynchronous task processing via `QThread`.
5. **Core**: CosyVoice3, PyTorch, and audio processing engine.

---

## Usage Guide

### Audio Cloning

* **Reference Audio**: Select a clear `.wav` file via the **BROWSE** button.
* **Model Selection**: Choose your preferred CosyVoice model from the dropdown.
* **Synthesis**: Enter your text (supports multiple languages) and adjust the **Pitch** (-12 to +12).
* **Generate**: Click **GENERATE** and wait for the progress bar to complete.

### Model Management

Access the **MODEL DOWNLOAD** page to manage your synthesis engines:

* View real-time download speed and progress.
* Download individual models or use **DOWNLOAD ALL**.
* **Refresh** to update current model statuses.

---

## Supported Models

| Model Name | Size | Description |
| --- | --- | --- |
| **CosyVoice3-0.5B-2512** | ~1.2 GB | Latest flagship model (Recommended) |
| **CosyVoice2-0.5B** | ~980 MB | Balanced performance |
| **CosyVoice-300M** | ~600 MB | Lightweight and fast |
| **CosyVoice-TTSFRD** | ~550 MB | Optimized for fast response |

---

**Built with PyQt6 + CosyVoice3**