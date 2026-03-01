import os, json, time, base64, subprocess, shutil
import urllib.request, urllib.error
import numpy as np
from io import BytesIO
from PIL import Image
import torch
import folder_paths

# ---------------------------------------------------------------------------
# Constants & Helpers
# ---------------------------------------------------------------------------
HECHICERIA_BASE = "https://dev.hechicer-ia.com/api/currentanima/v1"
CATEGORY = "HechicerIA_V3"

def _handle_api_error(e):
    try:
        err_body = e.read().decode("utf-8", "replace")
        err_json = json.loads(err_body)
        msg = err_json.get("message") or err_json.get("error") or err_body
        print(f"❌ API ERROR {e.code}: {msg}")
        return f"⚠️ API ERROR ({e.code}): {msg}"
    except Exception:
        print(f"❌ API ERROR {e.code}: (Could not parse error body)")
        return f"⚠️ API ERROR ({e.code})"

def _http(url, api_key, method="GET", data=None):
    headers = {"Authorization": f"Bearer {api_key}"}
    if data:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(_handle_api_error(e))
    except Exception as e:
        raise RuntimeError(f"Network Error: {e}")

def _download_file(url, path):
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-agent", "Mozilla/5.0")]
    urllib.request.install_opener(opener)
    urllib.request.urlretrieve(url, path)

def _img_to_b64(t):
    if t.ndim == 4:
        t = t[0]
    arr = (t.cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
    buf = BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

def _video_to_b64(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Video not found at: {file_path}")
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    return f"data:video/{ext};base64,{encoded}"

def _get_ffmpeg():
    import sys
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "imageio-ffmpeg"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        raise RuntimeError(f"Could not locate or install FFmpeg automatically. Error: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# NODES
# ═══════════════════════════════════════════════════════════════════════════

class HechiceriaAPIConfig:
    DESCRIPTION = """Central configuration node for HechicerIA.
    [-] Outputs:
        [-] api_keys: A dictionary containing your authenticated credentials. Connect this to all other Hechiceria nodes.
    [-] Widgets:
        [-] hechiceria_api_key: Your HechicerIA secret key (sk_live_...).
        [-] wavespeed_api_key: Your Wavespeed secret key."""
    
    CATEGORY = CATEGORY
    FUNCTION = "configure"
    RETURN_TYPES = ("API_KEYS",)
    RETURN_NAMES = ("api_keys",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "hechiceria_api_key": ("STRING", {"default": ""}),
                "wavespeed_api_key": ("STRING", {"default": ""}),
            }
        }

    def configure(self, hechiceria_api_key, wavespeed_api_key):
        return ({"hechiceria": hechiceria_api_key.strip(), "wavespeed": wavespeed_api_key.strip()},)


class HechiceriaProjectExplorer:
    DESCRIPTION = """Fetches all available projects in your HechicerIA account.
    [-] Inputs:
        [-] api_keys: Required authentication.
    [-] Outputs:
        [-] latest_project_id: The integer ID of your most recent project.
        [-] project_list_text: A formatted string of your projects. Connect to a ShowText node to read."""
        
    CATEGORY = CATEGORY
    FUNCTION = "explore"
    RETURN_TYPES = ("INT", "STRING")
    RETURN_NAMES = ("latest_project_id", "project_list_text")
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"api_keys": ("API_KEYS",)}}

    def explore(self, api_keys):
        hk = api_keys.get("hechiceria", "")
        url = f"{HECHICERIA_BASE}/projects?page=1"
        try:
            data = _http(url, hk)
            projects = data.get("projects", {}).get("data", [])
            if not projects:
                return {"ui": {"text": ("📂 No projects found in this account.",)}, "result": (0, "No Projects")}

            text = "📁 AVAILABLE PROJECTS:\n" + "=" * 30 + "\n"
            latest_id = 0
            for i, p in enumerate(projects):
                if i == 0: latest_id = p.get("id", 0)
                text += f"ID: {p.get('id')} | Name: {p.get('name')} | Status: {p.get('status')}\n"
            return {"ui": {"text": (text,)}, "result": (latest_id, text)}
        except Exception as e:
            return {"ui": {"text": (str(e),)}, "result": (0, str(e))}


