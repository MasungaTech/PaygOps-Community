from pony.orm import db_session
import json

PREMIUM_DEMO_FEATURE_DATA = {
    "FeatureToggles": {
        "paquita": True,
        "SalesFeatures": True,
        "LumpSumContracts": True,
        "LoanAndSubscriptionContracts": True,
        "AfterSales": True,
        "Inventory": True,
        "ClientGroup": True,
        "SSO": True,
        "AddOnsConfiguration": True,
        "AuditLogs": True,
        "PaymentManagement": True,
        "AutomatedMessagesSMS": True,
        "OffTaking": False,
        "EnableUserGuiding": True,
        "ClientGroups": True,
        "MobileSSO": True,
        "OfflineMobileApp": True,
        "ApiAccess": True,
        "BulkActions": True,
        "PaygoDevices": True,
        "user_journey_editor": False,
        "offtaking": True,
        "task_system": True,
        "automations": False,
        "TaskSystem": True,
        "UserJourneyEditor": True,
        "CustomAppDesigner": False,
        "Automations": True,
        "PackageInstaller": False,
        "NoValueLoanContracts": False,
        "Paquita": False,
        "BillingAnalytics": True,
        "BillingPaygOpsSMS": True,
    },
}

PREMIUM_PLATFORM_TYPES = ["premium", "new-premium", "freemium-demo"]

@db_session
def up(db):
    platform_type = db.Settings.get(key="PlatformType")
    print(platform_type.value)
    print(platform_type.value in PREMIUM_PLATFORM_TYPES)
    if platform_type.value in PREMIUM_PLATFORM_TYPES:
        feature_toggles = db.Settings.get(key="FeatureToggles")
        feature_toggles.value = json.dumps(PREMIUM_DEMO_FEATURE_DATA["FeatureToggles"])

@db_session
def down(db):
    pass
