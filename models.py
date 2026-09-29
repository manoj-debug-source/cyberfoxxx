from pydantic import BaseModel


class IdentityRequest(BaseModel):
    full_name: str
    date_of_birth: str
    gender: str
    id_type: str
    id_number: str
    address: str
    phone: str
    