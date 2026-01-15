import config
from accounting_system.expense.api_app.expense_all_resource import \
    ExpensesAllResource
from accounting_system.expense.api_app.expense_individual_resource import \
    ExpensesIndividualResource
from admin.api_app.api_key_resource import APIKeyResource
from admin.api_app.force_sync import ForceSyncResource
from admin.api_app.hook_subscription_resources import (
    AllWebhooksResource, IndividualWebhooksResource, SubscribeHookResource,
    UnsubscribeHookResource)
from admin.api_app.settings_resource import (SettingsResource,
                                             SettingsResourceAll)
from admin.api_app.testing_resource import TestResource
from admin.api_app.web_api_key_resource import ThirdPartyAPIKeyResource
from core_system.client.api_app.all_clients_resource import ClientsResource
from core_system.client.api_app.all_tags_resource import AllTagsResource
from core_system.client.api_app.client_resource import ClientResource
from core_system.client.api_app.individual_tag_resource import \
    IndividualTagResource
from core_system.client.api_app.merge_clients_api import MergeClientsResource
from core_system.client.api_app.simple_client_views import (
    ClientSimpleListResource, ClientSimpleResource)
from core_system.operational_entities.api_app.client_group_api import (
    AllClientGroupResource, IndividualClientGroupResource)
from core_system.operational_entities.api_app.legacy_operational_entities_api import (
    AllClustersResource, AllShopsResource, AllVillagesResource,
    IndividualClusterResource, IndividualShopResource,
    IndividualVillageResource)
from core_system.operational_entities.api_app.merge_entities_api import \
    MergeOperationalEntitiesResource
from core_system.operational_entities.api_app.operational_entities_api import (
    AllOperationalEntitiesResource, IndividualOperationalEntityResource)
from core_system.phone_numbers.api_views.preferred_phone_number_view import \
    PhoneNumberPreferredResource
from core_system.portfolios.api_app.all_portfolios import AllPortfoliosResource
from core_system.portfolios.api_app.individual_portfolio import \
    IndividualPortfolioResource
from core_system.role.api_app.all_roles import AllRolesResource
from core_system.role.api_app.individual_role import IndividualRoleResource
from core_system.users.api_app.all_users import AllUsersResource
from core_system.users.api_app.individual_operational_permission import \
    IndividualOperationalPermissionsResource
from core_system.users.api_app.individual_user import IndividualUserResource
from core_system.users.api_app.users_operational_permissions import (
    AllOperationalPermissionsResource, CopyOperationalPermissionsResource)
from messages_system.api_views.custom_messages import (
    AllCustomMessageResource, DeleteCustomMessageResource)
from messages_system.api_views.incoming_messages_route import \
    IncomingMessageResource
from messages_system.api_views.outgoing_messages_route import \
    OutgoingMessageResource
from messages_system.api_views.web_messages_route import WebAnswerResource
from payg_loan_system.contracts.api_app.addon_bundle_resources import (
    AllAddonBundleItemResource, AllAddonBundleResource,
    IndividualAddonBundleItemResource, IndividualAddonBundleResource)
from payg_loan_system.contracts.api_app.addon_categories_resources import (
    AllAddonCategoriesResource, IndividualAddonCategoryResource)
from payg_loan_system.contracts.api_app.addon_offer_resources import (
    AllAddonOfferResource, AllAddonOfferVersionResource,
    IndividualAddonOfferResource, IndividualAddonOfferVersionResource,
    OldAllAddonOfferResource, OldIndividualAddonOfferResource)
from payg_loan_system.contracts.api_app.addons_from_bundle_resource import \
    AllAddonsFromBundleResource
from payg_loan_system.contracts.api_app.addons_resources import (
    AllAddonsResource, IndividualAddonResource)
from payg_loan_system.contracts.api_app.contract_event_resource import (
    AllContractEventResource, IndividualContractEventResource)
from payg_loan_system.contracts.api_app.contract_expected_payments import \
    ContractExpectedPaidResource
from payg_loan_system.contracts.api_app.contract_repayment_resource import (
    AllContractRepaymentResource, IndividualContractRepaymentResource)
from payg_loan_system.contracts.api_app.contract_resource import (
    ContractHistoryResource, ContractsResource, IndividualContractResource)
from payg_loan_system.devices.api_app.all_token_history_resources import \
    AllDeviceTokensResource
from payg_loan_system.devices.api_app.device_metric_resource import \
    DeviceMetricsResourceAll
from payg_loan_system.devices.api_app.device_notes import (
    DeviceNotesAllResource, DeviceNotesIndividualResource)
