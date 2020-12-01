#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Documentation API for Communication Model Extractor


from fastapi import APIRouter
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from starlette.responses import JSONResponse
from starlette.status import HTTP_200_OK

from cme.api import api

router = APIRouter()


def as_open_api():
    if api.app.openapi_schema:
        return api.app.openapi_schema

    open_api_schema = get_openapi(
        title="Communication Model Extractor",
        version="1.0.0",
        description="This is the API Documentation for the Communication Model Extractor. You can also check the README in the Repository for documentation about setup etc.",
        routes=api.app.routes,

    )
    open_api_schema["info"]["x-logo"] = {
        "url": "logo.png"
    }
    api.app.open_api_schema = open_api_schema
    return open_api_schema


@router.get("/openapi.json", status_code=HTTP_200_OK, tags=['doc'])
async def get_open_api_endpoint():
    return JSONResponse(as_open_api())


@router.get("/docs", status_code=HTTP_200_OK, tags=['doc'])
async def get_documentation():
    return get_swagger_ui_html(openapi_url="/cme/doc/openapi.json", title="swagger-docs", )


@router.get("/redoc", status_code=HTTP_200_OK, tags=['doc'])
async def get_documentation():
    return get_redoc_html(openapi_url="/cme/doc/openapi.json", title="redoc-docs")
