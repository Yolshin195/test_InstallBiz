use axum::extract::rejection::JsonRejection;
use axum::extract::{FromRequest, Request};
use axum::response::{IntoResponse, Response};
use axum::http::StatusCode;
use axum::{async_trait, Json};
use serde::de::DeserializeOwned;

use super::dto::{HttpValidationError, ValidationErrorItem};

/// Обёртка над `axum::Json`, которая при ошибке разбора тела
/// возвращает `422 Unprocessable Entity` с телом в формате
/// `HTTPValidationError`, как это делает FastAPI/Pydantic, а не
/// стандартный axum-овский `400 Bad Request`.
pub struct ValidatedJson<T>(pub T);

#[async_trait]
impl<T, S> FromRequest<S> for ValidatedJson<T>
where
    T: DeserializeOwned,
    S: Send + Sync,
{
    type Rejection = Response;

    async fn from_request(req: Request, state: &S) -> Result<Self, Self::Rejection> {
        match Json::<T>::from_request(req, state).await {
            Ok(Json(value)) => Ok(ValidatedJson(value)),
            Err(rejection) => Err(validation_error_response(rejection)),
        }
    }
}

fn validation_error_response(rejection: JsonRejection) -> Response {
    let body = HttpValidationError {
        detail: vec![ValidationErrorItem {
            loc: vec!["body".to_string()],
            msg: rejection.to_string(),
            kind: "value_error".to_string(),
        }],
    };
    (StatusCode::UNPROCESSABLE_ENTITY, Json(body)).into_response()
}
