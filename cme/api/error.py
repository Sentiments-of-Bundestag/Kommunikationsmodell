import logging

from fastapi import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND

logger = logging.getLogger("cme.error")


def raise_401(message: str = 'No Authentication'):
    logging.info(f"Failed authentication: {message}")
    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Basic"},
    )


def raise_404(message: str = 'Not Found'):
    raise HTTPException(
        status_code=HTTP_404_NOT_FOUND,
        detail=message,
    )
