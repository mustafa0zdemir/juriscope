from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Access denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class NotFoundException(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class BadRequestException(AppException):
    def __init__(self, detail: str = "Bad request"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
