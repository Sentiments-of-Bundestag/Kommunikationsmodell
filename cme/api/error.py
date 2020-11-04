from fastapi import HTTPException
from starlette.status import HTTP_404_NOT_FOUND


def raise_404(message: str = 'Not Found'):
    raise HTTPException(
        status_code=HTTP_404_NOT_FOUND,
        detail=message,
    )