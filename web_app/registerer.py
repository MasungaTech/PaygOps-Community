import config
from accounting_system.account import account
from accounting_system.expense import expense

from core_system.client.web_app import client
from core_system.users.web_app import user
from core_system.phone_numbers.web_app import phone_numbers
from core_system.role.web_app import permission_system
from core_system.portfolios.web_app import portfolios
from data_system.csv_exports.web_app import file_exporter

from messages_system.web_app import message

from payg_loan_system.payments.web_app import payment
from payg_loan_system.devices.web_app import device_views
from payg_loan_system.reversed_payments.web_app import reversed_payment
from payg_loan_system.requests.web_app import mentor_request
from payg_loan_system.transaction_requests.web_app import transaction_request
from payg_loan_system.gogla_stats import historical_data
from payg_loan_system.offers.web_app import offer_system

from sales_system.leads.web_app import leads
from sales_system.lead_generator.web_app import lead_generator
from sales_system.sales_dashboard import sales_dashboard

if config.ENABLE_ENTERPRISE_FEATURES:
    from after_sales_system.interaction_system.web_app import interaction_report
    from after_sales_system.issue_system.web_app import issue
    from app_builder_system.user_journey_editor.web_app import user_journey_editor
    from app_builder_system.automations.web_app import automations
else:
    interaction_report = issue = None
    user_journey_editor = automations = None



class BlueprintRegisterer:
    @staticmethod
    def register(app):

        app.register_blueprint(file_exporter, url_prefix='/file')

        from admin.web_app import administration, two_factor
        app.register_blueprint(administration, url_prefix='/admin')
        app.register_blueprint(two_factor, url_prefix='/two_factor')

        from admin.passwords import auth
        app.register_blueprint(auth, url_prefix='/login')

        app.register_blueprint(sales_dashboard, url_prefix='/sales_dashboard')

        app.register_blueprint(expense, url_prefix='/accounting/expenses')
        app.register_blueprint(account, url_prefix='/accounting/accounts')
        app.register_blueprint(payment, url_prefix='/payments')
        app.register_blueprint(reversed_payment, url_prefix='/reversed_payments')
        app.register_blueprint(client, url_prefix='/clients')
        app.register_blueprint(leads, url_prefix='/leads')
        app.register_blueprint(lead_generator, url_prefix='/lead_generators')
        app.register_blueprint(user, url_prefix='/users')
        from core_system.operational_entities.web_app import operational_entities
        app.register_blueprint(operational_entities, url_prefix='/entities')
        app.register_blueprint(device_views, url_prefix='/devices')

        from stock_management_system.web_app import stock_management
        app.register_blueprint(stock_management, url_prefix='/stock')

        from data_system.web_app import overview
        app.register_blueprint(overview, url_prefix='/overview')

        app.register_blueprint(mentor_request, url_prefix='/requests')
        app.register_blueprint(transaction_request, url_prefix='/transaction_requests')
        app.register_blueprint(message, url_prefix='/messages')
        app.register_blueprint(phone_numbers, url_prefix='/phone_numbers')

        from survey_system.web_app import survey, custom_forms
        app.register_blueprint(survey, url_prefix='/surveys')
        app.register_blueprint(custom_forms, url_prefix='/custom_forms')

        if config.ENABLE_ENTERPRISE_FEATURES:
            app.register_blueprint(user_journey_editor, url_prefix='/user_journey_editor')
            app.register_blueprint(interaction_report, url_prefix='/interactions')
            app.register_blueprint(issue, url_prefix='/issues')
        app.register_blueprint(permission_system, url_prefix='/permissions')
        app.register_blueprint(historical_data, url_prefix='/historical_data')

        from admin.api_keys import api_system
        app.register_blueprint(api_system, url_prefix='/api_system_admin')

        app.register_blueprint(portfolios, url_prefix='/')

        app.register_blueprint(offer_system, url_prefix='/offers')

        from survey_system.form_editor.blueprint import forms_blueprint
        app.register_blueprint(forms_blueprint, url_prefix='/forms')

        from shared.file_upload.web_app import file_upload
        app.register_blueprint(file_upload, url_prefix='/files/')

        from payg_loan_system.contracts.web_app import contract
        app.register_blueprint(contract, url_prefix='/contracts')

        if config.ENABLE_ENTERPRISE_FEATURES:
            from task_system.web_app import task_category, task_manager
            app.register_blueprint(task_category, url_prefix='/task_type')
            app.register_blueprint(task_manager, url_prefix='/tasks')
            app.register_blueprint(automations, url_prefix='/automations')

        return app