from payg_loan_system.devices.api_app.device_resource import (
    AllDeviceResource, IndividualDeviceResource)
from payg_loan_system.devices.api_app.device_tag_resource import \
    DeviceTagsResource
from payg_loan_system.devices.api_app.individual_device_tag_resource import \
    IndividualDeviceTagResource
from payg_loan_system.devices.api_app.new_data_hook_resource import \
    NewDataHookResource
from payg_loan_system.offers.api_app.offer_api import (AllOffersResource,
                                                       IndividualOfferResource)
from payg_loan_system.payments.api_views.all_payments_route import (
    AllPaymentsResource, PaymentsRoutingValidationResource)
from payg_loan_system.payments.api_views.get_payment_route import \
    GetPaymentResource
from payg_loan_system.payments.api_views.b2c_payment_resource import AllB2CPaymentResource, IndividualB2CPaymentResource
from payg_loan_system.payments.api_views.payment_options_route import \
    PaymentOptionsResource
from payg_loan_system.payments.api_views.reconcile_payment_route import (
    IndividualReconciledPaymentResource, ReconciledPaymentAllResource)
from payg_loan_system.reversed_payments.api_views import \
    PaymentReversalResource
from payg_loan_system.transaction_requests.api_views.assign_device_transactions import AssignDeviceTransactionResource
from payg_loan_system.transaction_requests.api_views.cancellation_transactions import \
    CancelTransactionResource
from payg_loan_system.transaction_requests.api_views.change_offer_transactions import \
    ChangeOfferTransactionResource
from payg_loan_system.transaction_requests.api_views.collect_cash_transactions import \
    CollectCashTransactionResource
from payg_loan_system.transaction_requests.api_views.pay_client_transactions import PayClientTransactionResource
from payg_loan_system.transaction_requests.api_views.default_transactions import \
    DefaultTransactionResource
from payg_loan_system.transaction_requests.api_views.deregister_transactions import \
    DeRegisterTransactionResource
from payg_loan_system.transaction_requests.api_views.expected_paid_change_transactions import \
    ExpectedPaidChangeTransactionResource
from payg_loan_system.transaction_requests.api_views.give_delay_transactions import \
    GiveDelayTransactionResource
from payg_loan_system.transaction_requests.api_views.give_discount_transactions import \
    GiveDiscountTransactionResource
from payg_loan_system.transaction_requests.api_views.pause_transactions import \
    PauseTransactionResource
from payg_loan_system.transaction_requests.api_views.registration_transactions import \
    RegistrationTransactionResource
from payg_loan_system.transaction_requests.api_views.resume_transactions import \
    ResumeTransactionResource
from payg_loan_system.transaction_requests.api_views.reverse_repayment_transactions import \
    ReverseRepaymentTransactionResource
from payg_loan_system.transaction_requests.api_views.swap_device_transactions import \
    SwapDeviceTransactionResource
from payg_loan_system.transaction_requests.api_views.sync_activation_transactions import \
    SyncActivationTransactionResource
from payg_loan_system.transaction_requests.api_views.pair_device_transactions import \
    PairDeviceTransactionResource
from payg_loan_system.transaction_requests.api_views.undo_default_transaction import \
    UndoDefaultTransactionResource
from sales_system.lead_generator.api_views.generators_api import (
    AllLeadGeneratorResource, IndividualLeadGeneratorResource,
    LeadGeneratorCommissionResource)
from sales_system.lead_generator.api_views.lead_generator_type_api import AllLeadGeneratorTypeResource, IndividualLeadGeneratorTypeResource
from sales_system.leads.api_views.all_leads import AllLeadsResource
from sales_system.leads.api_views.individual_lead import IndividualLeadResource
from shared.file_upload.api_app.upload_file_resource import (
    DownloadFileResource, FileResource, UploadFileResource)
from stock_management_system.api_views.product_sub_type_resource import (
    ProductModelAllResource, ProductModelIndividualResource)
from stock_management_system.api_views.quantity_stock_api import \
    AllQuantityStockMovementsResource, IndividualQuantityStockMovementsResource
from stock_management_system.api_views.stock_api import (
    AllStockItemsResource, AllStockMovementsResource,
    IndividualStockItemResource, IndividualStockMovementResource)
from survey_system.api_app.individual_survey_answer_resource import (
    IndividualSurveyAnswersResource, IndividualSurveyAnswersResourceOld)
from survey_system.api_app.survey_answer_resource import (
    AllSurveyAnswersResource, AllSurveyAnswersResourceOld)
