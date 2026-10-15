from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from shared.helpers.authorizer import authorizer
from core_system.portfolios.services.portfolio_service import PortfoliosService
from core_system.portfolios.services.portfolio_getter_service import PortfolioGetterService
from shared.helpers.pagination import Pagination
from pony.orm import db_session

from . import portfolios


@portfolios.route('/portfolios', methods=['GET'])
@login_required
@authorizer('ViewPortfolios')
@db_session
def list_portfolios():
    portfolios = PortfolioGetterService.get_filtered_objects(current_user=current_user)
    pagination = Pagination.generate(request, default_sort='id:desc')
    pagination.objects = portfolios
    return render_template('list_portfolios.html', pagination=pagination)


@portfolios.route('/portfolios/<int:portfolio_id>', methods=['GET'])
@login_required
@authorizer('ViewPortfolios')
@db_session
def view_portfolio(portfolio_id):
    portfolio = PortfolioGetterService.get_from_user_and_id(current_user, portfolio_id, strict=True)
    return render_template(
        'view_portfolio.html',
        Portfolio=portfolio
    )


@portfolios.route('/portfolios/<int:portfolio_id>/edit', methods=['GET'])
@login_required
@authorizer('EditPortfolios')
@db_session
def edit_portfolio(portfolio_id):
    portfolio = PortfolioGetterService.get_from_user_and_id(current_user, portfolio_id, strict=True)
    return render_template(
        'edit_portfolio.html',
        Portfolio=portfolio
    )


@portfolios.route('/portfolios/add', methods=['GET'])
@login_required
@authorizer('CreatePortfolios')
@db_session
def add_portfolio():
    return render_template('edit_portfolio.html')
