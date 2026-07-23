use axum::routing::{delete, get, post};
use axum::Router;

use tower_http::trace::TraceLayer;

use super::app_state::AppState;
use super::{handlers, middleware as http_middleware, openapi};

pub fn build_router(state: AppState) -> Router {
    let files_routes = Router::new()
        .route("/api/files/names", get(handlers::get_file_names))
        .route("/api/files/download", post(handlers::download_files))
        .route("/api/files/downloaded", post(handlers::mark_downloaded))
        .layer(axum::middleware::from_fn_with_state(
            state.clone(),
            http_middleware::rate_limit,
        ));

    let admin_routes = Router::new().route(
        "/api/admin/candidates/:candidate_id/progress",
        delete(handlers::reset_candidate_progress),
    )
    .route(
        "/api/admin/clients/:client_ip/throttling",
        delete(handlers::reset_client_throttling),
    );

    let docs_routes = Router::new()
        .route("/openapi.json", get(openapi::openapi_json))
        .route("/docs", get(openapi::swagger_ui));

    Router::new()
        .merge(files_routes)
        .merge(admin_routes)
        .merge(docs_routes)
        .with_state(state)
        .layer(TraceLayer::new_for_http())
}
