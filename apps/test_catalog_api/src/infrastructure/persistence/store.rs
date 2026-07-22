use std::collections::{HashMap, HashSet};
use std::sync::RwLock;

use rand::Rng;
use uuid::Uuid;

use crate::domain::models::FileRecord;

/// Данные конкретного кандидата: полный набор назначенных ему имён
/// файлов (генерируется один раз, лениво, при первом обращении) и
/// множество тех из них, что он уже отметил скачанными.
struct CandidateEntry {
    assigned: Vec<String>,
    downloaded: HashSet<String>,
}

struct StoreInner {
    candidates: HashMap<String, CandidateEntry>,
    files: HashMap<String, FileRecord>,
}

/// Общее in-memory хранилище, на котором построены адаптеры
/// `InMemoryCandidateCatalog` и `InMemoryFileStore`. Вынесено в отдельный
/// тип, потому что оба порта должны согласованно смотреть на одни и те
/// же данные (имена файлов кандидата берутся из того же пространства
/// имён, что и глобальное хранилище содержимого).
pub struct Store {
    inner: RwLock<StoreInner>,
    catalog_min_files: usize,
    catalog_max_files: usize,
}

impl Store {
    pub fn new(catalog_min_files: usize, catalog_max_files: usize) -> Self {
        Self {
            inner: RwLock::new(StoreInner {
                candidates: HashMap::new(),
                files: HashMap::new(),
            }),
            catalog_min_files: catalog_min_files.max(1),
            catalog_max_files: catalog_max_files.max(catalog_min_files.max(1)),
        }
    }

    /// Гарантирует, что для кандидата уже сгенерирован каталог: если
    /// он обращается впервые, ему случайно назначается от
    /// `catalog_min_files` до `catalog_max_files` файлов со
    /// сгенерированным содержимым.
    fn ensure_candidate(&self, inner: &mut StoreInner, candidate_id: &str) {
        if inner.candidates.contains_key(candidate_id) {
            return;
        }

        let mut rng = rand::thread_rng();
        let count = rng.gen_range(self.catalog_min_files..=self.catalog_max_files);

        let mut assigned = Vec::with_capacity(count);
        for _ in 0..count {
            let name = format!("{}.txt", Uuid::new_v4());
            let content = generate_file_content(&name);
            inner
                .files
                .entry(name.clone())
                .or_insert_with(|| FileRecord {
                    name: name.clone(),
                    content,
                });
            assigned.push(name);
        }

        inner.candidates.insert(
            candidate_id.to_string(),
            CandidateEntry {
                assigned,
                downloaded: HashSet::new(),
            },
        );
    }

    pub fn pending_names(&self, candidate_id: &str) -> Vec<String> {
        let mut inner = self.inner.write().expect("store lock poisoned");
        self.ensure_candidate(&mut inner, candidate_id);
        let entry = inner
            .candidates
            .get(candidate_id)
            .expect("candidate just ensured to exist");
        entry
            .assigned
            .iter()
            .filter(|name| !entry.downloaded.contains(*name))
            .cloned()
            .collect()
    }

    pub fn mark_downloaded(&self, candidate_id: &str, names: &[String]) -> (u32, u32) {
        let mut inner = self.inner.write().expect("store lock poisoned");
        self.ensure_candidate(&mut inner, candidate_id);
        let entry = inner
            .candidates
            .get_mut(candidate_id)
            .expect("candidate just ensured to exist");

        let mut marked_now = 0u32;
        let mut already_marked = 0u32;
        for name in names {
            if entry.downloaded.insert(name.clone()) {
                marked_now += 1;
            } else {
                already_marked += 1;
            }
        }
        (marked_now, already_marked)
    }

    pub fn reset_candidate(&self, candidate_id: &str) -> bool {
        let mut inner = self.inner.write().expect("store lock poisoned");
        match inner.candidates.get_mut(candidate_id) {
            Some(entry) => {
                entry.downloaded.clear();
                true
            }
            None => false,
        }
    }

    pub fn check_exist(&self, names: &[String]) -> Result<(), Vec<String>> {
        let inner = self.inner.read().expect("store lock poisoned");
        let missing: Vec<String> = names
            .iter()
            .filter(|name| !inner.files.contains_key(name.as_str()))
            .cloned()
            .collect();
        if missing.is_empty() {
            Ok(())
        } else {
            Err(missing)
        }
    }

    pub fn get_many(&self, names: &[String]) -> Result<Vec<FileRecord>, Vec<String>> {
        let inner = self.inner.read().expect("store lock poisoned");
        let mut result = Vec::with_capacity(names.len());
        let mut missing = Vec::new();
        for name in names {
            match inner.files.get(name.as_str()) {
                Some(record) => result.push(record.clone()),
                None => missing.push(name.clone()),
            }
        }
        if missing.is_empty() {
            Ok(result)
        } else {
            Err(missing)
        }
    }
}

/// Генерирует псевдослучайное текстовое содержимое файла — набор из
/// нескольких предложений на основе небольшого банка слов.
fn generate_file_content(name: &str) -> Vec<u8> {
    const WORDS: &[&str] = &[
        "lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit", "sed",
        "do", "eiusmod", "tempor", "incididunt", "ut", "labore", "et", "dolore", "magna",
        "aliqua", "candidate", "file", "service", "test", "task", "download", "archive",
        "catalog", "random", "content", "sample", "data",
    ];

    let mut rng = rand::thread_rng();
    let sentence_count = rng.gen_range(3..=8);
    let mut text = format!("# {name}\n\n");

    for _ in 0..sentence_count {
        let word_count = rng.gen_range(6..=14);
        let mut sentence: Vec<&str> = (0..word_count)
            .map(|_| WORDS[rng.gen_range(0..WORDS.len())])
            .collect();
        if let Some(first) = sentence.first_mut() {
            let capitalized = capitalize(first);
            text.push_str(&capitalized);
            sentence.remove(0);
        }
        for word in sentence {
            text.push(' ');
            text.push_str(word);
        }
        text.push_str(".\n");
    }

    text.into_bytes()
}

fn capitalize(word: &str) -> String {
    let mut chars = word.chars();
    match chars.next() {
        Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
        None => String::new(),
    }
}
