import pyotp
import qrcode
import base64
import io
import secrets
from datetime import datetime, timedelta

import jwt
import config
from shared.api_helpers.server_helpers.jwt_generation import decode_jwt

TWO_FA_PENDING_LOGIN_PURPOSE = '2fa_pending_login'
TWO_FA_PENDING_LOGIN_EXPIRY_SECONDS = 600


class TwoFactorService:
    
    @staticmethod
    def create_pending_login_token(user_id):
        expiration = datetime.now() + timedelta(seconds=TWO_FA_PENDING_LOGIN_EXPIRY_SECONDS)
        payload = {
            'sub': str(user_id),
            'purpose': TWO_FA_PENDING_LOGIN_PURPOSE,
            'iat': datetime.now(),
            'exp': expiration,
        }
        return jwt.encode(payload, config.secret_key, algorithm='HS256')

    @staticmethod
    def resolve_pending_login_token(token):
        if not token:
            return None
        try:
            payload = decode_jwt(token, config.secret_key)
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        if payload.get('purpose') != TWO_FA_PENDING_LOGIN_PURPOSE:
            return None
        return payload.get('sub')

    @staticmethod
    def generate_secret():
        return pyotp.random_base32()
    
    @staticmethod
    def generate_totp(secret):
        totp = pyotp.TOTP(secret)
        return totp.now()
    
    @staticmethod
    def verify_totp(secret, code, window=1):
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)
    
    @staticmethod
    def generate_qr_code(secret, username, issuer=f"PaygOps - {config.INSTANCE_NAME}"):
        # Create the TOTP URI
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=username,
            issuer_name=issuer
        )
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for embedding in HTML
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    @staticmethod
    def setup_2fa_for_user(user):
        user.two_factor_secret = TwoFactorService.generate_secret()
        user.two_factor_enabled = False  # Will be enabled after verification
        user.two_factor_setup_time = datetime.now()
        return user.two_factor_secret
        return user.two_factor_secret
    
    @staticmethod
    def enable_2fa_for_user(user):
        """Enable 2FA for a user after successful verification"""
        user.two_factor_enabled = True
        user.two_factor_setup_time = datetime.now()
    
    @staticmethod
    def disable_2fa_for_user(user):
        """Disable 2FA for a user"""
        user.two_factor_enabled = False
        user.two_factor_secret = ''
        user.two_factor_setup_time = None
    
    @staticmethod
    def verify_and_enable_2fa(user, code):
        """Verify the setup code and enable 2FA if correct"""
        if not user.two_factor_secret:
            return False, "No 2FA secret found. Please setup 2FA first."
        
        if TwoFactorService.verify_totp(user.two_factor_secret, code):
            TwoFactorService.enable_2fa_for_user(user)
            return True, "2FA enabled successfully!"
        else:
            return False, "Invalid verification code. Please try again."
    
    @staticmethod
    def verify_login_code(user, code):
        """Verify 2FA code during login"""
        if not user.two_factor_enabled or not user.two_factor_secret:
            return False, "2FA is not enabled for this account."
        
        if TwoFactorService.verify_totp(user.two_factor_secret, code):
            return True, "2FA verification successful!"
        else:
            return False, "Invalid 2FA code. Please try again."
    
    @staticmethod
    def get_backup_codes(user):
        """Generate backup codes for emergency access"""
        if not user.two_factor_enabled:
            return []
        
        # Generate 8-digit backup codes
        backup_codes = []
        for _ in range(5):
            code = secrets.token_hex(4).upper()[:8]
            backup_codes.append(code)
        
        # Store hashed backup codes
        user.backup_codes = [TwoFactorService._hash_backup_code(code) for code in backup_codes]
        return backup_codes
    
    @staticmethod
    def verify_backup_code(user, code):
        """Verify a backup code"""
        if not user.backup_codes:
            return False
        
        hashed_code = TwoFactorService._hash_backup_code(code)
        if hashed_code in user.backup_codes:
            # Remove used backup code
            user.backup_codes.remove(hashed_code)
            return True
        return False
    
    @staticmethod
    def _hash_backup_code(code):
        """Hash a backup code for storage"""
        import hashlib
        return hashlib.sha256(code.encode('utf-8')).hexdigest()
