from fastapi import FastAPI, HTTPException

from uvicorn import run

from models import Post_Ip, PatchCameraModel
from webcam import WebCam

app = FastAPI()

CAMERAS: dict[str, WebCam] = {}
LOGIN = "admin"
PASS = "admin123456"
PORT = 6688


@app.post("/cameras_ip/")
async def add_cameras(data: Post_Ip):
    CAMERAS.clear()
    ip_with_error = []
    for ip in data.ip_cameras:
        try:
            cam = WebCam(ip, PORT, LOGIN, PASS)
            serial = str(cam.DeviceInfo.SerialNumber)
            CAMERAS[serial] = cam
        except Exception as _ex:
            ip_with_error.append(ip)
    return {'status': 'success', 'message': 'Cameras have been added successfully', 'ip_with_error': ip_with_error}


@app.get("/cameras/")
async def get_cameras():
    info_cams = []
    for serial in CAMERAS.keys():
        cam = CAMERAS[serial]
        info_cams.append(cam.createInfoPackage(0))

    return {'status': 'success', 'message': 'Cameras Data', 'data': info_cams}


@app.patch("/cameras/{serial_id}")
async def set_camera(serial_id: str, data: PatchCameraModel):
    cam = CAMERAS.get(serial_id)
    if cam is None:
        raise HTTPException(status_code=400, detail="invalid serial")
    prof = cam.profiles[0].VideoEncoderConfiguration
    try:
        cam.setVideoConf(data, prof)
    except Exception as _ex:
        raise HTTPException(status_code=500, detail="problem")
    return {'status': 'success', 'message': 'The changes were saved successfully'}


@app.get("/cameras_params/{serial_id}")
async def get_param_options(serial_id: str):
    cam = CAMERAS.get(serial_id)
    if cam is None:
        raise HTTPException(status_code=400, detail="invalid serial")
    info = cam.getParamOptions(0)
    return {'status': 'success', 'message': 'Cameras Data', 'data': info}

#if __name__ == "__main__":
 #   run(app, port=8000)