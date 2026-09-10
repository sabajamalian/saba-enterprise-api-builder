import logging

import uvicorn


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    uvicorn.run("saba_api.main:app", host="127.0.0.1", port=8000, access_log=False)


if __name__ == "__main__":
    main()
