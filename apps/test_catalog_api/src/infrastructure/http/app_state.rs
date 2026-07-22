use std::sync::Arc;

use crate::domain::ports::RateLimiterPort;
use crate::domain::services::{AdminService, DownloadService, FileNamesService, MarkDownloadedService};

#[derive(Clone)]
pub struct AppState {
    pub file_names_service: Arc<FileNamesService>,
    pub download_service: Arc<DownloadService>,
    pub mark_downloaded_service: Arc<MarkDownloadedService>,
    pub admin_service: Arc<AdminService>,
    pub rate_limiter: Arc<dyn RateLimiterPort>,
    pub admin_token: Arc<String>,
}
