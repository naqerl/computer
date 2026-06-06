# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-06-06

### Fixed

- 📱 **Improved mobile keyboard handling.** The terminal and chat now resize correctly when the on-screen keyboard opens on iOS and Android.
- 📱 **Fixed page bouncing on mobile.** Eliminated unwanted page scrolling and bounce effects on touch devices.

### Changed

- 🔄 **Model selection syncs across devices.** Your selected chat model now persists across browsers and devices instead of being saved locally.

## [0.1.1] - 2026-06-06

### Fixed

- 🛑 **File browser no longer refreshes constantly.** Replaced the macOS `PollingObserver` (which generated a feedback loop of phantom filesystem events) with the native `FSEventsObserver`. Background refreshes are now silent — no more loading spinner flash on every update.
- 🔇 **Eliminated noisy filesystem watcher events.** The watcher now ignores changes in `.git`, `__pycache__`, `.DS_Store`, and `node_modules` directories, which were triggering unnecessary file browser refreshes.
- ⚡ **Centralized git status store.** All components (GitBar, GitView, FileEditor, layout) now share a single `gitStatusStore` instead of each independently polling `git/status`. On page load, this reduces git status API calls from ~6+ down to 1.
- 🔁 **Reduced git polling frequency.** Removed the 5-second git status polling intervals that were running in multiple components simultaneously.

## [0.1.0] - 2026-06-06

### Added

- 🚀 **Initial release.** First public version of cptr: your computer, from anywhere. Code, manage, and control your machine from the web.
- 🖥️ **Terminal emulator.** Full PTY-backed terminal accessible from the browser with support for macOS and Linux.
- 💬 **AI chat.** Built-in chat panel with multi-provider LLM support (OpenAI, Anthropic, Ollama, and OpenAI-compatible endpoints), model selector, tool calling, and streaming responses.
- 🔧 **Tool system.** Extensible tool framework enabling AI agents to interact with the local filesystem, run commands, search the web (Brave, DuckDuckGo, Exa, Tavily), and read URLs. Streaming JSON parser for improved tool-calling reliability.
- 📎 **File mentions.** Type `@` in the chat input to mention files with an inline suggestion popup, giving the AI context about your codebase.
- 🔄 **Queued messages.** Queue follow-up messages while the AI is responding — they'll be sent automatically when the current response completes.
- ✏️ **Output editing.** Review and edit AI-generated file changes before applying them.
- 📁 **File browser.** Web-based file explorer with directory navigation, file viewing, file icons by extension, and management capabilities.
- ⌨️ **Keyboard shortcuts.** Customizable keybinding system with a dedicated settings panel, including support for new-tab, quick-open, and other common actions.
- 📐 **Resizable sidebar.** Drag-to-resize sidebar with persistent width and smooth panel resize handles.
- 🔍 **Quick open.** Cmd+K modal with keyboard pill hints for fast file and command navigation.
- 🌐 **Proxy middleware.** Reverse-proxy system for forwarding local ports with automatic port detection and notification.
- 📁 **Workspace management.** Manage multiple project directories from a single instance.
- 📊 **Chat history.** Persistent chat list with automatic title generation, scrolling, and pagination.
- 🔐 **Authentication.** Username/password authentication with JWT-based session management.
- 🎨 **Admin settings.** Settings UI for managing AI connections and app configuration.
- 🐳 **Docker support.** Multi-stage Dockerfile and GitHub Actions workflow for building and publishing to GHCR.
- 📦 **PyPI packaging.** Hatchling-based build with frontend assets bundled into the wheel, published via trusted OIDC publishing.