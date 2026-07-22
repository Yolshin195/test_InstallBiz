use std::sync::Arc;

use crate::domain::errors::DomainError;
use crate::domain::models::FileRecord;
use crate::domain::ports::FileStorePort;

/// Максимум файлов за один запрос на скачивание — намеренное
/// ограничение из спецификации, скачать "всё и сразу" нельзя.
pub const MAX_DOWNLOAD_BATCH: usize = 3;

/// Сценарий "скачать файлы по именам одним ZIP-архивом".
pub struct DownloadService {
    store: Arc<dyn FileStorePort>,
}

impl DownloadService {
    pub fn new(store: Arc<dyn FileStorePort>) -> Self {
        Self { store }
    }

    pub async fn download(&self, names: &[String]) -> Result<Vec<FileRecord>, DomainError> {
        if names.is_empty() {
            return Err(DomainError::Validation(
                "file_names не может быть пустым".to_string(),
            ));
        }
        if names.len() > MAX_DOWNLOAD_BATCH {
            return Err(DomainError::Validation(format!(
                "за один запрос можно скачать не более {MAX_DOWNLOAD_BATCH} файлов"
            )));
        }

        self.store
            .get_many(names)
            .await
            .map_err(DomainError::FilesNotFound)
    }
}
