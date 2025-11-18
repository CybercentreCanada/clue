from pydantic import BaseModel


class Result(BaseModel):
    "Base result object"

    @staticmethod
    def format() -> str:
        "Return the format of the result"
        raise NotImplementedError()
