"""Patcher node (docs/05-BACKEND-SPEC.md §6, §9). 0-2 model calls, 1-2 tool
calls. Tool-first for lint (0 model calls); model-authored with full
context otherwise, with one ast-retry on broken syntax. Guardrails:
diff_cap, no_main_write, and a defense-in-depth re-check of protected_file
(Analyst already checked it once before routing here).
"""

from __future__ import annotations

import ast
import asyncio
import difflib

from greenline.graph.budget import check_budget, guarded_node
from greenline.graph.state import GreenlineState
from greenline.guardrails.rails import diff_within_cap, is_main_or_master, protected_file
from greenline.llm.prompt_loader import load_prompt
from greenline.llm.schemas import PatchOutput

NODE = "patcher"
SYSTEM_PROMPT = load_prompt("patcher")
MAX_LOCAL_IMPORTS = 5


def _local_imports(source: str, package_prefix: str) -> list[str]:
    """Top-level import/from-import statements whose module starts with
    `package_prefix`, resolved to file paths (a.b.c -> a/b/c.py). Docs/02
    lesson 11: the Patcher needs neighbouring files, or it guesses names."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(a.name for a in node.names if a.name.startswith(package_prefix))
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(package_prefix):
            modules.append(node.module)

    seen: set[str] = set()
    paths: list[str] = []
    for module in modules:
        path = module.replace(".", "/") + ".py"
        if path not in seen:
            seen.add(path)
            paths.append(path)
    return paths[:MAX_LOCAL_IMPORTS]


def _restore_docstring_quotes(old_content: str, new_content: str) -> str:
    """The model often returns a file's one-line module docstring without its
    quotes (bare text instead of a triple-quoted line), which fails ast.parse on
    line 1. If the original's first line is a one-line docstring and the draft's
    first line is exactly its text, put the original line back. Narrow and
    deterministic; the result still goes through ast.parse, tests and the Critic."""
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    if not old_lines or not new_lines:
        return new_content
    first = old_lines[0].strip()
    for quote in ('"""', "'''"):
        if first.startswith(quote) and first.endswith(quote) and len(first) > 2 * len(quote):
            if new_lines[0].strip() == first[len(quote) : -len(quote)]:
                new_lines[0] = old_lines[0]
                return "\n".join(new_lines) + ("\n" if new_content.endswith("\n") else "")
    return new_content


async def _build_user_prompt(state: GreenlineState, target_content: str) -> str:
    sandbox = state["sandbox"]
    config = state["config"]
    attempts = state["patch_attempts"]

    parts = [
        f"Diagnosis: {state.get('verdict_cls', state.get('triage_cls'))}",
        f"Rationale: {state.get('rationale', '')}",
        f"\nTarget file ({config.patch_target}):\n{target_content}",
    ]

    if config.failing_test_nodeid:
        test_file = config.failing_test_nodeid.split("::")[0]
        try:
            test_content = await asyncio.to_thread(sandbox.read_file, config.branch, test_file)
            parts.append(f"\nFailing test file ({test_file}):\n{test_content}")
        except Exception:
            pass

    try:
        breaking_diff = await asyncio.to_thread(sandbox.breaking_diff, config.branch)
        if breaking_diff.strip():
            parts.append(f"\nThe breaking commit's diff:\n{breaking_diff}")
    except Exception:
        pass

    package_prefix = config.patch_target.split("/")[0]
    for path in _local_imports(target_content, package_prefix):
        if path == config.patch_target:
            continue
        try:
            content = await asyncio.to_thread(sandbox.read_file, config.branch, path)
            parts.append(f"\nLocal module it imports ({path}):\n{content}")
        except Exception:
            continue

    if attempts:
        last_attempt = attempts[-1]
        last_vote = state["critic_votes"][-1] if state["critic_votes"] else None
        parts.append(f"\nYour previous attempt's diff:\n{last_attempt['diff']}")
        if last_vote:
            reason = last_vote.get("rationale", "(no reason given)")
            parts.append(f"\nThe Critic rejected it because: {reason}")

    return "\n".join(parts)


def _unified_diff(old_content: str, new_content: str, target: str) -> str:
    return "".join(
        difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{target}",
            tofile=f"b/{target}",
        )
    )


