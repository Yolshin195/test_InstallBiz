use axum::http::{header, StatusCode};
use axum::response::{Html, IntoResponse, Response};

/// Спецификация OpenAPI ровно в том виде, в котором она была
/// предоставлена в задании — отдаётся как есть, без перегенерации,
/// чтобы гарантированно совпадать 1-в-1.
const OPENAPI_JSON: &str = include_str!("openapi.json");

pub async fn openapi_json() -> Response {
    (
        StatusCode::OK,
        [(header::CONTENT_TYPE, "application/json")],
        OPENAPI_JSON,
    )
        .into_response()
}

const SWAGGER_HTML: &str = r##"<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8" />
    <title>Сервис файлов — документация API</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
    <style>body { margin: 0; }</style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        window.onload = () => {
            window.ui = SwaggerUIBundle({
                url: "/openapi.json",
                dom_id: "#swagger-ui",
                presets: [SwaggerUIBundle.presets.apis],
                layout: "BaseLayout",
            });
        };
    </script>
</body>
</html>"##;

pub async fn swagger_ui() -> Html<&'static str> {
    Html(SWAGGER_HTML)
}
