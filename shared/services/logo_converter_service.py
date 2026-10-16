import config
import PIL


class LogoConverterService:
    LOGO_SIZE = (512*6, 512)  # Maximum 512 height with 1:6 ratio

    @classmethod
    def convert_logo_from_platform_settings(cls):
        # Needs to be imported here to avoid a circular import
        from shared.file_upload.services.stored_file_service import StoredFileService
        from shared.services.settings_service import SettingsService

        picture_uuid = SettingsService.get_setting('PlatformLogoPictureID')
        if picture_uuid:
            picture = StoredFileService.get_from_uuid(picture_uuid)
            if picture:
                picture_path = picture.get_file_path()
                cls.convert_logo_from_picture_path(picture_path)

    @classmethod
    def convert_logo_from_picture_path(cls, picture_path):
        cls.generate_positive_image(picture_path)
        cls.generate_inverted_image(picture_path)

    @classmethod
    def generate_positive_image(cls, picture_path):
        image = PIL.Image.open(picture_path)
        inverted_image = PIL.ImageOps.colorize(image.convert('L'), (255, 255, 255), (0, 62, 81))
        inverted_image.thumbnail(cls.LOGO_SIZE, PIL.Image.LANCZOS)
        inverted_image.save(config.LOGO_PATH)

    @classmethod
    def generate_inverted_image(cls, picture_path):
        image = PIL.Image.open(picture_path)
        positive_image = PIL.ImageOps.colorize(image.convert('L'), (0, 62, 81), (255, 255, 255))
        positive_image.thumbnail(cls.LOGO_SIZE, PIL.Image.LANCZOS)
        positive_image.save(config.LOGO_INVERTED_PATH)
