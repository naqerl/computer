/**
 * Centralized git status store.
 *
 * Single source of truth – replaces scattered getGitStatus() calls
 * across layout, GitBar, GitView, and FileEditor.
 *
 * Components read from this store; mutations (commit, stage, etc.)
 * call refresh() to update everyone at once.
 */

import { fetchJSON } from '$lib/apis';

export interface GitFile {
	path: string;
	status: string;
	staged: boolean;
}

export interface GitStatus {
	is_repo: boolean;
	branch: string;
	upstream?: string;
	remote_url?: string;
	ahead: number;
	behind: number;
	files: GitFile[];
}

let _status = $state<GitStatus | null>(null);
let _loading = $state(false);
let _currentRoot = '';
let _fetchPromise: Promise<void> | null = null;

async function _doFetch(root: string) {
	if (!root) {
		_status = null;
		return;
	}
	_loading = true;
	try {
		const data = (await fetchJSON(
			`/api/git/status?root=${encodeURIComponent(root)}`
		)) as GitStatus;
		// Only apply if root hasn't changed while we were fetching
		if (root === _currentRoot) {
			_status = data;
		}
	} catch {
		if (root === _currentRoot) {
			_status = null;
		}
	} finally {
		_loading = false;
		_fetchPromise = null;
	}
}

export const gitStatusStore = {
	get status() {
		return _status;
	},
	get loading() {
		return _loading;
	},
	get isRepo() {
		return _status?.is_repo ?? false;
	},

	/** Set the workspace root and fetch status. */
	setRoot(root: string) {
		if (root === _currentRoot) return;
		_currentRoot = root;
		_status = null;
		this.refresh();
	},

	/** Clear all state (no workspace). */
	clear() {
		_currentRoot = '';
		_status = null;
		_loading = false;
		_fetchPromise = null;
	},

	/**
	 * Refresh git status from the server.
	 * Concurrent calls are coalesced into a single fetch.
	 */
	refresh() {
		if (!_currentRoot) return;
		if (!_fetchPromise) {
			_fetchPromise = _doFetch(_currentRoot);
		}
		return _fetchPromise;
	}
};
