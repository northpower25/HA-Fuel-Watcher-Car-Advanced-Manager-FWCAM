# Contributing to haFWCMA

Thank you for your interest in contributing to the Fuel Watcher Car Advanced Manager integration!

## Ways to Contribute

- **Report bugs** via GitHub Issues
- **Suggest features** and enhancements
- **Submit pull requests** with bug fixes or new features
- **Improve documentation**
- **Help other users** in discussions
- **Translate** to other languages

## Getting Started

### Prerequisites

- Python 3.11 or later
- Home Assistant development environment
- Git
- Basic understanding of Python and Home Assistant integrations

### Development Setup

1. Fork the repository on GitHub

2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM.git
   cd HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM
   ```

3. Create a development branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. Set up development environment:
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements_dev.txt
   ```

## Code Standards

### Python Style

- Follow [PEP 8](https://pep8.org/)
- Use [Black](https://github.com/psf/black) for formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Use type hints for all function signatures
- Write docstrings for all public functions and classes

### Example Code Style

```python
"""Module docstring describing purpose."""
from __future__ import annotations

import logging
from typing import Any, Optional

_LOGGER = logging.getLogger(__name__)


class MyClass:
    """Class docstring.
    
    Attributes:
        attribute: Description of attribute
    """

    def __init__(self, param: str) -> None:
        """Initialize the class.
        
        Args:
            param: Description of parameter
        """
        self.attribute = param

    async def my_method(self, value: int) -> Optional[str]:
        """Method docstring.
        
        Args:
            value: Description of value
            
        Returns:
            Description of return value
            
        Raises:
            ValueError: When something goes wrong
        """
        if value < 0:
            raise ValueError("Value must be positive")
        return str(value)
```

### Commit Messages

Use clear, descriptive commit messages:

```
Add support for multiple vehicles

- Implement multi-vehicle coordinator
- Update config flow for vehicle selection
- Add tests for vehicle management
```

Format:
- First line: Brief summary (50 chars or less)
- Blank line
- Detailed description if needed
- Use present tense ("Add feature" not "Added feature")

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components/hafwcma

# Run specific test file
pytest tests/test_sensor.py
```

### Writing Tests

- Write tests for all new features
- Maintain or improve code coverage
- Use descriptive test names
- Follow existing test patterns

Example test:

```python
"""Tests for hafwcma sensors."""
import pytest
from homeassistant.core import HomeAssistant

async def test_fuel_price_sensor(hass: HomeAssistant):
    """Test fuel price sensor creation."""
    # Arrange
    config_entry = MockConfigEntry(domain=DOMAIN, data=TEST_CONFIG)
    
    # Act
    await async_setup_entry(hass, config_entry)
    await hass.async_block_till_done()
    
    # Assert
    state = hass.states.get("sensor.my_car_fuel_price")
    assert state is not None
    assert state.state == "1.649"
```

## Pull Request Process

### Before Submitting

1. **Test your changes**
   - All tests pass
   - No new warnings
   - Code coverage maintained

2. **Update documentation**
   - Update README if needed
   - Update relevant docs
   - Add docstrings

3. **Follow style guidelines**
   - Run Black: `black custom_components/hafwcma`
   - Run isort: `isort custom_components/hafwcma`
   - Check with pylint: `pylint custom_components/hafwcma`

### Submitting PR

1. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Create Pull Request on GitHub

3. Fill out the PR template:
   - Description of changes
   - Related issues
   - Testing performed
   - Screenshots (if UI changes)

4. Wait for review

### PR Review Process

- Maintainer will review your PR
- Address any requested changes
- Once approved, PR will be merged
- Your contribution will be credited

## Adding New Features

### Proposing Features

1. Check [TODO.md](../TODO.md) and existing issues
2. Create a feature request issue
3. Discuss design and implementation
4. Get approval before starting work

### Feature Development Checklist

- [ ] Feature implemented
- [ ] Tests added
- [ ] Documentation updated
- [ ] Translations updated (if needed)
- [ ] CHANGE-HISTORY.md updated
- [ ] No breaking changes (or documented)
- [ ] Backwards compatible

## Adding Translations

1. Copy `translations/en.json` to `translations/YOUR_LANG.json`
2. Translate all strings
3. Test in Home Assistant
4. Submit PR with translation

## Reporting Bugs

### Before Reporting

- Search existing issues
- Test with latest version
- Collect relevant information

### Bug Report Should Include

- Home Assistant version
- Integration version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Relevant logs
- Configuration (sanitized)

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the community

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Publishing private information
- Other unprofessional conduct

## Questions?

- Open a discussion on GitHub
- Check existing documentation
- Review closed issues

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Credited in release notes
- Thanked for their work!

Thank you for contributing to haFWCMA!
