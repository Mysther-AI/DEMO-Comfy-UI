"""
ComfyUI HechicerIA API Extension
=================================
AI-powered video stylization pipeline connecting ComfyUI
to the HechicerIA and Wavespeed APIs.

https://github.com/hechiceria/comfyui-hechiceria-api
"""

from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

WEB_DIRECTORY = "./web"
