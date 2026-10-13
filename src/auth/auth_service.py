import bcrypt
from sqlalchemy.exc import IntegrityError

from src.db.database import SessionLocal
from src.db.models import User


class AuthError(Exception):
    """Lỗi nghiệp vụ xác thực (username trùng, mật khẩu quá ngắn...) — hiển thị
    trực tiếp cho người dùng, khác với lỗi hệ thống (kết nối DB thất bại...)."""

    pass


def register_user(username: str, password: str) -> int:
    username = username.strip()
    if len(username) < 3:
        raise AuthError("Tên đăng nhập cần ít nhất 3 ký tự.")
    if len(password) < 6:
        raise AuthError("Mật khẩu cần ít nhất 6 ký tự.")

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    session = SessionLocal()
    try:
        user = User(username=username, password_hash=password_hash)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id
    except IntegrityError:
        session.rollback()
        raise AuthError("Tên đăng nhập đã tồn tại, hãy chọn tên khác.")
    finally:
        session.close()


def authenticate_user(username: str, password: str) -> int | None:
    """Trả về user.id nếu đúng, None nếu sai username/password."""
    session = SessionLocal()
    try:
        user = session.query(User).filter_by(username=username.strip()).first()
        if user is None:
            return None
        if bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            return user.id
        return None
    finally:
        session.close()
