use std::sync::Arc;

use rand::seq::SliceRandom;
use rand::Rng;

use crate::domain::ports::CandidateCatalogPort;

/// Размер случайной порции имён файлов, отдаваемой за один вызов
/// `GET /api/files/names` — от 3 до 9 включительно, как того требует
/// спецификация.
const MIN_PORTION: usize = 3;
const MAX_PORTION: usize = 9;

/// Сценарий "получить случайную порцию имён файлов, ещё не скачанных
/// кандидатом".
pub struct FileNamesService {
    catalog: Arc<dyn CandidateCatalogPort>,
}

impl FileNamesService {
    pub fn new(catalog: Arc<dyn CandidateCatalogPort>) -> Self {
        Self { catalog }
    }

    pub async fn get_random_names(&self, candidate_id: &str) -> Vec<String> {
        let mut pending = self.catalog.pending_names(candidate_id).await;
        if pending.is_empty() {
            return Vec::new();
        }

        let mut rng = rand::thread_rng();
        pending.shuffle(&mut rng);

        let portion = rng.gen_range(MIN_PORTION..=MAX_PORTION).min(pending.len());
        pending.truncate(portion);
        pending
    }
}