from survey_system.form_editor.api import (FormAPI, FormListAPI,
                                           FormsConfiguration,
                                           QuestionListAPI)
from survey_system.api_app.form_version_resources import (FormVersionAPI, FormVersionAPIAll)
from survey_system.web_app.api import (QuestionApi, QuestionsApi,
                                       QuestionTypesApi, SurveysApi)
API_STRUCTURE = {
    TestResource: '/test_route',
    APIKeyResource: '/api_key/request',
    ThirdPartyAPIKeyResource: '/api_key/web',
    SettingsResource: '/settings/<string:name>',
    SettingsResourceAll: '/settings',
    DeleteCustomMessageResource: '/custom_messages/<int:id>',
    AllCustomMessageResource: '/custom_messages',
    AllWebhooksResource: '/webhooks',
    IndividualWebhooksResource: '/webhooks/<int:id>',
    SubscribeHookResource: '/hook_subscription/create',
    UnsubscribeHookResource: '/hook_subscription/delete',
    PhoneNumberPreferredResource: '/phone_numbers/preferred', # Not Documented, not used
    OutgoingMessageResource: '/outgoing_messages',
    IncomingMessageResource: '/messages', # Not Documented
    AllPaymentsResource: '/payments',
    PaymentsRoutingValidationResource: '/payments/validate',
    GetPaymentResource: '/payments/<string:transaction_id>',
    PaymentReversalResource: '/payment_reversals',
    PaymentOptionsResource: '/payment_options', # Not documented
    ReconciledPaymentAllResource: '/payment_reconciliations',
    IndividualReconciledPaymentResource: '/payment_reconciliations/<int:id>',
    ClientSimpleListResource: '/clients/simple_list', # Not documented
    ClientSimpleResource: '/clients/simple', # Not documented
    ClientsResource: '/clients',
    ClientResource: '/clients/<int:client_id>',
    AllTagsResource: '/tags',
    IndividualTagResource: '/tags/<int:id>',
    DeviceTagsResource: '/device_tags',
    IndividualDeviceTagResource: '/device_tags/<int:id>',
    AllClientGroupResource: '/client_groups',
    IndividualClientGroupResource: '/client_groups/<int:id>',
    MergeClientsResource: '/clients/<int:original_client_id>/merge',
    IndividualContractResource: '/contracts/<string:contract_reference>',
    AllContractRepaymentResource: '/contract_repayments',
    IndividualContractRepaymentResource: '/contract_repayments/<int:id>',
    AllContractEventResource: '/contract_events',
    IndividualContractEventResource: '/contract_events/<int:id>',
    ContractHistoryResource: '/contracts/<string:contract_reference>/history',
    ContractsResource: '/contracts',
    ContractExpectedPaidResource: '/contracts/<string:contract_reference>/expected_payments',
    IndividualAddonResource: '/addons/<string:reference>',
    AllAddonsResource: '/addons',
    AllAddonsFromBundleResource: '/addons_from_bundle',
    OldIndividualAddonOfferResource: '/addon_offers/<int:id>',
    OldAllAddonOfferResource: '/addon_offers',
    IndividualAddonOfferResource: '/add_on_offers/<int:id>',
    AllAddonOfferResource: '/add_on_offers',
    IndividualAddonOfferVersionResource: '/offer_versions/<int:id>',
    AllAddonOfferVersionResource: '/offer_versions',
    IndividualAddonCategoryResource: '/addon_categories/<int:id>',
    AllAddonCategoriesResource: '/addon_categories',
    IndividualAddonBundleResource: '/addon_bundles/<int:id>',
    AllAddonBundleResource: '/addon_bundles',
    IndividualAddonBundleItemResource: '/addon_bundles/items/<int:id>',
    AllAddonBundleItemResource: '/addon_bundles/items',
    RegistrationTransactionResource: '/transaction_requests/registration/<string:uuid>',
    DeRegisterTransactionResource: '/transaction_requests/deregister/<string:uuid>',
    CancelTransactionResource: '/transaction_requests/cancel/<string:uuid>',
    PauseTransactionResource: '/transaction_requests/pause/<string:uuid>',
    ResumeTransactionResource: '/transaction_requests/resume/<string:uuid>',
    DefaultTransactionResource: '/transaction_requests/default/<string:uuid>',
    ExpectedPaidChangeTransactionResource: '/transaction_requests/expected_paid_change/<string:uuid>',
    UndoDefaultTransactionResource: '/transaction_requests/undo_default/<string:uuid>',
    SyncActivationTransactionResource: '/transaction_requests/sync_activation/<string:uuid>',
    PairDeviceTransactionResource: '/transaction_requests/pair_device/<string:uuid>',
    GiveDiscountTransactionResource: '/transaction_requests/give_discount/<string:uuid>',
    GiveDelayTransactionResource: '/transaction_requests/give_delay/<string:uuid>',
    CollectCashTransactionResource: '/transaction_requests/collect_cash/<string:uuid>',
    PayClientTransactionResource: '/transaction_requests/pay_client/<string:uuid>',
    SwapDeviceTransactionResource: '/transaction_requests/swap_device/<string:uuid>',
    AssignDeviceTransactionResource: '/transaction_requests/assign_device/<string:uuid>',
    ReverseRepaymentTransactionResource: '/transaction_requests/reverse_repayment/<string:uuid>',
    ChangeOfferTransactionResource: '/transaction_requests/change_offer/<string:uuid>',
    FormVersionAPI: '/form_versions/<int:id>', 
    FormVersionAPIAll: '/form_versions', 
    FormListAPI: '/forms', # Not documented
    FormAPI: '/forms/<int:form_id>', # Not Documented
    FormsConfiguration: '/forms_configuration', # Not Documented
    QuestionListAPI: '/questions_formatted', # Not Documented
    WebAnswerResource: '/messages/web_answers', # Not Documented
    ExpensesAllResource: '/expenses',
    ExpensesIndividualResource: '/expenses/<int:id>',
    SurveysApi: '/surveys', # Not Documented
    QuestionsApi: '/questions', # Not Documented
    QuestionApi: '/questions/<int:question_id>', # Not Documented
    QuestionTypesApi: '/question_types', # Not Documented
    IndividualSurveyAnswersResourceOld: '/forms/answers/<survey_answer_id>', # Not Documented, Legacy
    AllSurveyAnswersResourceOld: '/forms/answers', # Not Documented, Legacy
    IndividualSurveyAnswersResource: '/custom_forms/answers/<int:id>',
    AllSurveyAnswersResource: '/custom_forms/answers',
    AllLeadsResource: '/leads',
    IndividualLeadResource: '/leads/<int:id>',
    AllLeadGeneratorResource: '/lead_generators',
    IndividualLeadGeneratorResource: '/lead_generators/<int:id>',
    LeadGeneratorCommissionResource: '/lead_generators/<int:id>/pay_commission',
    AllLeadGeneratorTypeResource: '/lead_generators/types',
    IndividualLeadGeneratorTypeResource: '/lead_generators/types/<int:id>',
    AllOffersResource: '/offers',
    IndividualOfferResource: '/offers/<int:id>',
    AllUsersResource: '/users',
    IndividualUserResource: '/users/<int:id>',
    CopyOperationalPermissionsResource: '/users/<int:origin_user_id>/copy_operational_permissions',
    AllOperationalPermissionsResource: '/operational_permissions',
    IndividualOperationalPermissionsResource: '/operational_permissions/<int:id>',
    AllOperationalEntitiesResource: '/entities',
    IndividualOperationalEntityResource: '/entities/<int:id>',
    MergeOperationalEntitiesResource: '/entities/<int:target_entity_id>/merge',
    AllVillagesResource: '/villages',
    IndividualVillageResource: '/villages/<string:id>',
    AllClustersResource: '/clusters',
    IndividualClusterResource: '/clusters/<string:id>',
    AllShopsResource: '/hubs',
    IndividualShopResource: '/hubs/<string:id>',
    AllStockItemsResource: '/stock_items',
    IndividualStockItemResource: '/stock_items/<int:id>',
    AllStockMovementsResource: '/stock_movements',
    IndividualStockMovementResource: '/stock_movements/<int:id>',
    AllQuantityStockMovementsResource: '/quantity_stock_movements',
    IndividualQuantityStockMovementsResource: '/quantity_stock_movements/<int:id>',
    FileResource: '/files',
    UploadFileResource: '/files/pictures',
    DownloadFileResource: '/files/pictures/<string:uuid>',
    ForceSyncResource: '/force_sync', # Not documented
    AllPortfoliosResource:  '/portfolios',
    IndividualPortfolioResource:  '/portfolios/<int:id>',
    IndividualRoleResource:  '/roles/<int:id>',
    AllRolesResource:  '/roles',
    AllDeviceResource: '/devices',
    IndividualDeviceResource: '/devices/<path:serial_number>',
    AllDeviceTokensResource: '/devices/<path:serial_number>/tokens',
    DeviceMetricsResourceAll: '/devices/metrics',
    NewDataHookResource: '/devices/new_usage_data/<string:uuid>', # Not documented
    DeviceNotesAllResource: '/devices/<path:device_serial_number>/notes',
    DeviceNotesIndividualResource: '/devices_notes/<int:id>',
    ProductModelAllResource: '/product_sub_types',
    ProductModelIndividualResource: '/product_sub_types/<int:id>',
    IndividualB2CPaymentResource: '/b2c_payments/<string:payment_uuid>',
    AllB2CPaymentResource: '/b2c_payments',
}

