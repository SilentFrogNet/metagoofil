from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from .base_extractor import IBaseExtractor
from mercurius.core import data_parser
from mercurius.loaders.extractor_loader import extractors_foo
from mercurius.utils.file_types import FileTypes


class ImageExtractor(IBaseExtractor):
    extractor_name = "ImageExtractor"

    def __init__(self, logger=None):
        super(ImageExtractor, self).__init__(logger)

    @extractors_foo
    def parse_data(self, path, filetype, **kwargs):
        self.filename = path

        if filetype not in FileTypes.IMAGES:
            return None

        self.image = Image.open(self.filename)

        if self.metadata:
            return self

        exif_data = {}
        info = self.image._getexif()
        if info:
            for tag, value in info.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "GPSInfo":
                    gps_data = {}
                    for t in value:
                        sub_decoded = GPSTAGS.get(t, t)
                        gps_data[sub_decoded] = value[t]

                    exif_data[decoded] = gps_data
                else:
                    exif_data[decoded] = value

        self.metadata = exif_data
        self._parse_metadata()

        return self

    @staticmethod
    def _convert_to_degrees(value):
        """
            Helper function to convert the GPS coordinates stored in the EXIF to degrees in float format
        """
        d0 = value[0][0]
        d1 = value[0][1]
        d = float(d0) / float(d1)

        m0 = value[1][0]
        m1 = value[1][1]
        m = float(m0) / float(m1)

        s0 = value[2][0]
        s1 = value[2][1]
        s = float(s0) / float(s1)

        return d + (m / 60.0) + (s / 3600.0)

    def _get_lat_lng(self):
        """
            Returns the latitude and longitude, if available, from the extracted EXIF data
        """
        lat = None
        lng = None
        if "GPSInfo" in self.metadata:
            gps_info = self.metadata["GPSInfo"]
            gps_latitude = gps_info.get("GPSLatitude", None)
            gps_latitude_ref = gps_info.get('GPSLatitudeRef', None)
            gps_longitude = gps_info.get('GPSLongitude', None)
            gps_longitude_ref = gps_info.get('GPSLongitudeRef', None)
            if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
                lat = self._convert_to_degrees(gps_latitude)
                if gps_latitude_ref != "N":
                    lat = 0 - lat
                lng = self._convert_to_degrees(gps_longitude)
                if gps_longitude_ref != "E":
                    lng = 0 - lng
        return lat, lng

    def _parse_metadata(self):
        lat, lng = self._get_lat_lng()

        artist = self.metadata.get('Artist', "").replace(u'\x00', '').strip()
        if artist:
            self.users.append(artist)
            res = data_parser.DataParser(artist)
            self.emails.extend(res.emails())
        str_copy = self.metadata.get('Copyright', "").replace(u'\x00', '').strip()
        if str_copy:
            self.users.append(str_copy)
            res = data_parser.DataParser(str_copy)
            self.emails.extend(res.emails())
        self.emails = self.unique(self.emails)
        taken = self.metadata.get('DateTime', "").strip()
        if taken:
            self.misc.append({'taken': taken})
        if lat and lng:
            self.misc.append({
                'gps': {
                    'latitude': lat,
                    'longitude': lng
                }
            })
        vendor = self.metadata.get('Make', None)
        model = self.metadata.get('Model', None)
        if vendor or model:
            self.misc.append({
                'camera': {
                    'vendor': vendor,
                    'model': model
                },
            })