class HechiceriaVideoExplorer:
    DESCRIPTION = """Lists every video inside a given HechicerIA project.
    [-] Inputs:
        [-] api_keys: Required authentication.
    [-] Outputs:
        [-] latest_video_id: The integer ID of the most recent video.
        [-] video_list_text: Formatted string of available videos.
    [-] Widgets:
        [-] project_id: Input a project ID from the Project Explorer."""
        
    CATEGORY = CATEGORY
    FUNCTION = "explore"
    RETURN_TYPES = ("INT", "STRING")
    RETURN_NAMES = ("latest_video_id", "video_list_text")
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_keys": ("API_KEYS",),
                "project_id": ("INT", {"default": 0}),
            }
        }

    def explore(self, api_keys, project_id):
        if project_id == 0:
            txt = "⬅️ Please enter a valid Project ID in the box above."
            return {"ui": {"text": (txt,)}, "result": (0, txt)}

        hk = api_keys.get("hechiceria", "")
        url = f"{HECHICERIA_BASE}/{project_id}/videos?page=1"
        try:
            data = _http(url, hk)
            videos = data.get("videos", {}).get("data", [])
            if not videos:
                return {"ui": {"text": ("📂 Project is empty.",)}, "result": (0, "Empty")}

            text = f"🎞️ VIDEOS FOR PROJECT {project_id}:\n" + "=" * 30 + "\n"
            latest_id = 0
            for i, v in enumerate(videos):
                if i == 0: latest_id = v.get("id", 0)
                text += f"ID: {v.get('id')} | Name: {v.get('name')} | Subvideos: {v.get('subvideos_count')}\n"
            return {"ui": {"text": (text,)}, "result": (latest_id, text)}
        except Exception as e:
            return {"ui": {"text": (str(e),)}, "result": (0, str(e))}


class HechiceriaSubvideoDownloader:
    DESCRIPTION = """Downloads a specific subvideo clip from the API. Leave IDs at 0 to pause the workflow.
    [-] Inputs:
        [-] api_keys: Required authentication.
    [-] Outputs:
        [-] local_video_path: The file path to the downloaded .mp4.
        [-] duration: Length of the clip in seconds.
        [-] frame_preview: A single image frame for previewing.
        [-] info_text: Formatted metadata about the downloaded clip.
    [-] Widgets:
        [-] project_id: The target project ID.
        [-] video_id: The target video ID.
        [-] subvideo_index: The specific subvideo index to pull."""
        
    CATEGORY = CATEGORY
    FUNCTION = "download"
    RETURN_TYPES = ("STRING", "FLOAT", "IMAGE", "STRING")
    RETURN_NAMES = ("local_video_path", "duration", "frame_preview", "info_text")
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_keys": ("API_KEYS",),
                "project_id": ("INT", {"default": 0}),
                "video_id": ("INT", {"default": 0}),
                "subvideo_index": ("INT", {"default": 0, "min": 0, "max": 100}),
            }
        }

    def download(self, api_keys, project_id, video_id, subvideo_index):
        if project_id == 0 or video_id == 0:
            raise ValueError("⏸️ PAUSED: Please read the text above and select valid Project and Video IDs.")

        hk = api_keys.get("hechiceria", "")
        url = f"{HECHICERIA_BASE}/{project_id}/{video_id}/subvideos?page=1"
        data = _http(url, hk)

        subvideos = data.get("subvideos", {}).get("data", [])
        if not subvideos:
            raise ValueError("No subvideos found.")

        idx = max(0, min(subvideo_index, len(subvideos) - 1))
        sub = subvideos[idx]

        vid_url = sub.get("original_video_url")
        frame_url = sub.get("original_frame_url")
        duration = float(sub.get("duration", 0.0))
        frames = sub.get("frames", [])

        if not vid_url:
            raise ValueError("Subvideo does not contain an original_video_url.")

        filename = f"hech_sub_{sub.get('id', 'unknown')}.mp4"
        path = os.path.join(folder_paths.get_temp_directory(), filename)

        if not os.path.exists(path):
            _download_file(vid_url, path)

        if frame_url:
            req = urllib.request.Request(frame_url, headers={"User-Agent": "Mozilla/5.0"})
            try:
                with urllib.request.urlopen(req) as resp:
                    img = Image.open(BytesIO(resp.read())).convert("RGB")
                image_tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0).unsqueeze(0)
            except Exception:
                image_tensor = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
        else:
            image_tensor = torch.zeros((1, 512, 512, 3), dtype=torch.float32)

        info_text = f"🎥 SELECTED SUBVIDEO:\n========================\nRoute: {path}\nID: {sub.get('id')}\nDuration: {duration}s\nFrames: {frames}"

        return {
            "ui": {"text": (info_text,)},
            "result": (path, duration, image_tensor, info_text),
        }


