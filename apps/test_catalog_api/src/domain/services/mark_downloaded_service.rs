use std::sync::Arc;

use crate::domain::errors::DomainError;
use crate::domain::models::MarkResult;
use crate::domain::ports::{CandidateCatalogPort, FileStorePort};

/// Сценарий "отметить файлы скачанными кандидатом".
pub struct MarkDownloadedService {
    catalog: Arc<dyn CandidateCatalogPort>,
    store: Arc<dyn FileStorePort>,
}

impl MarkDownloadedService {
    pub fn new(catalog: Arc<dyn CandidateCatalogPort>, store: Arc<dyn FileStorePort>) -> Self {
        Self { catalog, store }
    }

    pub async fn mark(
        &self,
        candidate_id: &str,
        names: &[String],
    ) -> Result<MarkResult, DomainError> {
        if names.is_empty() {
            return Err(DomainError::Validation(
                "file_names не может быть пустым".to_string(),
            ));
        }

        self.store
            .check_exist(names)
            .await
            .map_err(DomainError::FilesNotFound)?;

        let (marked_now, already_marked) = self.catalog.mark_downloaded(candidate_id, names).await;
        Ok(MarkResult {
            marked_now,
            already_marked,
        })
    }
}