if config.ENABLE_ENTERPRISE_FEATURES:
    from enterprise_features.api_app.billing_resource import (
        AggregatedBilledItemsResource,
        BillingResource,
        NewBillingResource,
    )
    from task_system.api_app.task_category_resource import (
        AllTaskCategoryResource,
        IndividualTaskCategoryResource,
    )
    from task_system.api_app.task_resource import (
        AllTaskResource,
        IndividualTaskResource,
    )
    from after_sales_system.interaction_system.api_app.interaction_all_resource import (
        InteractionsAllResource,
    )
    from after_sales_system.interaction_system.api_app.interaction_individual_resource import (
        InteractionsIndividualResource,
    )
    from after_sales_system.interaction_system.api_app.topics_api import (
        InteractionTopicApi,
        AllInteractionTopicGroupApi,
        IndividualInteractionTopicGroupApi,
        InteractionTopicListApi,
    )
    from after_sales_system.issue_system.api_app.issue_type import (
        AllIssueTypeResource,
        IndividualIssueTypeResource,
    )
    from after_sales_system.issue_system.api_app.issues import (
        IssuesAllResource,
        IssuesIndividualResource,
    )
    from after_sales_system.notes.api_app.notes import (
        NotesAllResource,
        NotesIndividualResource,
    )
    from after_sales_system.planning_system.api_app.planning import (
        PlanningAllResource,
        PlanningIndividualResource,
    )
    from app_builder_system.user_journey_editor.api_app.individual_journey_run_resource import (
        IndividualJourneyRunResource,
    )
    from app_builder_system.user_journey_editor.api_app.user_journey_resources import (
        AllJourneyResource,
        IndividualJourneyResource,
    )
    from app_builder_system.user_journey_editor.api_app.user_journey_version_resources import (
        IndividualJourneyVersionResource,
        AllJourneyVersionResource,
    )
    from app_builder_system.automations.api_app.automation_resources import (
        AllAutomationResource,
        IndividualAutomationResource,
    )
    from enterprise_features.api_app.odyssey_payments_route import (
        OdysseyPaymentsResource,
    )

    API_STRUCTURE.update({
        BillingResource: '/billing',
        NewBillingResource: '/billing/<string:year_and_month>',
        AggregatedBilledItemsResource: '/billing/<string:year_and_month>/items',
        IndividualTaskCategoryResource: '/task_types/<int:id>',
        AllTaskCategoryResource: '/task_types',
        IndividualTaskResource: '/tasks/<int:id>',
        AllTaskResource: '/tasks',
        InteractionsAllResource: '/interactions',
        InteractionsIndividualResource: '/interactions/<int:id>',
        AllInteractionTopicGroupApi: '/interaction_topic_groups',
        IndividualInteractionTopicGroupApi: '/interaction_topic_groups/<int:id>',
        InteractionTopicListApi: '/interaction_topics',
        InteractionTopicApi: '/interaction_topics/<int:id>',
        AllIssueTypeResource: '/issue_types',
        IndividualIssueTypeResource: '/issue_types/<int:id>',
        IssuesAllResource: '/issues',
        IssuesIndividualResource: '/issues/<int:id>',
        NotesAllResource: '/issues/<int:issue_id>/notes',
        NotesIndividualResource: '/notes/<int:id>',
        PlanningAllResource: '/plans',
        PlanningIndividualResource: '/plans/<int:id>',
        IndividualJourneyResource: '/user_journeys/<string:slug>',
        IndividualJourneyVersionResource: '/user_journey_version/<int:id>',
        AllJourneyVersionResource: '/user_journey_versions',
        AllJourneyResource: '/user_journeys',
        IndividualJourneyRunResource: '/user_journeys/run/<string:uuid>',
        AllAutomationResource: '/automations',
        IndividualAutomationResource: '/automations/<string:uuid>',
        OdysseyPaymentsResource: '/payments/odyssey',
    })

API_STRUCTURE_NAMES = {r.__name__: r for r in API_STRUCTURE}
