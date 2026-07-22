use thiserror::Error;

/// Ошибки уровня предметной области. HTTP-слой сам решает, в какой
/// код ответа их превратить — домен ничего не знает про HTTP.
#[derive(Debug, Error)]
pub enum DomainError {
    #[error("часть запрошенных файлов отсутствует в каталоге: {0:?}")]
    FilesNotFound(Vec<String>),

    #[error("ошибка валидации: {0}")]
    Validation(String),
}
