import base64
from io import BytesIO

import pyotp
import qrcode
from flask import current_app
from qrcode.image.svg import SvgPathImage

from app.auth.services import verify_totp
from app.extensions import db
from app.models import User


def generate_mfa_secret() -> str:
    return pyotp.random_base32()


def build_mfa_qr_data_uri(user: User, secret: str) -> str:
    provisioning_uri = pyotp.TOTP(secret).provisioning_uri(
        name=user.username,
        issuer_name=current_app.config["MFA_ISSUER_NAME"],
    )
    image = qrcode.make(provisioning_uri, image_factory=SvgPathImage)
    output = BytesIO()
    image.save(output)
    encoded_image = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded_image}"


def enable_mfa(user: User, secret: str, code: str) -> bool:
    if not verify_totp(secret, code):
        return False

    user.mfa_secret = secret
    user.mfa_enabled = True
    db.session.commit()
    return True


def disable_mfa(user: User, password: str, code: str) -> bool:
    if (
        not user.mfa_enabled
        or not user.mfa_secret
        or not user.check_password(password)
        or not verify_totp(user.mfa_secret, code)
    ):
        return False

    user.mfa_enabled = False
    user.mfa_secret = None
    db.session.commit()
    return True
