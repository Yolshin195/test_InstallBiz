mod domain;
mod infrastructure;

use std::net::SocketAddr;
use std::sync::Arc;

use tracing_subscriber::EnvFilter;

use domain::ports::{CandidateCatalogPort, FileStorePort, RateLimiterPort};
use domain::services::{AdminService, DownloadService, FileNamesService, MarkDownloadedService};
use infrastructure::config::AppConfig;
use infrastructure::http::{build_router, AppState};
use infrastructure::persistence::{InMemoryCandidateCatalog, InMemoryFileStore, InMemoryRateLimiter, Store};

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")))
        .init();

    let config = AppConfig::from_env();

    if config.admin_token_is_default {
        tracing::warn!(
            "ADMIN_TOKEN не задан в окружении — используется dev-токен по умолчанию ('{}'). \
             Задайте ADMIN_TOKEN для боевого окружения.",
            config.admin_token
        );
    }

    tracing::info!(
        rate_limit_per_window = config.rate_limit_per_window,
        rate_limit_window_secs = config.rate_limit_window_secs,
        rate_limit_ban_threshold = config.rate_limit_ban_threshold,
        rate_limit_ban_duration_secs = config.rate_limit_ban_duration_secs,
        catalog_min_files = config.catalog_min_files,
        catalog_max_files = config.catalog_max_files,
        "конфигурация загружена"
    );

    // ---- Infrastructure: адаптеры хранения (in-memory) ----
    let store = Arc::new(Store::new(config.catalog_min_files, config.catalog_max_files));
    let candidate_catalog: Arc<dyn CandidateCatalogPort> =
        Arc::new(InMemoryCandidateCatalog::new(store.clone()));
    let file_store: Arc<dyn FileStorePort> = Arc::new(InMemoryFileStore::new(store.clone()));
    let rate_limiter: Arc<dyn RateLimiterPort> = Arc::new(InMemoryRateLimiter::new(
        config.rate_limit_per_window,
        config.rate_limit_window_secs,
        config.rate_limit_ban_threshold,
        config.rate_limit_ban_duration_secs,
    ));

    // ---- Domain: use-case сервисы, зависят только от портов ----
    let file_names_service = Arc::new(FileNamesService::new(candidate_catalog.clone()));
    let download_service = Arc::new(DownloadService::new(file_store.clone()));
    let mark_downloaded_service = Arc::new(MarkDownloadedService::new(
        candidate_catalog.clone(),
        file_store.clone(),
    ));
    let admin_service = Arc::new(AdminService::new(
        candidate_catalog.clone(),
        rate_limiter.clone(),
    ));

    let state = AppState {
        file_names_service,
        download_service,
        mark_downloaded_service,
        admin_service,
        rate_limiter,
        admin_token: Arc::new(config.admin_token.clone()),
    };

    let app = build_router(state);

    let addr: SocketAddr = format!("{}:{}", config.host, config.port)
        .parse()
        .expect("некорректный host:port");

    tracing::info!("сервис запущен на http://{addr}, документация на /docs");

    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .expect("не удалось забиндить адрес");

    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<SocketAddr>(),
    )
    .await
    .expect("ошибка при работе сервера");
}
