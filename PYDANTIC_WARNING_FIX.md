# Pydantic Warning Fix: Field Name Shadowing 🔧

## Issue Fixed ✅

**Warning was:**
```
/Users/max/code/backend-sdk/.venv/lib/python3.12/site-packages/pydantic/_internal/_fields.py:198: UserWarning: Field name "json" in "OutputOptions" shadows an attribute in parent "BaseModel"
```

## Root Cause 🔍

Pydantic's `BaseModel` has a built-in `json()` method for serialization. Our `OutputOptions` class was defining a `json` field, which shadowed this method.

```python
# PROBLEMATIC CODE:
class OutputOptions(BaseModel):
    json: bool = False        # ❌ Shadows BaseModel.json() method
    yaml: bool = False
    porcelain: bool = False
```

## Solution Applied 🛠️

Renamed the conflicting fields to be more descriptive:

```python
# FIXED CODE:
class OutputOptions(BaseModel):
    json_output: bool = False    # ✅ Clear and non-conflicting
    yaml_output: bool = False    # ✅ Consistent naming
    porcelain: bool = False      # ✅ No conflict
```

## Files Updated 📝

1. **`src/sup/config/settings.py`** - Updated `OutputOptions` field names
2. **`src/sup/decorators/output.py`** - Updated decorator parameter mapping
3. **`src/sup/commands/dataset_dry.py`** - Updated field references
4. **`src/sup/commands/chart_dry.py`** - Updated field references

## Before/After Comparison 🔄

### Before:
```python
@with_output_options
def my_command(output: OutputOptions):
    if output.json:        # ❌ Warning: shadows BaseModel.json()
        print_json(data)
    elif output.yaml:      # Could potentially conflict too
        print_yaml(data)
```

### After:
```python
@with_output_options
def my_command(output: OutputOptions):
    if output.json_output:    # ✅ Clear, no shadowing
        print_json(data)
    elif output.yaml_output:  # ✅ Consistent naming
        print_yaml(data)
```

## Benefits ✨

1. **✅ No more Pydantic warnings** - Clean console output
2. **✅ More descriptive field names** - `json_output` vs `json` is clearer
3. **✅ Future-proof** - Avoids potential conflicts with BaseModel methods
4. **✅ Consistent naming** - All output format fields follow same pattern

## CLI Usage Unchanged 🎯

The actual CLI parameters remain the same for users:

```bash
sup chart list --json        # Still works the same
sup dataset list --yaml      # Still works the same
sup workspace list --porcelain  # Still works the same
```

Only the internal field names changed, not the user interface.

## Validation ✅

```python
# Test shows fix works:
from sup.config.settings import OutputOptions
opts = OutputOptions(json_output=True, yaml_output=False, porcelain=False)
print(f'✅ OutputOptions works: format={opts.format}')
# Output: ✅ OutputOptions works: format=json
```

## Lesson Learned 📚

When using Pydantic models, be careful of field names that might conflict with BaseModel's built-in methods:
- `json()` - serialization method
- `dict()` - dictionary conversion method
- `copy()` - model copying method
- etc.

Use descriptive field names like `json_output`, `data_dict`, `copy_mode` to avoid conflicts.

## Status: Fixed! 🎉

The warning is now eliminated and the code is cleaner with more descriptive field names. The DRY architecture continues to work perfectly with proper Pydantic hygiene.
