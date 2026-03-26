# Verification Rules

Verify at least these points:

1. all required stages are present
2. no major invented stage appears
3. backend matches the figure need
4. labels are not overloaded
5. the result still reflects the main scientific story

Suggested status payload:

```yaml
status: pass|needs-fix
backend_ok: true|false
structure_ok: true|false
label_density_ok: true|false
issues:
  - ...
retry_strategy:
  - ...
```
