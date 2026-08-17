---
applyTo: "**/*"
# This file is ONLY for the code review agent.
excludeAgent: ["coding-agent"]
---

# Copilot Instructions - Pull Request Review

**Purpose:** Guide Copilot to review pull requests consistently and request changes when rules are not met.

---

## How Copilot Should Operate

- **Examine each file individually:** Review every file changed in the pull request thoroughly.
- **Leave specific comments:** Comment on individual changes with line references. Focus on the diff plus a small surrounding context (nearby functions/classes/files).
- **Analyze with full codebase context:** Use semantic understanding of the entire codebase to identify if changes break existing functionality, dependencies, or contracts.
- **Suggest simplifications:** If changes can be simplified without losing functionality, recommend cleaner approaches (reduce complexity, remove duplication, use existing utilities).
- **Validate control flow:** Test the logic mentally with 2-3 representative inputs:
  - **Normal case:** Typical valid input that exercises the happy path
  - **Edge case:** Boundary conditions (empty, null, zero, max values, special characters)
  - **Error case:** Invalid input that should trigger error handling
- **Propose test cases:** If test coverage is missing for the changed logic, provide exact test cases in review comments with:
  - Input values
  - Expected output/behavior
  - Specific assertions to verify
- **Provide constructive feedback:** Be specific and actionable. Explain the "why" behind recommendations. Acknowledge good patterns when you see them. Ask clarifying questions when code intent is unclear. Suggest changes to improve readability.
- **Prioritize:** Security vulnerabilities and performance issues that could impact users come first. Post clear review comments with:
  - What changed (file/line)
  - Why it matters (risk/impact)
  - What to do (specific fix or example)
- **Final summary:** After reviewing all files, post a summary comment indicating "Ready," "Needs changes," or other status.

---

## Mandatory Checks

### 1. Tests & Coverage

For code changes, verify unit/integration tests are added or updated in `/src/test/*` (or repo-specific test paths). Look for meaningful assertions and edge cases (null/empty inputs, error paths).

- If logic changes without corresponding tests, request changes with specific test cases to add.

### 2. Build Scripts & CI

- **No print statements:** Flag leftover `print()` statements in production code. Use `logger` from `utils.log_helper` instead.
- **Commented-out code:** Remove commented debug code (e.g., `print()`) unless accompanied by explanation.
- **Exception handling:** Ensure proper exception handling with specific exception types, not bare `except:` without logging.

### 3. Function Design

- **Use early returns:** Use early returns for error conditions (avoid deep nesting).
- **Focused functions:** Functions should be focused and appropriately sized (single responsibility).
- **Clear naming:** Use clear, descriptive variable names (no single-letter vars except loop counters).
- **Input validation:** Proper input validation and sanitization at function entry points.

### 4. Configuration File Changes

**Critical config files:** Changes to `config.yaml` require:
- Validation that YAML syntax is correct
- Backward compatibility verification
- Description of what mappings changed and why
- Verification that dependent projects are not broken

### 5. Security & Secrets

- **Parameterized queries:** Flag string-built SQL or command injection risks. Prefer parameterized queries.
- **Input validation:** Verify proper sanitization of user inputs, file paths, and external data.
- **Logging restrictions:** No logging of PII (personal identifiable information):
  - No logging of tokens, passwords, or credentials
  - No logging of full database connection strings

---

## Review Comment Templates

### Tests Missing

> **#file:#line:** Changes in file alter logic but test coverage was not updated. Please add/modify tests covering success, failure, and edge cases (null/empty).
>
> **Suggested scenarios:**
> - Normal case: [describe typical input]
> - Edge case: [describe boundary conditions]
> - Error case: [describe invalid input]

### Configuration Changes

> **#file:#line:** `config.yaml` modified. Please confirm this change is intentional and provide:
> - Brief description of what changed
> - Impact assessment (which workflows/projects affected)
> - Validation that syntax is correct

### Potential Secret or Sensitive Value

> **#file:#line:** Potential secret or sensitive value found. Replace with env var/secret manager reference and remove/redact the value. Also avoid logging this field.

### Logging Issue

> **#file:#line:** Logging statement may contain sensitive data (PII/credentials). Please verify no sensitive information is logged or sanitize before logging.

### Concurrency Issue

> **#file:#line:** Potential thread safety issue with shared state access. Consider using locks, thread-local storage, or immutable data structures.
>
> **Example:** Use `threading.Lock()` or pass copies instead of shared references.

### Simplification Suggestion

> **#file:#line:** This implementation can be simplified.
>
> **Suggested approach:** [provide simpler example]
>
> **Benefits:** Improved readability, reduced maintenance, leverages tested code.

### Breaking Change Detected

> **#file:#line:** This change may break existing functionality.
>
> **Impact:** [describe what breaks and where]
>
> **Files affected:** [list files/modules that depend on this]
>
> **Recommendation:** [preserve backward compatibility, add migration path, or update all callers]

### Performance Note - N+1 Query Problem

> **#file:#line:** Detected N+1 query pattern - database query executed inside loop. This will execute [N] queries instead of 1.
>
> **Consider:**
> - Fetch all data upfront with a single query using `WHERE id IN (...)`
> - Use joins or eager loading to fetch related data
>
> **Impact:** Severe performance degradation as data grows.

### Memory Leak Risk

> **#file:#line:** Resource not properly cleaned up. [File/connection/resource] may leak if exception occurs before cleanup. Use context manager (`with` statement) or ensure cleanup in `finally` block.
>
> **Example:** `with open(file) as f:...` or add `finally: connection.close()`

### Early Return Suggestion

> **#file:#line:** Consider using early return for error condition. Instead of nesting entire function body in if/else, return early on error. This improves readability by reducing indentation depth.
>
> **Example:** `if not valid: return None # then continue with main logic`

### Clarification Needed

> **#file:#line:** The intent of this change is unclear. Could you explain what problem this solves or why this approach was chosen? This will help ensure the implementation aligns with the intended goal.

### Documentation Issue

> **#file:** Public behavior changed. Please update README/docs and add a brief changelog entry describing the impact and migration steps.

### Test Coverage Missing

> **#file:#line:** Logic changed but no corresponding test coverage found. Please add tests covering these cases:
>
> **Normal case:**
> ```python
> # Test with typical valid input
> result = function_name(valid_input)
> assert result == expected_output
> ```
>
> **Edge case:**
> ```python
> # Test with boundary conditions
> result = function_name(empty_input)  # or None, 0, [], etc.
> assert result == expected_edge_behavior
> ```
>
> **Error case:**
> ```python
> # Test error handling
> with pytest.raises(ExpectedError):
>     function_name(invalid_input)
> ```

---

## Summary

This guide ensures consistent, thorough code reviews that catch:
- Missing test coverage
- Configuration and security issues
- Performance problems (N+1 queries, memory leaks)
- Code quality (simplifications, early returns, proper naming)
- Breaking changes and documentation gaps