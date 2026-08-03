from flask import render_template, flash, redirect, url_for
from flask_login import login_required
from pony.orm import db_session

from shared.helpers.authorizer import authorizer
from shared.services.celery_queue_service import CeleryQueueService

from .. import historical_data

@historical_data.route('/gogla')
@login_required
@authorizer('GoglaDashboards')
@db_session
def gogla_dashboard():
    return render_template('gogla.html')


@historical_data.route('/gogla/compute_kpis')
@login_required
@authorizer('GoglaDashboards')
@db_session
def compute_gogla_dashboard():
    CeleryQueueService.execute_task_by_name('worker_app.tasks.compute_gogla_kpis.compute_gogla_now')
    flash('The KPIs are being refreshed, try loading the page again in a few seconds to see the results. ')
    return redirect(url_for('historical_data.gogla_dashboard'))
