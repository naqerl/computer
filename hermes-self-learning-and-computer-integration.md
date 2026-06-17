# Hermes Agent Self-Learning Loop — Analysis & Integration into Computer

## 1. The Self-Learning Loop in Hermes Agent

The self-learning loop is a **background meta-cognition system** that runs after every conversation turn. It consists of two complementary mechanisms:

### 1a. Turn-by-Turn Background Review (`agent/background_review.py`)

**Trigger**: After each turn completes in `turn_finalizer.py` (lines 376–401), if the turn produced a final response and wasn't interrupted, the agent checks two counters:

- `_should_review_memory`: fires every `_memory_nudge_interval` turns (default configurable). Set in `turn_context.py` (lines 212–219).
- `_should_review_skills`: fires every `_skill_nudge_interval` tool-calling iterations (set in `turn_finalizer.py` lines 376–381).

**Mechanism**: `AIAgent._spawn_background_review()` (`run_agent.py:1426`) creates a **daemon thread** that:

1. **Forks a new `AIAgent`** that inherits the parent's runtime (provider, model, base_url, api_key, cached system prompt) so it hits the same prefix cache and uses the same auth.
2. **Restricts the fork to only memory and skill-management tools** via a thread-local tool whitelist (`set_thread_tool_whitelist`).
3. **Replays the conversation snapshot** as `conversation_history` and sends a carefully crafted prompt asking it to evaluate the turn.
4. **The fork can call tools like `memory` (add/replace/remove) and `skill_manage` (create/patch/archive/consolidate)** to persist learnings directly to disk.
5. After the fork completes, `summarize_background_review_actions()` scans the fork's messages for successful tool actions and prints a compact summary like: `💾 Self-improvement review: Memory updated · Skill 'python-debugging' patched`

**Three review prompts exist** (`background_review.py:34–233`):
- **Memory review**: Focuses on user persona, preferences, desires, personal details.
- **Skill review**: Looks for corrections, technique improvements, workflow preferences, tool-usage patterns. Encourages class-level skills (not one-off task narratives).
- **Combined review**: Runs both simultaneously.

### 1b. Background Curator (`agent/curator.py`)

**Trigger**: Runs **inactivity-triggered** (not cron-based). When the agent is idle and the last curator run was longer than `interval_hours` (default 7 days), `maybe_run_curator()` spawns a forked AIAgent.

**Responsibilities**:
- **Auto-transition lifecycle states** for skills based on derived activity timestamps (stale → archive).
- **Consolidation**: Uses an LLM to merge overlapping agent-created skills into class-level umbrella skills.
- **Pinning**: Protected skills (bundled, hub-installed) are never touched; pinned skills bypass auto-transitions.
- **Never auto-deletes** — only archives (recoverable).

### 1c. The Data Flow

```
User message → Agent loop (tool calling) → Turn finalization
                                                  ↓
                                     Check nudge interval counters
                                                  ↓
                                     Spawn daemon thread:
                                       ┌────────────────────────┐
                                       │  Fork AIAgent          │
                                       │  - Inherits credentials│
                                       │  - Tool whitelist      │
                                       │  - Replay conversation │
                                       │  - Prompt: "Should any │
                                       │    memory/skill be     │
                                       │    saved or updated?"  │
                                       │                        │
                                       │  Fork calls:           │
                                       │  • memory(action=add,  │
                                       │    content=...)        │
                                       │  • skill_manage(action=│
                                       │    patch, name=...)    │
                                       └────────────────────────┘
                                                  ↓
                                     On completion:
                                     • Summarize actions
                                     • Print "💾 Self-improvement
                                       review: …"
```

### 1d. Memory System Integration

The memory system (`agent/memory_manager.py`) coordinates **external memory providers** (Honcho, mem0, SuperMemory, etc.) and **local file-based memory** (MEMORY.md, USER.md). The flow:

- **Pre-turn**: `prefetch_all()` queries external providers and injects relevant context into system prompt.
- **Post-turn**: `sync_all()` writes the turn summary to external providers.
- **Background review** can also invoke `memory` tool to write to the local MEMORY.md.

---

## 2. Integration into Computer

The Computer agent (`computer/cptr/utils/chat_task.py`) has a **simpler loop** than Hermes:

```
User message → Load history → Stream API calls → Execute tool calls → Repeat → Save & return
```

There is **no background review, no memory system, and no skill management** currently.

### 2a. Architecture Differences

| Aspect | Hermes Agent | Computer |
|--------|-------------|----------|
| Language | Python (synchronous threads) | Python (async/await) |
| Loop | `while` loop with manual iteration counting | `for _iteration in range(CHAT_MAX_ITERATIONS)` |
| Memory | `MemoryManager` with providers + local files | None (uses `MEMORY.md` / `AGENTS.md` instruction files) |
| Skills | `skill_manage` tool, curator, background review | `view_skill` tool, basic skill loading from `$skill` mentions |
| Background work | Daemon threads | No background tasks |
| Persistence | JSON log + SQLite + external providers | SQLAlchemy + SQLite |

