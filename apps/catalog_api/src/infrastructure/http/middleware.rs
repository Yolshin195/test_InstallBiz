use std::net::SocketAddr;

use axum::body::Body;
use axum::extract::{ConnectInfo, Request, State};
use axum::http::{HeaderValue, StatusCode};
use axum::middleware::Next;
use axum::response::{IntoResponse, Response};
use axum::Json;

use crate::domain::models::RateLimitDecision;

use super::app_state::AppState;
use super::dto::ErrorResponse;

/// Идентификация клиента для целей троттлинга — всегда по IP-адресу
/// подключения, независимо от `X-Candidate-Id` (согласовано со
/// служебной ручкой `/api/admin/clients/{client_ip}/throttling`,
/// которая тоже оперирует IP).
pub async fn rate_limit(
    State(state): State<AppState>,
    ConnectInfo(addr): ConnectInfo<SocketAddr>,
    request: Request<Body>,
    next: Next,
) -> Response {
    let client_key = addr.ip().to_string();

    match state.rate_limiter.check(&client_key).await {
        RateLimitDecision::Allowed => next.run(request).await,
        RateLimitDecision::Throttled { retry_after_secs } => {
            rate_limit_response(StatusCode::TOO_MANY_REQUESTS, retry_after_secs, "превышена допустимая частота запросов")
        }
        RateLimitDecision::Banned { retry_after_secs } => rate_limit_response(
            StatusCode::FORBIDDEN,
            retry_after_secs,
            &format!(
                "клиент временно заблокирован за злоупотребление запросами, повторите через {retry_after_secs} с"
            ),
        ),
    }
}

fn rate_limit_response(status: StatusCode, retry_after_secs: u64, detail: &str) -> Response {
    let mut response = (
        status,
        Json(ErrorResponse {
            detail: detail.to_string(),
        }),
    )
        .into_response();

    if let Ok(value) = HeaderValue::from_str(&retry_after_secs.to_string()) {
        response.headers_mut().insert("Retry-After", value);
    }

    response
}
