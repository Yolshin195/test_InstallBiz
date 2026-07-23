# ЭТАП 1: Подготовка рецепта зависимостей для workspace
FROM rust:slim AS chef
RUN cargo install cargo-chef
WORKDIR /app

FROM chef AS planner
# Копируем всё из корня контекста в рабочую директорию контейнера
COPY . .
RUN cargo chef prepare --recipe-path recipe.json

# ЭТАП 2: Сборка самого приложения
FROM chef AS builder
WORKDIR /app

# Копируем сгенерированный рецепт
COPY --from=planner /app/recipe.json recipe.json

# Кэшируем сборку зависимостей воркспейса
RUN cargo chef cook --release --recipe-path recipe.json

# Копируем весь исходный код воркспейса целиком из корня контекста
COPY . .

# Собираем конкретный бинарник через воркспейс
RUN cargo build --release --bin test_catalog_api -p test_catalog_api

# ЭТАП 3: Финальный легковесный образ для продакшена
FROM debian:bookworm-slim AS runtime

RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем бинарник из общей папки target/release воркспейса
COPY --from=builder /app/target/release/test_catalog_api /app/test_catalog_api

EXPOSE 8080

CMD ["./test_catalog_api"]