#!/usr/bin/env python3

import uvicorn

from src.utils.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to True for development
        log_level=settings.log_level.lower(),
    )
