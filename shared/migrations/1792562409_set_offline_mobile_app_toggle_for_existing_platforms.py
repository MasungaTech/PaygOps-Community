import json

from pony.orm import db_session


@db_session
def up(db):
    platform_type = db.Settings.get(key="PlatformType")
    feature_toggles = db.Settings.get(key="FeatureToggles")
    if not platform_type or not feature_toggles:
        return

    toggles = json.loads(feature_toggles.value)
    if "OfflineMobileApp" not in toggles:
        toggles["OfflineMobileApp"] = platform_type.value != "features-package"
        feature_toggles.value = json.dumps(toggles)


@db_session
def down(db):
    pass
