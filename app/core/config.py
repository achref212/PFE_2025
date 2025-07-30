from pydantic import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str
    authjwt_secret_key: str
    authjwt_algorithm: str = "HS256"
    authjwt_token_location: set = {"headers"}
    authjwt_header_name: str = "Authorization"
    authjwt_header_type: str = "Bearer"
    authjwt_access_token_expires: int = 3600
    authjwt_refresh_token_expires: int = 604800  # 7 days
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    EMAIL_SENDER: str
    EMAIL_PASSWORD: str
    EMAIL_HOST: str
    EMAIL_PORT: int
    EMAIL_USE_SSL: bool
    EMAIL_DEFAULT_SENDER: str
    RESET_CODE_EXPIRES: int = 1800  # 30 minutes
    REGISTRATION_CODE_EXPIRES: int = 1800  # 30 minutes
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()