import copy
import config
from core_system.role.permissions import all_permissions

# Roles in use:
# - SuperAdmin (OK, has all permissions)
# - Admin
# - Accountant
# - SuperManager
# - Manager
# - Mentor
# - ViewOnly

admin_permissions = copy.deepcopy(all_permissions)
if not config.ENV_VAR == 'TEST':
    admin_permissions['Admin'].remove('ConfigureDeviceAPI')
    admin_permissions['Admin'].remove('EditBanner')
    admin_permissions['Admin'].remove('ConfigurePaymentRouter')
    admin_permissions['Actions'].remove('ChangeExpectedPaid')
    admin_permissions['Payments'].remove('ViewOdyssey')


accountant_permissions = {
    # Sales
    'Leads': ['View', 'ViewCreated', 'Add', 'Edit', 'EditPortfolio', 'SetCommission', 'EditPlannedDeliveryDate', 'FillCustomForms'],
    'LeadGenerators': ['View', 'Add', 'Edit', 'GiveCommissionTo'],
    # AfterSales
    'Clients': ['View', 'Edit', 'EditPortfolio', 'FillCustomForms', 'AddTags', 'CreateTags'],
    'AddOns': ['Approve'],
    'Issues': ['View', 'ViewBadge', 'AddNotes', 'DeleteOwnNotes'],
    'Interactions': ['View'],
    'Planning': ['View'],
    # Accounting
    'Payments': ['View', 'ViewOrphaned'],
    'Accounts': ['View', 'Edit', 'Manage', 'ManageAll', 'DownloadGlobal'],
    'Transfers': ['Request', 'Confirm', 'View', 'Delete'],
    'Expenses': ['View', 'Add', 'Edit', 'EditOwn', 'EditOthers', 'EditAmount'],
    # Management
    'Users': ['View', 'ViewOwn', 'Edit', 'Add'],
    'Roles': ['View', 'Assign'],
    # Logistics
    'Devices': [],
    'ViewStock': ['InStock', 'WithUsers', 'WithMe', 'WithClients', 'Orphaned'],
    'MoveStock': ['FromOrphaned', 'FromInStock', 'FromUsers', 'FromWithMe', 'FromLost',
                  'ToOrphaned', 'ToInStock', 'ToUsers', 'ToWithMe', 'ToLost'],
    # Admin
    'Admin': ['ExportData'],
    'Messages': ['AddIncoming', 'AddOutgoing', 'View'],
    'Offers': ['View'],
    'AddonOffers': ['View'],
    # General
    'Actions': ['View', 'SyncActivation', 'MakeOnStockOutsideView', 'DoChangeOffer', 'DeRegister', 'GiveDiscount',
                'Register', 'CollectCash', 'SwapDevice', 'GiveDelay', 'GiveDiscountOver2Days', 'GiveDelayOver2Days','CancelContract', 'PauseContract', 'ResumeContract'],
    'Dashboards': ['View', 'ViewGlobal'],
    'Mobile': ['SyncLeads', 'SyncAllCreatedLeads', 'SyncLeadGenerators', 'SyncOwnLeadGenerator',
                'SyncClients', 'SyncCompletedClients', 'SyncInteractions', 'SyncPlanning'],
}


