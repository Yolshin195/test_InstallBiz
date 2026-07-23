//! DTO-структуры для HTTP-слоя. Формы и имена полей соответствуют
//! схемам из предоставленного OpenAPI-описания.

use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize)]
pub struct FileNamesResponse {
    pub file_names: Vec<String>,
}

#[derive(Debug, Deserialize)]
pub struct DownloadRequest {
    pub file_names: Vec<String>,
}

#[derive(Debug, Deserialize)]
pub struct MarkDownloadedRequest {
    pub file_names: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct MarkDownloadedResponse {
    pub marked_now: u32,
    pub already_marked: u32,
}

#[derive(Debug, Serialize)]
pub struct ResetResponse {
    pub reset: bool,
}

#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub detail: String,
}

#[derive(Debug, Serialize)]
pub struct ValidationErrorItem {
    pub loc: Vec<String>,
    pub msg: String,
    #[serde(rename = "type")]
    pub kind: String,
}

#[derive(Debug, Serialize)]
pub struct HttpValidationError {
    pub detail: Vec<ValidationErrorItem>,
}