async def patcher_node(state: GreenlineState) -> GreenlineState:
    emitter = state["emitter"]
    llm = state["llm"]
    sandbox = state["sandbox"]
    config = state["config"]
    cls = state["verdict_cls"]
    target = config.patch_target
    attempt_n = len(state["patch_attempts"]) + 1

    async with guarded_node(state, NODE):
        check_budget(state)
        old_content = await asyncio.to_thread(sandbox.read_file, config.branch, target)

        if cls == "lint":
            emitter.narrate(NODE, f"Attempt {attempt_n}: running ruff --fix (tool-first, no model call)")
            fix_result = await asyncio.to_thread(sandbox.ruff_fix, config.branch, target)
            emitter.record_tool_call()
            new_content = fix_result.stdout
            source = "tool"
        else:
            emitter.narrate(NODE, f"Attempt {attempt_n}: drafting a minimal fix")
            user_prompt = await _build_user_prompt(state, old_content)
            result = await llm.complete(SYSTEM_PROMPT, user_prompt, PatchOutput, 0.1)
            emitter.record_model_call()
            new_content = result.new_content
            source = "model"

            syntax_error: SyntaxError | None = None
            try:
                ast.parse(new_content)
            except SyntaxError as exc:
                syntax_error = exc
                repaired = _restore_docstring_quotes(old_content, new_content)
                if repaired != new_content:
                    try:
                        ast.parse(repaired)
                    except SyntaxError:
                        pass
                    else:
                        emitter.log(NODE, "info", "restored the module docstring quotes the draft dropped")
                        new_content = repaired
                        syntax_error = None
            if syntax_error is not None:
                check_budget(state)
                emitter.log(NODE, "warn", f"patch failed ast.parse ({syntax_error}); one corrective retry")
                corrective_prompt = (
                    f"{user_prompt}\n\nYour previous response did not parse as valid Python: "
                    f"{syntax_error}. Return the full corrected file content again, as valid Python."
                )
                result = await llm.complete(SYSTEM_PROMPT, corrective_prompt, PatchOutput, 0.1)
                emitter.record_model_call()
                new_content = result.new_content
                try:
                    ast.parse(new_content)
                except SyntaxError:
                    emitter.log(NODE, "warn", "corrective retry also failed ast.parse; treating as no change")
                    new_content = old_content  # empty diff below -> honest escalation

        diff = _unified_diff(old_content, new_content, target)

        if not diff.strip():
            emitter.log(NODE, "warn", "no change proposed -- escalating")
            state["patch_attempts"].append(
                {"n": attempt_n, "file": target, "diff": "", "source": source, "result": "vetoed"}
            )
            emitter.emit("patch.attempt", n=attempt_n, file=target, diff="", source=source, result="vetoed")
            return state

        within_cap = diff_within_cap(diff)
        emitter.emit(
            "guardrail",
            rail="diff_cap",
            fired=not within_cap,
            note=(
                f"diff exceeds the {80}-line cap"
                if not within_cap
                else "diff is within the 80-line cap"
            ),
        )

        fix_branch = f"fix/{state['case_id']}"
        main_write = is_main_or_master(fix_branch)
        emitter.emit("guardrail", rail="no_main_write", fired=main_write, note=f"target branch {fix_branch!r}")

        still_protected = protected_file([target])
        emitter.emit(
            "guardrail",
            rail="protected_file",
            fired=still_protected,
            note=f"{target} re-checked before applying the patch",
        )

        if not within_cap or main_write or still_protected:
            state["patch_attempts"].append(
                {"n": attempt_n, "file": target, "diff": diff, "source": source, "result": "vetoed"}
            )
            emitter.emit("patch.attempt", n=attempt_n, file=target, diff=diff, source=source, result="vetoed")
            return state

        check_budget(state)
        verify = await asyncio.to_thread(sandbox.run_patched, config.branch, target, new_content)
        emitter.record_tool_call()
        result_label = "green" if verify["tests_passed"] and verify["lint_passed"] else "red"
        state["patch_attempts"].append(
            {
                "n": attempt_n,
                "file": target,
                "diff": diff,
                "source": source,
                "result": result_label,
                "new_content": new_content,  # in-memory only: lets the Reporter open a real PR (B18)
                "tests_passed": verify["tests_passed"],
                "lint_passed": verify["lint_passed"],
            }
        )
        emitter.emit("patch.attempt", n=attempt_n, file=target, diff=diff, source=source, result=result_label)

    return state
