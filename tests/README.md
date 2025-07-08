# GW2 WvW Leaderboards Test Suite

Automated tests to prevent regressions during development.

## Test Suites

### Quick Regression Tests (`test_quick_regression.py`)
**Runtime: ~30 seconds**

Fast tests that validate core functionality without generating web UI:
- ✅ Database schema integrity
- ✅ APM data exists in database
- ✅ Date filtering logic
- ✅ Profession metrics configuration
- ✅ Module imports work correctly
- ✅ Sample APM calculations
- ✅ Guild data availability
- ✅ Recent data exists

### Comprehensive Functionality Tests (`test_web_ui_functionality.py`)
**Runtime: ~2-3 minutes**

Full end-to-end tests that generate a test web UI and validate output:
- 🔍 **Date filtering differences**: Validates that 30d/60d/all show different data
  - Individual metrics (DPS, Healing, Stability)
  - Profession leaderboards (Firebrand, Chronomancer, Druid)
  - High scores across time periods
- 🎯 **APM calculation accuracy**: Ensures APM shows actual values, not 0.0/0.0
- 🏛️ **Guild filtering functionality**: Validates guild member data structure
- 📈 **Latest change (rating deltas)**: Checks rating delta functionality
- 🔄 **Modal data structure**: Ensures player modal has required data fields
- 🏗️ **Data structure integrity**: Validates overall JSON structure

## Usage

### Test Runner (Recommended)
```bash
# Quick regression tests (30 seconds)
python run_tests.py quick

# Full functionality tests (2-3 minutes)  
python run_tests.py full

# All tests
python run_tests.py all

# Environment check
python run_tests.py --check
```

### Direct Execution
```bash
# Quick tests only
python tests/test_quick_regression.py

# Full tests only
python tests/test_web_ui_functionality.py
```

## Integration with Development Workflow

### Before Committing Changes
```bash
# Quick validation (recommended)
python run_tests.py quick
```

### After Major Changes
```bash
# Full validation
python run_tests.py full
```

### Continuous Integration
```bash
# Complete test suite
python run_tests.py all
```

## Test Categories

### Date Filtering Tests
- **Purpose**: Prevent regression of the critical date filtering fixes from July 2025
- **Validates**: 30d/60d/90d/overall filters show different data
- **Covers**: Individual metrics, profession leaderboards, high scores

### APM Calculation Tests  
- **Purpose**: Prevent regression of APM calculation fix
- **Validates**: APM data shows actual values instead of 0.0/0.0
- **Covers**: Database queries, date filtering, profession leaderboards

### UI Feature Tests
- **Purpose**: Ensure modal, guild filter, and latest change features work
- **Validates**: Required data structures and fields exist
- **Covers**: Player modals, guild membership, rating deltas

### Data Integrity Tests
- **Purpose**: Validate overall system health
- **Validates**: Database schema, imports, data structure
- **Covers**: Core functionality and system stability

## Adding New Tests

### For New Features
1. Add tests to `test_web_ui_functionality.py` for UI features
2. Add tests to `test_quick_regression.py` for core logic
3. Update this README with test descriptions

### Test Naming Convention
- `test_<feature>_<aspect>()` - e.g., `test_apm_calculation_accuracy()`
- Use descriptive names that explain what's being tested
- Group related tests in the same test class

### Test Data Validation
- Use `self.subTest()` for testing multiple similar items (e.g., metrics, professions)
- Include helpful assertion messages that explain expected vs actual
- Test both positive cases (data exists) and edge cases (empty data)

## Troubleshooting

### Common Issues

**"Database not found"**
- Run tests from project root directory
- Ensure `gw2_comprehensive.db` exists

**"No APM data found"**
- Check database has recent performance data
- Verify APM parsing is working correctly

**"Module import errors"**
- Ensure all dependencies are installed
- Check Python path includes project root

**Test timeouts**
- Full tests can take 2-3 minutes due to web UI generation
- Quick tests should complete in under 30 seconds

### Debug Mode
```bash
python run_tests.py full --verbose
```

## Test Output Examples

### Success
```
✅ All 12 tests passed!
💡 Tip: Run 'python run_tests.py full' for comprehensive validation
```

### Failure
```
❌ 1 failures, 0 errors out of 8 tests
  - test_apm_data_not_zero: No non-zero APM values found in 30d profession leaderboards
🔧 Check the output above for specific failures
```