super_manager_permissions = {
    # Sales
    'Leads': ['View', 'ViewCreated', 'ViewBadge', 'Add', 'Edit', 'EditPortfolio', 'SetCommission', 'EditPlannedDeliveryDate', 'FillCustomForms'],
    'LeadGenerators': ['View', 'Add', 'Merge', 'Edit', 'GiveCommissionTo'],
    # AfterSales
    'Clients': ['View', 'Edit', 'EditPortfolio', 'FillCustomForms', 'AddTags', 'CreateTags'],
    'AddOns': ['Approve', 'MarkAsDelivered', 'MarkAsUnDelivered', 'MarkAsDeliveredWithoutPlannedDate'],
    'Issues': ['View', 'Add', 'Edit', 'ViewBadge', 'AddNotes', 'DeleteNotes', 'DeleteOwnNotes'],
    'Interactions': ['View', 'Add', 'Edit', 'Delete'],
    'Planning': ['View', 'Add', 'Edit', 'Delete'],
    # Accounting
    'Payments': ['View', 'ViewOrphaned'],
    'Accounts': ['View', 'Edit', 'Manage'],
    'Transfers': ['Request', 'View'],
    'Expenses': ['View', 'Add', 'EditOwn', 'EditAmount'],
    # Management
    'Villages': ['Add', 'Edit', 'Delete'],
    'Clusters': ['Add', 'Edit'],
    'Users': ['View', 'ViewOwn'],
    # Logistics
    'Devices': [],
    'Offers': ['View'],
    'AddonOffers': ['View'],
    'ViewStock': ['InStock', 'WithUsers', 'WithMe', 'WithClients', 'Orphaned'],
    'MoveStock': ['FromOrphaned', 'FromInStock', 'FromUsers', 'FromWithMe', 'FromLost',
                  'ToOrphaned', 'ToInStock', 'ToUsers', 'ToWithMe', 'ToLost'],
    # Admin
    'Admin': ['ExportData'],
    'Messages': ['AddIncoming', 'AddOutgoing', 'ViewAll', 'View', 'ViewOrphaned'],
    # General
    'Actions': ['View', 'SyncActivation', 'MakeOnStockOutsideView', 'DoChangeOffer', 'DeRegister', 'GiveDiscount',
                'Register', 'CollectCash', 'SwapDevice', 'GiveDelay', 'GiveDiscountOver2Days',
                'GiveDelayOver2Days', 'GiveTokensOffline', 'PauseContract', 'ResumeContract', 'CancelContract'],
    'Dashboards': ['View', 'ViewGlobal'],
    'Mobile': ['SyncLeads', 'SyncAllCreatedLeads', 'SyncLeadGenerators', 'SyncOwnLeadGenerator',
                'SyncClients', 'SyncCompletedClients', 'SyncInteractions', 'SyncPlanning'],
}


manager_permissions = {
    # Sales
    'Leads': ['View', 'ViewCreated', 'Add', 'Edit', 'EditPortfolio', 'SetCommission', 'EditPlannedDeliveryDate', 'FillCustomForms'],
    'LeadGenerators': ['View', 'Add', 'Edit', 'GiveCommissionTo'],
    # AfterSales
    'Clients': ['View', 'Edit', 'EditPortfolio', 'FillCustomForms', 'AddTags', 'CreateTags'],
    'AddOns': [],
    'Issues': ['View', 'Add', 'Edit', 'ViewBadge', 'AddNotes', 'DeleteOwnNotes'],
    'Interactions': ['View', 'Add', 'Edit', 'Delete'],
    'Planning': ['View', 'Add', 'Edit', 'Delete'],
    # Accounting
    'Payments': ['View', 'ViewOrphaned'],
    'Accounts': ['View', 'Edit', 'Manage'],
    'Transfers': ['Request', 'View'],
    'Expenses': ['View', 'Add', 'EditOwn', 'EditAmount'],
    # Management
    'Villages': ['Add', 'Edit', 'Delete'],
    'Clusters': ['Add', 'Edit'],
    'Users': ['View', 'ViewOwn'],
    # Logistics
    'Offers': ['View'],
    'AddonOffers': ['View'],
    'ViewStock': ['InStock', 'WithUsers', 'WithMe', 'WithClients', 'Orphaned'],
    'MoveStock': ['FromOrphaned', 'FromInStock', 'FromUsers', 'FromWithMe', 'FromLost',
                  'ToOrphaned', 'ToInStock', 'ToUsers', 'ToWithMe', 'ToLost'],
    # Admin
    'Messages': ['AddOutgoing', 'View'],
    # General
    'Actions': ['View', 'SyncActivation', 'MakeOnStockOutsideView', 'DoChangeOffer', 'DeRegister', 'GiveDiscount',
                'Register', 'CollectCash', 'SwapDevice', 'GiveDelay', 'GiveDiscountOver2Days',
                'GiveTokensOffline'],
    'Dashboards': ['View'],
    'Mobile': ['SyncLeads', 'SyncAllCreatedLeads', 'SyncLeadGenerators', 'SyncOwnLeadGenerator',
                'SyncClients', 'SyncInteractions', 'SyncPlanning'],
    # Task System
    'Tasks': ['Add', 'Edit', 'Delete', 'View'],
}

