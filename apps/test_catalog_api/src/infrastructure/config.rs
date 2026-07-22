use std::env;

/// Дефолтный admin-токен для dev-окружения. Используется, только если
/// переменная окружения `ADMIN_TOKEN` не задана — при этом сервис
/// явно предупреждает об этом в логах при старте.
pub const DEV_DEFAULT_ADMIN_TOKEN: &str = "dev-admin-token";

#[derive(Debug, Clone)]
pub struct AppConfig {
    pub host: String,
    pub port: u16,

    /// Токен для служебных ручек `/api/admin/*` (заголовок `X-Admin-Token`).
    pub admin_token: String,
    /// true, если admin_token взят из дефолта, а не из окружения.
    pub admin_token_is_default: bool,

    /// Сколько запросов от одного клиента (IP) разрешено за одно окно.
    pub rate_limit_per_window: u32,
    /// Длительность окна лимитера, в секундах.
    pub rate_limit_window_secs: u64,
    /// После скольких запросов "поверх лимита" внутри окна клиент
    /// уходит в бан.
    pub rate_limit_ban_threshold: u32,
    /// Длительность бана, в секундах (по умолчанию — 30 минут).
    pub rate_limit_ban_duration_secs: u64,

    /// Границы случайного размера каталога, генерируемого кандидату
    /// при первом обращении.
    pub catalog_min_files: usize,
    pub catalog_max_files: usize,
}

fn env_or<T: std::str::FromStr>(key: &str, default: T) -> T {
    env::var(key)
        .ok()
        .and_then(|v| v.parse::<T>().ok())
        .unwrap_or(default)
}

impl AppConfig {
    pub fn from_env() -> Self {
        let admin_token_env = env::var("ADMIN_TOKEN").ok();
        let admin_token_is_default = admin_token_env.is_none();
        let admin_token = admin_token_env.unwrap_or_else(|| DEV_DEFAULT_ADMIN_TOKEN.to_string());

        let catalog_min_files = env_or("CATALOG_MIN_FILES", 200usize);
        let catalog_max_files = env_or("CATALOG_MAX_FILES", 1000usize);

        Self {
            host: env::var("HOST").unwrap_or_else(|_| "0.0.0.0".to_string()),
            port: env_or("PORT", 5050u16),

            admin_token,
            admin_token_is_default,

            rate_limit_per_window: env_or("RATE_LIMIT_PER_WINDOW", 20u32),
            rate_limit_window_secs: env_or("RATE_LIMIT_WINDOW_SECS", 60u64),
            rate_limit_ban_threshold: env_or("RATE_LIMIT_BAN_THRESHOLD", 3u32),
            rate_limit_ban_duration_secs: env_or("RATE_LIMIT_BAN_DURATION_SECS", 1800u64),

            catalog_min_files: catalog_min_files.min(catalog_max_files),
            catalog_max_files: catalog_max_files.max(catalog_min_files),
        }
    }
}
