// Taza-Gojo School — desktop shell (Tauri 2).
// Wraps the same React build as the PWA so schools and computer labs can run a
// native window. Build with the Tauri CLI; see docs/desktop.md.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running Taza-Gojo desktop");
}
