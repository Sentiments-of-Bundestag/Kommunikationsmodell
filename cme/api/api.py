#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Analytics Service AS API

import time
import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST

from cme import database
from cme.api import api_data

BASE_PREFIX = "cme"

#config = common.get_config()
db = database.get_db()
app = FastAPI()

app.include_router(api_data.router, prefix=f"/{BASE_PREFIX}/data")


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(exc.errors(), status_code=HTTP_400_BAD_REQUEST)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9001, log_level="debug", reload=True)
