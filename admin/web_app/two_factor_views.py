from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from flask_login import login_required, current_user
from pony.orm import db_session
from shared.services.two_factor_service import TwoFactorService
from . import two_factor

@two_factor.route('/setup', methods=['GET', 'POST'])
@login_required
@db_session
def setup_2fa():
    """Setup two-factor authentication for the current user"""
    user = current_user.reload()
    qr_code = None
    
    if request.method == 'POST':
        action = request.form.get('action')
    else:
        action = request.args.get('action')

    if not user.two_factor_secret:
        action = 'generate_secret'
        
    if action == 'generate_secret':
        # Generate new secret and QR code
        secret = TwoFactorService.setup_2fa_for_user(user)
        qr_code = TwoFactorService.generate_qr_code(secret, user.username)
    
    elif action == 'verify_and_enable':
        # Verify the code and enable 2FA
        code = request.form.get('verification_code', '').strip()
        if not code:
            flash('Please enter the verification code from your authenticator app.', 'error')
            return redirect(url_for('two_factor.setup_2fa'))
        
        success, message = TwoFactorService.verify_and_enable_2fa(user, code)
        if success:
            flash(message, 'success')
            return redirect(url_for('two_factor.get_backup_codes', action='complete_2fa_setup'))
        else:
            flash(message, 'error')
            return redirect(url_for('two_factor.setup_2fa'))
    
    elif action == 'disable':
        # Disable 2FA
        TwoFactorService.disable_2fa_for_user(user)
        flash('Two-factor authentication has been disabled.', 'info')
        return redirect(url_for('admin.user_settings'))
    
    # Get current 2FA status
    secret = user.two_factor_secret
    if not qr_code and secret:
        qr_code = TwoFactorService.generate_qr_code(secret, user.username)
    
    return render_template('two_factor/setup.html', 
                         user=user, 
                         secret=secret, 
                         qr_code=qr_code,
                         is_setup_mode=bool(session.get('temp_2fa_secret')))


@two_factor.route('/backup_codes', methods=['GET', 'POST'])
@login_required
@db_session
def get_backup_codes():
    user = current_user.reload()
    action = request.args.get('action')
    
    if action == 'complete_2fa_setup' or action == 'regenerate_backup_codes':
        first_setup = action == 'complete_2fa_setup'
        if user.two_factor_enabled:
            backup_codes = TwoFactorService.get_backup_codes(user)
            return render_template('two_factor/backup_codes.html', 
                                 user=user, 
                                 backup_codes=backup_codes,
                                 show_codes=True,
                                 first_setup=first_setup)
        else:
            flash('2FA must be enabled to generate backup codes.', 'error')
            return redirect(url_for('two_factor.setup_2fa'))
    
    return render_template('two_factor/backup_codes.html', 
                         user=user, 
                         backup_codes=[],
                         show_codes=False)
