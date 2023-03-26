from storages.backends.gcloud import GoogleCloudStorage


class StaticRootGoogleCloudStorage(GoogleCloudStorage):
    default_acl = "publicRead"
    file_overwrite = True
    location = "static"


class MediaRootGoogleCloudStorage(GoogleCloudStorage):
    default_acl = "projectPrivate"
    file_overwrite = False
    location = "media"
