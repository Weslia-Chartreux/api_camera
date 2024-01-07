from pydantic import BaseModel


class Post_Ip(BaseModel):
    ip_cameras: list


class PatchCameraModel(BaseModel):
    Resolution: dict[str, int] = {
        "Width": None,
        "Height": None
    }
    Quality: float = None
    FrameRateLimit: int = None
    BitrateLimit: int = None
