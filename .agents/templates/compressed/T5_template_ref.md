# T5: Template Reference (Externalized Format)

**Savings:** 90% (embed → reference)

## Format

```
<step:N STEP_NAME>
template: "path/to/template.md"
required_sections: [1,2,3,4,5]
optional_sections: [6,7,8]
output: "path/to/output.md"
</step>
```

## Rules
- Never inline large templates — always reference external file
- required_sections: must be filled
- optional_sections: skip for small projects
- output: where the filled template is saved
