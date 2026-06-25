from fastAPI import Request

from fastAPI.responses import JSONResponse

from logger import logger

async def catch_exception_middleware(request : Request,call_next):
    try: 
        return await call_next(request)
    except Exception as exc:
        logger.exception("UNHANDLED EXCEPTION")
        return JSONResponse(status_code = 500,contents={"error": str(exc)})
    