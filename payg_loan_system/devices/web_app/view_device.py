import config
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from flask_login import login_required, current_user
from flask import flash, redirect, url_for, render_template, jsonify
from pony.orm import db_session, desc, select, max
from shared.helpers.pagination import Pagination
from shared.helpers.pagination import ResultSet
from payg_loan_system.devices.model.token import Token
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from shared.logger.loggers import Error
from stock_management_system.services.product_sub_type_service import ProductSubTypeService
from stock_management_system.stock_status import StockStatus
from payg_loan_system.devices.services.offline_token_config_service import OfflineTokenConfigService
from payg_loan_system.devices.services.device_metrics_service import DeviceMetricsService
from . import device_views
from datetime import datetime, timedelta
from flask import request, abort
from pony.orm import db_session
from shared.helpers.authorizer import authorizer
from shared.helpers.date_helper import from_str_to_date
from payg_loan_system.devices.model.device import Device
from payg_loan_system.devices.services.device_metrics_chart_service import DeviceLineChartService
from payg_loan_system.devices.services.device_tag_getter import DeviceTagService

if config.ENABLE_ENTERPRISE_FEATURES:
    from after_sales_system.issue_system.services.issue_service import IssueService
    from after_sales_system.issue_system.model.issue_model import Issue
else:
    IssueService = None
    Issue = None


@device_views.route('/<int:device_id>', methods=['GET'])
@login_required
@authorizer(['InStockViewStock', 'WithUsersViewStock', 'WithMeViewStock', 'WithClientsViewStock', 'OrphanedViewStock'])
@db_session
def view_device(device_id):
    device = DeviceGetterService.get_from_user_and_id(current_user, device_id)
    if not device:
        flash("Device does not exists. ")
        return redirect(url_for('stock.stock_list'))
    else:
        device_number_of_issues = 0
        if config.ENABLE_ENTERPRISE_FEATURES and IssueService:
            device_number_of_issues = IssueService.get_list(current_user, device=device).count()
        tokens = Token.select(lambda t: t.device == device).order_by(desc(Token.time))
        offline_token_configs = OfflineTokenConfigService.get_config_for_device_type(device.type)
        offline_tokens = device.offline_tokens.filter(lambda d: not d.deleted).order_by(lambda d: desc(d.generation_time))
        
        end_date = datetime.today()
        start_date = end_date - timedelta(weeks=1)

        more_tokens = False
        MAX_TOKENS = 50
        if tokens.count() > MAX_TOKENS:
            more_tokens = True
            tokens = tokens.limit(MAX_TOKENS)
        return render_template(
            'view_device.html',
            Device=device,
            requires_code=DeviceAPIService.device_requires_request_code(device),
            device_number_of_issues=device_number_of_issues,
            tokens=tokens,
            stock_statuses=StockStatus,
            offline_token_configs=offline_token_configs,
            BeginDate=start_date,
            EndDate=end_date,
            offline_tokens=offline_tokens,
            tags=[(t.name) for t in device.tags],
            more_tokens=more_tokens,
            product_sub_types=[(p.id, p.name) for p in ProductSubTypeService.get_list(current_user, device_type=device.type)]
        )


@device_views.route('/serial/<path:composed_serial>', methods=['GET'])
@login_required
@authorizer(['InStockViewStock', 'WithUsersViewStock', 'WithMeViewStock', 'WithClientsViewStock', 'OrphanedViewStock'])
@db_session
def view_device_from_composed_serial(composed_serial):
    this_device = DeviceGetterService.get_from_user_and_properties(current_user, composed_serial=composed_serial)
    if not this_device:
        flash('Device does not exists')
        return redirect(url_for('stock.stock_list'))
    return redirect(url_for('.view_device', device_id=this_device.id))


@device_views.route('/<int:device_id>/sync', methods=['GET'])
@login_required
@authorizer(['InStockViewStock', 'WithUsersViewStock', 'WithMeViewStock', 'WithClientsViewStock', 'OrphanedViewStock'])
@db_session
def sync_device(device_id):
    SelectedDevice = DeviceGetterService.get_from_user_and_id(current_user, device_id)
    if not SelectedDevice:
        flash("Device does not exists. ")
        return redirect(url_for('stock.stock_list'))
    else:
        try:
            DeviceAPIService.get_usage_metric_types_for_device(SelectedDevice)
            SelectedDevice.supports_monitoring_data = True  # Only set if the above succeeds
            DeviceAPIService.subscribe_or_unsubscribe_to_new_data_hook(SelectedDevice)
        except Exception as e:
            pass
        DeviceMetricsService.update_device_metrics(SelectedDevice, force_sync=True)
        flash('Synced! ')
        return redirect(url_for('.view_device', device_id=device_id))


@device_views.route('/chart/usage_metrics/<int:device_id>', methods=['GET'])
@login_required
@authorizer(['InStockViewStock', 'WithUsersViewStock', 'WithMeViewStock', 'WithClientsViewStock', 'OrphanedViewStock'])
@db_session
def view_device_metrics_chart(device_id):
    device = DeviceGetterService.get_from_user_and_id(current_user, device_id, strict=True, main_resource=True)
    chart = DeviceLineChartService(device)
    format = request.values.get('format', '%Y-%m-%d')
    metric = request.values.get('metric')
    if not metric: raise Error('Invalid metric')
    start_date = from_str_to_date(request.values.get('start_date'), format=format)
    end_date = from_str_to_date(request.values.get('end_date'), format=format)+timedelta(days=1)
    return chart.usage_metric_info(start_date,
                                   end_date,
                                   metric)