class HechiceriaVideoTrimmer:
    DESCRIPTION = """Trims a local video to a specific time window using FFmpeg.
    [-] Inputs:
        [-] local_video_path: The file path of the source video.
    [-] Outputs:
        [-] trimmed_video_path: The file path of the newly cut video.
    [-] Widgets:
        [-] start_time: The second mark to start cutting from.
        [-] max_duration: Total length of the cut in seconds."""
        
    CATEGORY = CATEGORY
    FUNCTION = "trim"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("trimmed_video_path",)
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "local_video_path": ("STRING", {"forceInput": True}),
                "start_time": ("FLOAT", {"default": 0.0, "min": 0.0, "step": 0.1}),
                "max_duration": ("FLOAT", {"default": 5.0, "min": 0.1, "max": 10.0, "step": 0.1}),
            }
        }

    def trim(self, local_video_path, start_time, max_duration):
        ffmpeg_cmd = _get_ffmpeg()
        out_filename = f"trimmed_{int(start_time)}_{int(max_duration)}_{os.path.basename(local_video_path)}"
        out_path = os.path.join(folder_paths.get_temp_directory(), out_filename)

        cmd = [
            ffmpeg_cmd, "-y", "-i", local_video_path, "-ss", str(start_time),
            "-t", str(max_duration), "-c:v", "libx264", "-c:a", "aac", out_path,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return {
            "ui": {"text": (f"✂️ Trimmed Video Route:\n{out_path}",)},
            "result": (out_path,)
        }


class HechiceriaImageStylizer:
    DESCRIPTION = """Applies an AI style to an image using Wavespeed.
    [-] Inputs:
        [-] api_keys: Required authentication.
        [-] image: Source image tensor.
    [-] Outputs:
        [-] stylized_image: Generated image tensor.
        [-] image_save_path: Local file path of the saved image.
    [-] Widgets:
        [-] prompt: Text description of the desired style.
        [-] model: The AI model to use."""
        
    CATEGORY = CATEGORY
    FUNCTION = "stylize"
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("stylized_image", "image_save_path")
    OUTPUT_NODE = True 

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_keys": ("API_KEYS",),
                "image": ("IMAGE",),
                "prompt": ("STRING", {"multiline": True, "default": "Transform into high-quality modern anime illustration."}),
                "model": (["Nano Banana", "Hunyuan"],),
            }
        }

    def stylize(self, api_keys, image, prompt, model):
        import requests as req_lib

        wk = api_keys.get("wavespeed", "")
        img_b64 = _img_to_b64(image)
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {wk}"}

        if model == "Nano Banana":
            url = "https://api.wavespeed.ai/api/v3/google/nano-banana-pro/edit"
            payload = {"aspect_ratio": "16:9", "images": [img_b64], "output_format": "png", "prompt": prompt}
        else:
            url = "https://api.wavespeed.ai/api/v3/wavespeed-ai/hunyuan-image-3-instruct/edit"
            payload = {"images": [img_b64], "prompt": prompt, "seed": 42, "size": "1280*720"}

        response = req_lib.post(url, headers=headers, json=payload).json()
        if "data" not in response:
            raise RuntimeError(f"Stylization API Error: {response}")

        task_id = response["data"]["id"]
        url_check = response["data"]["urls"]["get"]

        for _ in range(60):
            res = req_lib.get(url_check, headers=headers).json()
            status = res.get("data", {}).get("status", "").lower()
            if status == "completed":
                url_final = res["data"]["outputs"][0]
                break
            elif status == "failed":
                raise RuntimeError("Stylization failed.")
            time.sleep(5)
        else:
            raise RuntimeError("Timeout waiting for stylization result.")

        resp = req_lib.get(url_final)
        img = Image.open(BytesIO(resp.content)).convert("RGB")

        output_dir = folder_paths.get_output_directory()
        img_fname = f"hech_style_{task_id}.png"
        out_path = os.path.join(output_dir, img_fname)
        with open(out_path, "wb") as f:
            f.write(resp.content)

        out_tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0).unsqueeze(0)
        info_text = f"🎨 STYLIZED IMAGE SAVED:\n========================\nRoute: {out_path}\nModel: {model}"
        
        return {
            "ui": {"text": (info_text,)},
            "result": (out_tensor, out_path)
        }


