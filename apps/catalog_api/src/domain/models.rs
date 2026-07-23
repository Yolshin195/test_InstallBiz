//! Основные сущности предметной области. Не зависят ни от Axum, ни от
//! конкретного способа хранения данных.

/// Текстовый файл каталога: имя + содержимое.
#[derive(Debug, Clone)]
pub struct FileRecord {
    pub name: String,
    pub content: Vec<u8>,
}

/// Результат отметки файлов скачанными.
#[derive(Debug, Clone, Copy)]
pub struct MarkResult {
    pub marked_now: u32,
    pub already_marked: u32,
}

/// Решение лимитера частоты запросов.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RateLimitDecision {
    Allowed,
    Throttled { retry_after_secs: u64 },
    Banned { retry_after_secs: u64 },
}
