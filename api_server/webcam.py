from onvif import ONVIFCamera
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup as bs
import lxml.etree as et

from models import PatchCameraModel


class WebCam:
    def __init__(self, ip, port, login, password):
        self.profiles = None
        self.DeviceInfo = None
        self.Hostname = None
        self._onvif_camera = ONVIFCamera(ip, port, login, password, "../wsdl")

        self._login = login
        self._password = password
        self._ip = ip
        self._port = port

        self.OSDConfig = None

        self.loadModules()

        self.getHostname()
        self.getDeviceInfo()
        self.getProfiles()
        self.getMediaServiceCapabilities()
        self.getOSDs()

    def loadModules(self):
        self._onvif_camera.create_media_service()

    def getDeviceInfo(self):
        self.DeviceInfo = self._onvif_camera.devicemgmt.GetDeviceInformation()

    def getHostname(self):
        self.Hostname = self._onvif_camera.devicemgmt.GetHostname().Name

    def setHostname(self, name):
        params = self._onvif_camera.devicemgmt.create_type("SetHostname")
        params.Name = name
        self._onvif_camera.devicemgmt.SetHostname(params)

        self.getHostname()

    def getProfiles(self):
        prof = self._onvif_camera.media.GetProfiles()

        self.profiles = prof

        for i in prof:
            f = open(f"./profiles/{i.Name}.txt", "w")
            print(i, file=f)
            f.close()

    def getMediaServiceCapabilities(self):
        self.mediaServiceCapabilities = (
            self._onvif_camera.media.GetServiceCapabilities()
        )

    def getOSDs(self):
        res = self._onvif_camera.media.GetOSDs()
        for i in res:
            f = open(f"./osd/{i.token}.txt", "w")
            print(i, file=f)
            f.close()

    def createTextOSD(self, token, videoSource, position, text):
        params = self._onvif_camera.media.create_type("CreateOSD")
        params.token = token
        params.VideoSourceConfigurationToken = videoSource
        params.Type = "Text"
        params.Position = {"Type": position}
        params.TextString = {
            "Type": "Plain",
            "PlainText": text,
        }
        self._onvif_camera.media.CreateOSD(params)

    def getVideoURL(self, profileToken):
        params = self._onvif_camera.media.create_type("GetStreamUri")

        params.StreamSetup = {
            "Stream": "RTP-Unicast",
            "Transport": {"Protocol": "HTTP"},
        }
        params.ProfileToken = profileToken

        res = self._onvif_camera.media.GetStreamUri(params)
        uri = res.Uri.replace("//", f"//{self._login}:{self._password}@")

        return uri

    def setTime(self):
        params = self._onvif_camera.devicemgmt.create_type("SetSystemDateAndTime")
        params.DateTimeType = "Manual"
        params.DaylightSavings = True
        now = datetime.now()
        params.UTCDateTime = {
            "Time": {"Hour": now.hour, "Minute": now.minute, "Second": now.second},
            "Date": {"Year": now.year, "Month": now.month, "Day": now.day},
        }
        self._onvif_camera.devicemgmt.SetSystemDateAndTime(params)

    def getOSDConfig(self):
        url = f"http://{self._ip}/PSIA/YG/OSD/OSDConfig/0"
        req = requests.get(url)
        data = str(req.content).split("?>")[1]
        self.OSDConfig = bs(data, "xml")

    def setOSDConfig(self):
        str_xsl = """
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output indent="yes"/>
    <xsl:strip-space elements="*"/>

    <!-- IDENTITY TRANSFORM -->
    <xsl:template match="@*|node()">
      <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
      </xsl:copy>
    </xsl:template>

    <!-- RUN normalize-space() ON ALL TEXT NODES -->
    <xsl:template match="text()">
        <xsl:copy-of select="normalize-space()"/>
    </xsl:template>
</xsl:stylesheet>
        """

        if self.OSDConfig == None:
            return
        str_xml = str(self.OSDConfig.prettify()).encode()

        doc = et.fromstring(str_xml)
        style = et.fromstring(str_xsl)

        transformer = et.XSLT(style)
        result = str(transformer(doc))

        requests.put(f"http://{self._ip}/PSIA/YG/OSD/OSDConfig/0", data=result)

    def setDisplayName(self, flag: bool, text: str):
        if self.OSDConfig == None:
            return

        for tag in self.OSDConfig.find_all("OSDDispName"):
            tag.string = flag

        for tag in self.OSDConfig.find_all("OSDChannelName"):
            tag.string = text

    def setDisplayBitrate(self, flag: bool):
        if self.OSDConfig == None:
            return

        for tag in self.OSDConfig.find_all("OSDDispBitrate"):
            tag.string = flag

    def setDisplayDateAndTime(
            self, flag: bool, timeForm: str = "HH:mm:ss", dateForm: str = "yyyy/MM/api_server WWW"
    ):
        if self.OSDConfig == None:
            return

        for tag in self.OSDConfig.find_all("OSDDispDate"):
            tag.string = flag

        for tag in self.OSDConfig.find_all("OSDTimeForm"):
            tag.string = timeForm

        for tag in self.OSDConfig.find_all("OSDDateForm"):
            tag.string = dateForm

    def createInfoPackage(self, streamType: int):
        info = {
            "SerialNumber": self.DeviceInfo.SerialNumber,
            "Resolution": {
                "Width": self.profiles[streamType].VideoEncoderConfiguration.Resolution.Width,
                "Height": self.profiles[streamType].VideoEncoderConfiguration.Resolution.Height
            },
            "Quality": self.profiles[streamType].VideoEncoderConfiguration.Quality,
            "FrameRateLimit": self.profiles[streamType].VideoEncoderConfiguration.RateControl.FrameRateLimit,
            "BitrateLimit": self.profiles[streamType].VideoEncoderConfiguration.RateControl.BitrateLimit,
        }
        return info

    def setVideoConf(self, data: PatchCameraModel, prof):
        params = self._onvif_camera.media.create_type("SetVideoEncoderConfiguration")
        params.Configuration = prof
        if data.Quality is not None:
            params.Configuration.Quality = data.Quality
        if data.FrameRateLimit is not None:
            params.Configuration.RateControl.FrameRateLimit = data.FrameRateLimit
        if data.BitrateLimit is not None:
            params.Configuration.RateControl.BitrateLimit = data.BitrateLimit
        if data.Resolution.get("Width") is not None and data.Resolution.get("Height") is not None:
            params.Configuration.Resolution.Width = data.Resolution.get("Width")
            params.Configuration.Resolution.Height = data.Resolution.get("Height")
        params.ForcePersistence = True
        self._onvif_camera.media.SetVideoEncoderConfiguration(params)
        self.getHostname()
        self.getDeviceInfo()
        self.getProfiles()
        self.getMediaServiceCapabilities()
        self.getOSDs()

    def getParamOptions(self, streamType):
        token = self.profiles[streamType].token
        params = self._onvif_camera.media.create_type("GetVideoEncoderConfigurationOptions")
        params.ProfileToken = token
        config = self._onvif_camera.media.GetVideoEncoderConfigurationOptions(params)
        info = {
            "SerialNumber": self.DeviceInfo.SerialNumber,
            "ResolutionOptions": config.H264.ResolutionsAvailable,
            "QualityOptions": config.QualityRange,
            "FrameRateLimitOptions": config.H264.FrameRateRange,
        }
        return info
