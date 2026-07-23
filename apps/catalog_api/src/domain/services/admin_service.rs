use std::sync::Arc;

use crate::domain::ports::{CandidateCatalogPort, RateLimiterPort};

/// Служебные сценарии для администрирования: сброс прогресса кандидата
/// и снятие бана/троттлинга клиента. Проверка `X-Admin-Token`
/// выполняется на HTTP-слое (это деталь транспорта, а не бизнес-правило),
/// сюда сервис попадает только если токен уже подтверждён.
pub struct AdminService {
    catalog: Arc<dyn CandidateCatalogPort>,
    rate_limiter: Arc<dyn RateLimiterPort>,
}

impl AdminService {
    pub fn new(catalog: Arc<dyn CandidateCatalogPort>, rate_limiter: Arc<dyn RateLimiterPort>) -> Self {
        Self {
            catalog,
            rate_limiter,
        }
    }

    pub async fn reset_candidate_progress(&self, candidate_id: &str) -> bool {
        self.catalog.reset(candidate_id).await
    }

    pub async fn reset_client_throttling(&self, client_ip: &str) -> bool {
        self.rate_limiter.reset(client_ip).await
    }
}
