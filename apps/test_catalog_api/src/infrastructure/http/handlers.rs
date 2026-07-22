use std::io::{Cursor, Write};
use std::net::SocketAddr;

use axum::extract::{ConnectInfo, Path, State};
use axum::http::{header, HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::Json;

use crate::domain::errors::DomainError;
use crate::domain::models::FileRecord;

use super::app_state::AppState;
use super::dto::{
    DownloadRequest, ErrorResponse, FileNamesResponse, MarkDownloadedRequest,
    MarkDownloadedResponse, ResetResponse,
};
use super::extractors::ValidatedJson;

const CANDIDATE_HEADER: &str = "x-candidate-id";
const ADMIN_TOKEN_HEADER: &str = "x-admin-token";

/// Определить идентификатор кандидата: явный заголовок
/// `X-Candidate-Id`, если он задан и не пуст, иначе — IP-адрес клиента.
fn candidate_id_from(headers: &HeaderMap, addr: SocketAddr) -> String {
    headers
        .get(CANDIDATE_HEADER)
        .and_then(|v| v.to_str().ok())
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(str::to_string)
        .unwrap_or_else(|| addr.ip().to_string())
}

fn error_json(status: StatusCode, detail: impl Into<String>) -> Response {
    (
        status,
        Json(ErrorResponse {
            detail: detail.into(),
        }),
    )
        .into_response()
}

fn domain_error_response(err: DomainError) -> Response {
    match err {
        DomainError::FilesNotFound(missing) => error_json(
            StatusCode::NOT_FOUND,
            format!(
                "часть запрошенных файлов отсутствует в каталоге: {}",
                missing.join(", ")
            ),
        ),
        DomainError::Validation(msg) => error_json(StatusCode::UNPROCESSABLE_ENTITY, msg),
    }
}

fn check_admin_token(headers: &HeaderMap, expected: &str) -> bool {
    headers
        .get(ADMIN_TOKEN_HEADER)
        .and_then(|v| v.to_str().ok())
        .map(|token| token == expected)
        .unwrap_or(false)
}

fn admin_forbidden() -> Response {
    error_json(
        StatusCode::FORBIDDEN,
        "неверный или отсутствующий токен администратора",
    )
}

// ---- GET /api/files/names ----

pub async fn get_file_names(
    State(state): State<AppState>,
    ConnectInfo(addr): ConnectInfo<SocketAddr>,
    headers: HeaderMap,
) -> Response {
    let candidate_id = candidate_id_from(&headers, addr);
    let file_names = state
        .file_names_service
        .get_random_names(&candidate_id)
        .await;
    Json(FileNamesResponse { file_names }).into_response()
}

// ---- POST /api/files/download ----

pub async fn download_files(
    State(state): State<AppState>,
    ValidatedJson(payload): ValidatedJson<DownloadRequest>,
) -> Response {
    match state.download_service.download(&payload.file_names).await {
        Ok(files) => build_zip_response(&files),
        Err(err) => domain_error_response(err),
    }
}

fn build_zip_response(files: &[FileRecord]) -> Response {
    let mut cursor = Cursor::new(Vec::new());
    {
        let mut zip = zip::ZipWriter::new(&mut cursor);
        let options: zip::write::FileOptions =
            zip::write::FileOptions::default().compression_method(zip::CompressionMethod::Deflated);

        for file in files {
            if zip.start_file(&file.name, options).is_err() || zip.write_all(&file.content).is_err()
            {
                return error_json(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "не удалось сформировать ZIP-архив",
                );
            }
        }

        if zip.finish().is_err() {
            return error_json(
                StatusCode::INTERNAL_SERVER_ERROR,
                "не удалось сформировать ZIP-архив",
            );
        }
    }

    let bytes = cursor.into_inner();
    Response::builder()
        .status(StatusCode::OK)
        .header(header::CONTENT_TYPE, "application/zip")
        .header(
            header::CONTENT_DISPOSITION,
            "attachment; filename=\"files.zip\"",
        )
        .body(axum::body::Body::from(bytes))
        .unwrap_or_else(|_| {
            error_json(StatusCode::INTERNAL_SERVER_ERROR, "не удалось собрать ответ")
        })
}

// ---- POST /api/files/downloaded ----

pub async fn mark_downloaded(
    State(state): State<AppState>,
    ConnectInfo(addr): ConnectInfo<SocketAddr>,
    headers: HeaderMap,
    ValidatedJson(payload): ValidatedJson<MarkDownloadedRequest>,
) -> Response {
    let candidate_id = candidate_id_from(&headers, addr);
    match state
        .mark_downloaded_service
        .mark(&candidate_id, &payload.file_names)
        .await
    {
        Ok(result) => Json(MarkDownloadedResponse {
            marked_now: result.marked_now,
            already_marked: result.already_marked,
        })
        .into_response(),
        Err(err) => domain_error_response(err),
    }
}

// ---- DELETE /api/admin/candidates/{candidate_id}/progress ----

pub async fn reset_candidate_progress(
    State(state): State<AppState>,
    Path(candidate_id): Path<String>,
    headers: HeaderMap,
) -> Response {
    if !check_admin_token(&headers, &state.admin_token) {
        return admin_forbidden();
    }
    let reset = state
        .admin_service
        .reset_candidate_progress(&candidate_id)
        .await;
    Json(ResetResponse { reset }).into_response()
}

// ---- DELETE /api/admin/clients/{client_ip}/throttling ----

pub async fn reset_client_throttling(
    State(state): State<AppState>,
    Path(client_ip): Path<String>,
    headers: HeaderMap,
) -> Response {
    if !check_admin_token(&headers, &state.admin_token) {
        return admin_forbidden();
    }
    let reset = state
        .admin_service
        .reset_client_throttling(&client_ip)
        .await;
    Json(ResetResponse { reset }).into_response()
}