### 2b. Integration Strategy

The self-learning loop can be ported to Computer as follows:

#### Phase 1: Memory System

**Add a `MemoryManager`** (patterned after `hermes-agent/agent/memory_manager.py`):

```
cptr/utils/memory/
  __init__.py
  manager.py         # MemoryManager orchestrator
  providers/
    file_provider.py  # Read/write MEMORY.md, USER.md in workspace
    (future: vector, external)
```

The memory provider for Computer should:

1. **Read `MEMORY.md` and `USER.md`** from the workspace root (these are already loaded by `_load_instruction_files`).
2. **Implement `add(content)`, `remove(content)`, `replace(old, new)`** operations that edit these files.
3. **Inject relevant memory into the system prompt** (already partially done via `_load_instruction_files` — just need to format it consistently).
4. **Add a `memory` tool** that the agent can call during conversation (not just in background review).

#### Phase 2: Skill Management

**Add `skill_manage` tool** (patterned after Hermes' `tools/skill_commands.py`):

- `skill_manage` supports `action=create|patch|edit|archive|delete|list|view`
- Already have `discover_skills()`, `load_skill()`, `build_catalog_xml()` — need to add write operations.
- Skill directory structure (already exists under workspace skills).

#### Phase 3: Background Review

**Add a post-turn hook in `chat_task.py`** after the tool-calling loop completes:

```python
# In run_chat_task(), after usage is received and the response
# is saved, spawn a background task (asyncio.create_task)
# that forks a review agent.

if _should_review_memory or _should_review_skills:
    asyncio.create_task(
        _run_background_review(
            messages=api_messages,
            workspace=workspace,
            connection=connection,
            model=model,
            review_memory=_should_review_memory,
            review_skills=_should_review_skills,
        )
    )
```

The background review function would:

1. **Build a minimal assistant agent** using the same provider/model/credentials.
2. **Replay the conversation** as context with a review prompt.
3. **Only allow `memory` and `skill_manage` tools** (strip all other tools from the tool list).
4. **Collect the fork's tool calls** and apply them to the local filesystem (MEMORY.md, skills).
5. **Optionally notify the user** via a Socket.IO event.

Since Computer uses **asyncio** (not threading), the review should run as an `asyncio.create_task` with a dedicated HTTP client session.

#### Phase 4: Curator (optional, longer-term)

Add an inactivity-triggered curator that:

1. Checks `last_curator_run` timestamp on startup and after idle periods.
2. Runs skill consolidation, archiving of stale skills.
3. Uses the auxiliary model config or the same model.

### 2c. Specific Code Changes

Here's where each change lands in the Computer codebase:

| File | Change |
|------|--------|
| `cptr/utils/memory/manager.py` | New: `MemoryManager` class |
| `cptr/utils/memory/providers/file_provider.py` | New: reads/writes MEMORY.md, USER.md |
| `cptr/utils/tools.py` | Add `memory` and `skill_manage` tool definitions |
| `cptr/utils/chat_task.py` | Add `_should_review_memory`/`_should_review_skills` counters. Add post-turn background review spawn. Track iteration/skill nudge intervals. |
| `cptr/utils/background_review.py` | New: `run_background_review()` async function |
| `cptr/models/chats.py` | Add `memory_nudge_interval`, `skill_nudge_interval` to chat params / config |

### 2d. Key Design Decisions for the Port

1. **No thread forking**: Computer uses asyncio, so the review runs as an `asyncio.create_task` with a **fresh HTTP client session** (no shared state issues).

2. **Simpler tool whitelist**: Instead of Hermes' thread-local whitelist, just **strip non-memory/skill tools** from the fork's tool list before calling the API.

3. **File-based memory first**: Start with `MEMORY.md` / `USER.md` file operations (the instructions system already supports them). Add vector/external providers later.

4. **Background review prompt reuse**: The prompts from `hermes-agent/agent/background_review.py` can be used almost verbatim.

5. **Nudge intervals**: Add to `Config` as `memory_nudge_interval` (default 5 turns) and `skill_nudge_interval` (default 10 tool-iterations).

---

## 3. What the Self-Learning Loop Gets You

| Capability | Before | After |
|-----------|--------|-------|
| User preference memory | Relies on user manually writing MEMORY.md | Agent automatically saves preferences after conversation |
| Skill improvement | User must manually edit skill files | Agent patches skills when it notices corrections |
| Cross-session learning | None (each session starts fresh) | MEMORY.md + skills persist learnings across sessions |
| Self-correction | Agent might repeat the same mistake | After being corrected once, the skill is updated so the mistake is not repeated |
| Skill library health | Skills accumulate without maintenance | Curator auto-archives stale skills, merges overlapping ones |
