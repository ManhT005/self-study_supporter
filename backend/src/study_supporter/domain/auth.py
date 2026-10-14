class AuthError(Exception):
    """Lỗi nghiệp vụ xác thực (username trùng, mật khẩu quá ngắn...) — hiển thị
    trực tiếp cho người dùng, khác với lỗi hệ thống (kết nối DB thất bại...)."""

    pass
