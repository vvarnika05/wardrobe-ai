from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.utils.security import decode_access_token

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    subject = decode_access_token(token)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(subject)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

#this is where authentication is enforced.
#this answers how do i verify that a request is coming from a logged in user
#it converts JWT token into User Object. This is used in the /me endpoint to get the current user. It is also used in other endpoints that require authentication.

# `HTTPBearer()` is a FastAPI security helper that tells FastAPI, **"This endpoint expects authentication using the HTTP Bearer authentication scheme."** In HTTP, a logged-in client (browser, mobile app, Swagger UI, etc.) sends a JWT in the `Authorization` header in the standard format `Authorization: Bearer <JWT_TOKEN>`. When a request reaches a protected route like `/auth/me`, FastAPI automatically calls `HTTPBearer()`, which looks inside the incoming request headers, checks that an `Authorization` header exists and that it begins with the word **Bearer**, extracts only the JWT part (everything after `Bearer`), and returns it as an `HTTPAuthorizationCredentials` object. For example, if the request contains `Authorization: Bearer eyJhbGciOiJIUzI1Ni...`, then `credentials.scheme` will be `"Bearer"` and `credentials.credentials` will be `"eyJhbGciOiJIUzI1Ni..."`. Your code then uses `credentials.credentials` to get the JWT and passes it to `decode_access_token()` for verification. If the header is missing or does not use the Bearer scheme, `HTTPBearer()` rejects the request and FastAPI returns a **401 Unauthorized** response before your route function even executes. In short, `HTTPBearer()` saves you from manually reading and parsing the `Authorization` header and provides the JWT in a clean, standardized way.