agent_permissions = {
    # Sales
    'Leads': ['View', 'ViewCreated', 'Add', 'Edit', 'EditPortfolio', 'FillCustomForms'],
    'LeadGenerators': ['View', 'Add'],
    # AfterSales
    'Clients': ['View', 'Edit', 'EditPortfolio', 'FillCustomForms'],
    'AddOns': [],
    'Issues': ['View', 'Add', 'Edit', 'ViewBadge', 'AddNotes', 'DeleteOwnNotes'],
    'Interactions': ['View', 'Add', 'Edit', 'Delete'],
    'Planning': ['View'],
    # Accounting
    'Payments': ['View', 'ViewOrphaned'],
    'Transfers': ['Request', 'View'],
    'Expenses': ['View', 'Add', 'EditOwn'],
    # Management
    'Villages': ['Edit', 'Add'],
    'Users': ['ViewOwn'],
    'Messages': ['AddOutgoing', 'View'],
    # Logistics
    'Offers': ['View'],
    'AddonOffers': ['View'],
    'ViewStock': ['InStock', 'WithUsers', 'WithMe', 'WithClients', 'Orphaned'],
    'MoveStock': ['FromOrphaned', 'FromInStock', 'FromUsers', 'FromWithMe', 'FromLost',
                  'ToOrphaned', 'ToInStock', 'ToUsers', 'ToWithMe', 'ToLost'],
    # General
    'Actions': ['View', 'SyncActivation', 'MakeOnStockOutsideView', 'DoChangeOffer', 'DeRegister', 
                'Register', 'CollectCash', 'SwapDevice'],
    'Dashboards': ['View'],
    'Mobile': ['SyncLeads', 'SyncAllCreatedLeads', 'SyncLeadGenerators', 'SyncOwnLeadGenerator',
                'SyncClients', 'SyncCompletedClients', 'SyncInteractions', 'SyncPlanning'],
    # Task System
    'Tasks': ['ChangeStatusOfAssigned', 'ViewAssigned', 'AddAssigned', 'EditCreated',
            'DeleteCreated']
}

viewonly_permissions = {
    # Sales
    'Leads': ['View', 'ViewBadge'],
    'LeadGenerators': ['View'],
    # AfterSales
    'Clients': ['View'],
    'Issues': ['View', 'ViewBadge'],
    'Interactions': ['View'],
    'Planning': ['View'],
    # Accounting
    'Payments': ['View', 'ViewOrphaned'],
    'Accounts': ['View'],
    'Transfers': ['View', 'ViewBadge'],
    'Expenses': ['View'],
    # Management
    'Users': ['View', 'ViewOwn'],
    # Logistics
    'Devices': [],
    'Messages': ['ViewAll', 'View', 'ViewOrphaned'],
    'Offers': ['View'],
    'AddonOffers': ['View'],
    'ViewStock': ['InStock', 'WithUsers', 'WithMe', 'WithClients', 'Orphaned'],
    # General
    'Actions': ['View'],
    'Dashboards': ['View', 'ViewGlobal', 'Gogla'],
    'Mobile': ['SyncLeads', 'SyncAllCreatedLeads',
                'SyncClients', 'SyncInteractions', 'SyncPlanning']
}

billing_api_permissions = {
    'Admin': ['ViewBilling', 'EditBanner', 'ConfigureGeneralSettings'],
    'Users': ['View', 'Edit'],
    'Clients': ['View'],
    'Roles': ['View'],
    'Payments': ['View']
}
