use std::sync::Arc;

use async_trait::async_trait;

use crate::domain::models::FileRecord;
use crate::domain::ports::{CandidateCatalogPort, FileStorePort};

use super::store::Store;

/// Адаптер `CandidateCatalogPort` поверх общего in-memory хранилища.
/// Тонкая обёртка: вся логика — в `Store`, здесь только реализация
/// трейта порта.
pub struct InMemoryCandidateCatalog {
    store: Arc<Store>,
}

impl InMemoryCandidateCatalog {
    pub fn new(store: Arc<Store>) -> Self {
        Self { store }
    }
}

#[async_trait]
impl CandidateCatalogPort for InMemoryCandidateCatalog {
    async fn pending_names(&self, candidate_id: &str) -> Vec<String> {
        self.store.pending_names(candidate_id)
    }

    async fn mark_downloaded(&self, candidate_id: &str, names: &[String]) -> (u32, u32) {
        self.store.mark_downloaded(candidate_id, names)
    }

    async fn reset(&self, candidate_id: &str) -> bool {
        self.store.reset_candidate(candidate_id)
    }
}

/// Адаптер `FileStorePort` поверх того же общего in-memory хранилища.
pub struct InMemoryFileStore {
    store: Arc<Store>,
}

impl InMemoryFileStore {
    pub fn new(store: Arc<Store>) -> Self {
        Self { store }
    }
}

#[async_trait]
impl FileStorePort for InMemoryFileStore {
    async fn check_exist(&self, names: &[String]) -> Result<(), Vec<String>> {
        self.store.check_exist(names)
    }

    async fn get_many(&self, names: &[String]) -> Result<Vec<FileRecord>, Vec<String>> {
        self.store.get_many(names)
    }
}
