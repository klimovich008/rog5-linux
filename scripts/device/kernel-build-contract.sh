#!/bin/sh

# Source this file from a kernel builder. File descriptor 9 remains locked
# after rog5_kernel_prepare_output succeeds. Build children inherit it, so the
# kernel releases the lock only after the last process that can still write the
# output exits, including after an uncatchable termination of the parent.

rog5_kernel_fail() {
	echo "FAIL $*" >&2
	exit 1
}

rog5_kernel_cache_identity() {
	case ${KBUILD_CCACHE:-0} in
		0)
			printf '%s\n' 'compiler_cache=disabled'
			;;
		1)
			_rog5_ccache_path=$(command -v ccache) ||
				rog5_kernel_fail 'KBUILD_CCACHE=1 but ccache is unavailable'
			[ -f "$_rog5_ccache_path" ] && [ -x "$_rog5_ccache_path" ] ||
				rog5_kernel_fail 'ccache is not an executable regular file'
			printf '%s\n' \
				'compiler_cache=ccache' \
				"ccache_sha256=$(sha256sum "$_rog5_ccache_path" | cut -d ' ' -f 1)"
			;;
		*)
			rog5_kernel_fail 'KBUILD_CCACHE must be 0 or 1'
			;;
	esac
}

rog5_kernel_toolchain_identity() {
	[ "$#" -gt 0 ] ||
		rog5_kernel_fail 'toolchain identity requires at least one command'
	for _rog5_tool do
		case $_rog5_tool in
			*[!A-Za-z0-9_.+-]*|'')
				rog5_kernel_fail "invalid toolchain command name: $_rog5_tool"
				;;
		esac
		_rog5_tool_path=$(command -v "$_rog5_tool") ||
			rog5_kernel_fail "missing kernel build command: $_rog5_tool"
		[ -f "$_rog5_tool_path" ] && [ -x "$_rog5_tool_path" ] ||
			rog5_kernel_fail \
				"kernel build command is not executable: $_rog5_tool"
		printf 'tool.%s.sha256=%s\n' "$_rog5_tool" \
			"$(sha256sum "$_rog5_tool_path" | cut -d ' ' -f 1)"
	done
}

rog5_kernel_prepare_output() {
	_rog5_output_dir=$1
	_rog5_expected_state=$2
	_rog5_state_name=.rog5-kbuild-inputs-v1
	_rog5_lock_name=.rog5-kbuild.lock

	case ${INCREMENTAL_BUILD:-0} in
		0|1) ;;
		*) rog5_kernel_fail 'INCREMENTAL_BUILD must be 0 or 1' ;;
	esac
	[ -n "$_rog5_expected_state" ] ||
		rog5_kernel_fail 'kernel build state must not be empty'
	case $_rog5_output_dir in
		''|/|.|..)
			rog5_kernel_fail 'unsafe kernel output directory'
			;;
	esac
	[ ! -L "$_rog5_output_dir" ] ||
		rog5_kernel_fail 'kernel output directory must not be a symlink'
	mkdir -p -- "$_rog5_output_dir"
	[ -d "$_rog5_output_dir" ] ||
		rog5_kernel_fail 'kernel output path is not a directory'

	command -v flock >/dev/null ||
		rog5_kernel_fail 'missing kernel build command: flock'
	_rog5_lock_path=$_rog5_output_dir/$_rog5_lock_name
	if [ ! -e "$_rog5_lock_path" ]; then
		(
			umask 077
			set -C
			: >"$_rog5_lock_path"
		) 2>/dev/null ||
			rog5_kernel_fail 'cannot create kernel output lock file'
	fi
	[ -f "$_rog5_lock_path" ] && [ ! -L "$_rog5_lock_path" ] ||
		rog5_kernel_fail 'kernel output lock is not a regular file'
	[ "$(stat -c '%u' "$_rog5_lock_path")" = "$(id -u)" ] &&
		[ "$(stat -c '%a' "$_rog5_lock_path")" = 600 ] ||
		rog5_kernel_fail 'kernel output lock owner or mode is unsafe'
	exec 9<>"$_rog5_lock_path"
	flock -n 9 ||
		rog5_kernel_fail 'another kernel builder owns this output directory'

	_rog5_state_path=$_rog5_output_dir/$_rog5_state_name
	_rog5_existing=$(find "$_rog5_output_dir" -mindepth 1 -maxdepth 1 \
		! -name "$_rog5_lock_name" -print -quit)
	if [ -z "$_rog5_existing" ]; then
		_rog5_state_tmp=$_rog5_output_dir/$_rog5_state_name.tmp.$$
		(
			umask 077
			set -C
			printf '%s\n' "$_rog5_expected_state" >"$_rog5_state_tmp"
		) || rog5_kernel_fail 'cannot create kernel build state'
		if ! ln -- "$_rog5_state_tmp" "$_rog5_state_path" 2>/dev/null; then
			rm -f -- "$_rog5_state_tmp"
			rog5_kernel_fail 'kernel build state appeared concurrently'
		fi
		rm -f -- "$_rog5_state_tmp"
		return
	fi

	[ "${INCREMENTAL_BUILD:-0}" = 1 ] ||
		rog5_kernel_fail \
			'output directory is nonempty; use a fresh directory or explicitly set INCREMENTAL_BUILD=1'
	[ -f "$_rog5_state_path" ] && [ ! -L "$_rog5_state_path" ] ||
		rog5_kernel_fail 'incremental output lacks a regular build-state file'
	[ "$(stat -c '%u' "$_rog5_state_path")" = "$(id -u)" ] ||
		rog5_kernel_fail 'incremental build-state owner is not the current user'
	[ "$(stat -c '%a' "$_rog5_state_path")" = 600 ] ||
		rog5_kernel_fail 'incremental build-state mode is not 0600'
	_rog5_actual_state=$(cat -- "$_rog5_state_path")
	[ "$_rog5_actual_state" = "$_rog5_expected_state" ] ||
		rog5_kernel_fail 'incremental output does not match current build inputs'
}

rog5_kernel_make() {
	case ${KBUILD_CCACHE:-0} in
		0)
			command make "$@"
			;;
		1)
			command -v ccache >/dev/null ||
				rog5_kernel_fail 'ccache disappeared after build preparation'
			CCACHE_COMPILERCHECK=content \
			CCACHE_NODEPEND=true \
			CCACHE_SLOPPINESS='' \
				command make "$@" \
				'CC=ccache clang' \
				'HOSTCC=ccache clang' \
				'HOSTCXX=ccache clang++'
			;;
		*)
			rog5_kernel_fail 'KBUILD_CCACHE must be 0 or 1'
			;;
	esac
}

rog5_kernel_cache_stats() {
	if [ "${KBUILD_CCACHE:-0}" = 1 ]; then
		printf '%s\n' 'INFO ccache statistics'
		ccache --show-stats
	fi
}
