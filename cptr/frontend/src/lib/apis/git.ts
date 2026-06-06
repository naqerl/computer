/**
 * Git API: status, log, diff, stage, commit, push, pull, branches.
 */
import { fetchJSON, jsonBody } from '$lib/apis';

export const getGitStatus = (root: string) =>
	fetchJSON(`/api/git/status?root=${encodeURIComponent(root)}`);

export const getGitLog = (root: string, limit = 30) =>
	fetchJSON(`/api/git/log?root=${encodeURIComponent(root)}&limit=${limit}`);

export const getGitDiff = (params: string) =>
	fetchJSON(`/api/git/diff?${params}`);

export const getGitShow = (root: string, ref: string) =>
	fetchJSON(`/api/git/show?root=${encodeURIComponent(root)}&ref=${encodeURIComponent(ref)}`);

export const getGitBranches = (root: string) =>
	fetchJSON(`/api/git/branches?root=${encodeURIComponent(root)}`);

export const stageFiles = (root: string, files: string[]) =>
	fetchJSON('/api/git/stage', jsonBody({ root, files }));

export const unstageFiles = (root: string, files: string[]) =>
	fetchJSON('/api/git/unstage', jsonBody({ root, files }));

export const discardChanges = (root: string, files: string[]) =>
	fetchJSON('/api/git/discard', jsonBody({ root, files }));

export const gitCommit = (root: string, message: string) =>
	fetchJSON('/api/git/commit', jsonBody({ root, message }));

export const gitPull = (root: string) =>
	fetchJSON('/api/git/pull', jsonBody({ root }));

export const gitPush = (root: string) =>
	fetchJSON('/api/git/push', jsonBody({ root }));

export const createGitBranch = (root: string, name: string) =>
	fetchJSON('/api/git/branch', jsonBody({ root, name }));

export const checkoutBranch = (root: string, branch: string) =>
	fetchJSON('/api/git/checkout', jsonBody({ root, branch }));

export const stageAll = (root: string) =>
	fetchJSON('/api/git/stage', jsonBody({ root, files: ['.'] }));

export const unstageAll = (root: string) =>
	fetchJSON('/api/git/unstage', jsonBody({ root, files: ['.'] }));