class HechiceriaVideoGenerator:
    DESCRIPTION = """Combines stylized image and video for final animation.
    [-] Inputs:
        [-] api_keys: Required authentication.
        [-] stylized_image: Reference image tensor.
        [-] local_video_path: File path of the motion video.
    [-] Outputs:
        [-] final_video_path: Path where the new video was saved.
    [-] Widgets:
        [-] prompt: Instructions for the animation.
        [-] model: AI video model to use.
        [-] output_subfolder: Folder to save final videos in."""
        
    CATEGORY = CATEGORY
    FUNCTION = "generate"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("final_video_path",)
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_keys": ("API_KEYS",),
                "stylized_image": ("IMAGE",),
                "local_video_path": ("STRING", {"forceInput": True}),
                "prompt": ("STRING", {"multiline": True, "default": "Modern cinematic anime animation..."}),
                "model": (["Kling", "LTX"],),
                "output_subfolder": ("STRING", {"default": "HechicerIA_Finals"}),
            }
        }

    def generate(self, api_keys, stylized_image, local_video_path, prompt, model, output_subfolder):
        import requests as req_lib

        wk = api_keys.get("wavespeed", "")
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {wk}"}

        img_b64 = _img_to_b64(stylized_image)
        vid_b64 = _video_to_b64(local_video_path)

        if model == "Kling":
            url = "https://api.wavespeed.ai/api/v3/kwaivgi/kling-video-o1/reference-to-video"
            payload = {"aspect_ratio": "16:9", "duration": 5, "images": [img_b64], "video": vid_b64, "prompt": prompt}
        else:
            url = "https://api.wavespeed.ai/api/v3/wavespeed-ai/ltx-2-19b/control"
            payload = {"audio_mode": "preserve", "image": img_b64, "mode": "pose", "prompt": prompt, "resolution": "1080p", "seed": 42, "video": vid_b64}

        response = req_lib.post(url, headers=headers, json=payload).json()
        if "data" not in response:
            raise RuntimeError(f"Video Gen API Error: {response}")

        task_id = response["data"]["id"]
        url_check = response["data"]["urls"]["get"]

        for _ in range(90):
            res = req_lib.get(url_check, headers=headers).json()
            status = res.get("data", {}).get("status", "").lower()
            if status == "completed":
                url_final = res["data"]["outputs"][0]
                break
            elif status == "failed":
                raise RuntimeError("Video generation failed.")
            time.sleep(10)
        else:
            raise RuntimeError("Timeout waiting for video generation.")

        clean_subfolder = output_subfolder.strip("/\\")
        output_dir = os.path.join(folder_paths.get_output_directory(), clean_subfolder)
        os.makedirs(output_dir, exist_ok=True)

        filename = f"hech_gen_{task_id}.mp4"
        out_path = os.path.join(output_dir, filename)

        with open(out_path, "wb") as f:
            f.write(req_lib.get(url_final).content)

        return {
            "ui": {"text": (f"🎬 FINAL VIDEO SAVED:\n========================\nRoute: {out_path}",)},
            "result": (out_path,),
        }

# ═══════════════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════════════

NODE_CLASS_MAPPINGS = {
    "HechiceriaAPIConfig": HechiceriaAPIConfig,
    "HechiceriaProjectExplorer": HechiceriaProjectExplorer,
    "HechiceriaVideoExplorer": HechiceriaVideoExplorer,
    "HechiceriaSubvideoDownloader": HechiceriaSubvideoDownloader,
    "HechiceriaVideoTrimmer": HechiceriaVideoTrimmer,
    "HechiceriaImageStylizer": HechiceriaImageStylizer,
    "HechiceriaVideoGenerator": HechiceriaVideoGenerator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "HechiceriaAPIConfig": "🔑 Configure API Keys",
    "HechiceriaProjectExplorer": "📁 Project Explorer",
    "HechiceriaVideoExplorer": "🎞️ Video Explorer",
    "HechiceriaSubvideoDownloader": "📥 Subvideo Downloader",
    "HechiceriaVideoTrimmer": "✂️ Video Trimmer",
    "HechiceriaImageStylizer": "🎨 Image Stylizer",
    "HechiceriaVideoGenerator": "🎬 Video Generator",
}