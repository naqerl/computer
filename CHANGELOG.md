# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.1] - 2026-06-05

### Added

- 🚀 **Initial release.** First public version of cptr: your computer, from anywhere. Code, manage, and control your machine from the web.
- 🖥️ **Terminal emulator.** Full PTY-backed terminal accessible from the browser with support for macOS and Linux.
- 💬 **AI chat interface.** Built-in chat panel with multi-provider LLM support (OpenAI, Anthropic, Ollama, and OpenAI-compatible endpoints), tool calling, and streaming responses.
- 🔧 **Tool system.** Extensible tool framework enabling AI agents to interact with the local filesystem, run commands, search the web, and read URLs.
- 📁 **File browser.** Web-based file explorer with directory navigation, file viewing, and management capabilities.
- 🔐 **Authentication.** Username/password authentication with JWT-based session management.
- 🐳 **Docker support.** Multi-stage Dockerfile and GitHub Actions workflow for building and publishing to GHCR.
- 📦 **PyPI packaging.** Hatchling-based build with frontend assets bundled into the wheel, published via trusted OIDC publishing.