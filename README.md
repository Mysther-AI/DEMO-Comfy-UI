# 🎬 ComfyUI HechicerIA API Extension

> AI-powered video stylization pipeline for ComfyUI — download, trim, stylize, generate, and preview animated videos entirely from within ComfyUI.

![Version](https://img.shields.io/badge/version-3.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![ComfyUI](https://img.shields.io/badge/ComfyUI-compatible-orange)

## ✨ Features

| Node | Purpose |
|------|---------|
| 🔑 **Config API Keys** | Central credential store for HechicerIA + Wavespeed APIs |
| 📁 **Project Explorer** | Browse all projects in your HechicerIA account |
| 🎞️ **Video Explorer** | List videos inside a project |
| 📥 **Subvideo Downloader** | Download subvideo clips with frame preview |
| ✂️ **Video Trimmer** | Trim clips to AI-model-compatible lengths (FFmpeg) |
| 🎨 **Image Stylizer** | Apply artistic styles via Wavespeed (Nano Banana / Hunyuan) |
| 🎬 **Video Generator** | Generate final animations (Kling / LTX) with inline player |
| ▶️ **Video Player** | Load any video path → inline preview + VHS-compatible IMAGE batch |

## 📦 Installation

### Option A — ComfyUI Manager (recommended)

Search **"HechicerIA"** in ComfyUI Manager and click Install.

### Option B — Manual

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/hechiceria/comfyui-hechiceria-api.git
pip install -r requirements.txt   # or: pip install requests imageio-ffmpeg Pillow
```

Restart ComfyUI.

## 🔧 Requirements

- **Python** ≥ 3.10
- **ComfyUI** (latest)
- **FFmpeg** — installed automatically via `imageio-ffmpeg`, or system-wide
- **API Keys** — [HechicerIA](https://hechicer-ia.com) + [Wavespeed](https://wavespeed.ai)

## 🚀 Quick Start

1. Add a **🔑 Config API Keys** node and paste your keys.
2. Wire `api_keys` → **📁 Project Explorer** → read your project IDs.
3. Wire `api_keys` → **🎞️ Video Explorer** → select a project → read video IDs.
4. Wire `api_keys` → **📥 Subvideo Downloader** → enter IDs → download a clip.
5. Feed the clip into **✂️ Video Trimmer** (0–5 s recommended).
6. Load a reference image → **🎨 Image Stylizer** to transform it.
7. Combine styled image + trimmed video in **🎬 Video Generator**.
8. Connect the `final_video_path` output to **▶️ Video Player** for an inline preview and VHS-compatible frame output.

A ready-to-use workflow JSON is included in the repository.

## 🌍 Language Support

This extension supports **ComfyUI's native localization system**.

To switch to Spanish:

1. Open ComfyUI Settings (gear icon).
2. Set language to **Español**.
3. All node names, descriptions, and tooltips will display in Spanish.

The translation files live in `locales/es/nodeDefs.json`.

### Adding a New Language

```
locales/
└── <language_code>/       # e.g. "fr", "pt", "ja"
    └── nodeDefs.json
```

Copy `locales/es/nodeDefs.json` as a template and translate the values.

## 🎥 VHS Integration

The **▶️ Video Player** node bridges the text-path outputs from this extension into the VHS (Video Helper Suite) ecosystem:

- **Input**: any `STRING` video path (from Generator, Trimmer, or Downloader)
- **Output**: `IMAGE` batch (frame tensor), `frame_count`, `fps`, `audio_path`
- **Canvas**: renders an inline video player automatically

Wire the `frames` output to any VHS node (e.g. **Video Combine**) for further compositing.

## 📁 Project Structure

```
comfyui-hechiceria-api/
├── __init__.py              # Extension entry point
├── nodes.py                 # All node definitions
├── README.md
├── locales/
│   └── es/
│       └── nodeDefs.json    # Spanish translations
└── workflows/
    └── Workflow_HechicerIA.json
```

## 📝 License

MIT — © 2025 HechicerIA
