use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, Instant};

use async_trait::async_trait;

use crate::domain::models::RateLimitDecision;
use crate::domain::ports::RateLimiterPort;

/// Состояние одного клиента (по IP).
struct ClientState {
    /// Начало текущего окна подсчёта запросов.
    window_start: Instant,
    /// Сколько запросов клиент сделал в текущем окне.
    requests_in_window: u32,
    /// Сколько раз подряд (в рамках текущего окна) клиент превышал
    /// лимит — используется, чтобы решить, пора ли банить.
    violations_in_window: u32,
    /// Если клиент забанен — момент, до которого действует бан.
    banned_until: Option<Instant>,
}

impl ClientState {
    fn fresh(now: Instant) -> Self {
        Self {
            window_start: now,
            requests_in_window: 0,
            violations_in_window: 0,
            banned_until: None,
        }
    }
}

/// Простой in-memory лимитер частоты запросов с эскалацией в бан.
///
/// Алгоритм:
/// 1. Если клиент сейчас забанен — 403 с оставшимся временем бана.
/// 2. Иначе считаем запросы в скользящем фиксированном окне
///    (`window_secs`). Как только окно истекло — счётчики обнуляются.
/// 3. Пока запросов в окне не больше лимита — запрос разрешён.
/// 4. Как только лимит превышен — 429, а счётчик нарушений в этом
///    окне увеличивается.
/// 5. Если нарушений в одном окне набралось `ban_threshold` — клиент
///    банится на `ban_duration_secs`.
pub struct InMemoryRateLimiter {
    clients: Mutex<HashMap<String, ClientState>>,
    limit_per_window: u32,
    window: Duration,
    ban_threshold: u32,
    ban_duration: Duration,
}

impl InMemoryRateLimiter {
    pub fn new(
        limit_per_window: u32,
        window_secs: u64,
        ban_threshold: u32,
        ban_duration_secs: u64,
    ) -> Self {
        Self {
            clients: Mutex::new(HashMap::new()),
            limit_per_window: limit_per_window.max(1),
            window: Duration::from_secs(window_secs.max(1)),
            ban_threshold: ban_threshold.max(1),
            ban_duration: Duration::from_secs(ban_duration_secs.max(1)),
        }
    }
}

#[async_trait]
impl RateLimiterPort for InMemoryRateLimiter {
    async fn check(&self, client_key: &str) -> RateLimitDecision {
        let now = Instant::now();
        let mut clients = self.clients.lock().expect("rate limiter lock poisoned");
        let state = clients
            .entry(client_key.to_string())
            .or_insert_with(|| ClientState::fresh(now));

        // Уже забанен?
        if let Some(banned_until) = state.banned_until {
            if now < banned_until {
                let retry_after_secs = (banned_until - now).as_secs().max(1);
                return RateLimitDecision::Banned { retry_after_secs };
            }
            // бан истёк — начинаем с чистого листа
            *state = ClientState::fresh(now);
        }

        // Истекло окно — сбрасываем счётчики.
        if now.duration_since(state.window_start) >= self.window {
            state.window_start = now;
            state.requests_in_window = 0;
            state.violations_in_window = 0;
        }

        state.requests_in_window += 1;

        if state.requests_in_window <= self.limit_per_window {
            return RateLimitDecision::Allowed;
        }

        // Лимит превышен в этом окне.
        state.violations_in_window += 1;

        if state.violations_in_window >= self.ban_threshold {
            let banned_until = now + self.ban_duration;
            state.banned_until = Some(banned_until);
            return RateLimitDecision::Banned {
                retry_after_secs: self.ban_duration.as_secs(),
            };
        }

        let elapsed = now.duration_since(state.window_start);
        let retry_after_secs = self.window.saturating_sub(elapsed).as_secs().max(1);
        RateLimitDecision::Throttled { retry_after_secs }
    }

    async fn reset(&self, client_key: &str) -> bool {
        let mut clients = self.clients.lock().expect("rate limiter lock poisoned");
        clients.remove(client_key).is_some()
    }
}
