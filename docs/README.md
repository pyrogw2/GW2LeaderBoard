# Documentation Index

Welcome to the GW2 WvW Leaderboard System documentation. This system provides comprehensive skill-based rankings for Guild Wars 2 World vs World combat using advanced statistical methods.

## Quick Start

- **New to the system?** Start with [Getting Started Guide](GETTING_STARTED.md)
- **Need to understand how it works?** Read the [System Overview](SYSTEM_OVERVIEW.md)  
- **Daily operations?** Check the [Daily Usage Guide](DAILY_USAGE.md)
- **Having problems?** See the [Troubleshooting Guide](TROUBLESHOOTING.md)

## Documentation Structure

### 📚 Core Documentation

#### [System Overview](SYSTEM_OVERVIEW.md)
**What it covers:**
- High-level architecture and data flow
- Component relationships and technologies used
- Scalability and performance characteristics
- Extension points for customization

**Read this if:**
- You want to understand how the system works
- You're planning to modify or extend the system
- You need to explain the system to others

#### [Getting Started Guide](GETTING_STARTED.md)
**What it covers:**
- Complete setup from scratch
- Step-by-step installation instructions
- Initial configuration and testing
- Verification procedures

**Read this if:**
- You're setting up the system for the first time
- You need to install on a new machine
- You're helping someone else get started

#### [Daily Usage Guide](DAILY_USAGE.md)
**What it covers:**
- Routine maintenance tasks
- Automated sync procedures
- Monitoring and health checks
- Deployment strategies

**Read this if:**
- You operate an existing system
- You want to automate regular tasks
- You need to monitor system health

### 🔧 Technical References

#### [Glicko System Documentation](GLICKO_SYSTEM.md)
**What it covers:**
- Detailed rating algorithm explanation
- Profession weighting configuration
- Adding new metrics and leaderboards
- Performance optimization techniques

**Read this if:**
- You want to understand the rating calculations
- You need to add new metrics or professions
- You want to tune rating parameters
- You're debugging rating issues

#### [Configuration Reference](CONFIGURATION.md)
**What it covers:**
- All configuration options and settings
- Environment variables and deployment configs
- Security and backup configurations
- Performance tuning parameters

**Read this if:**
- You need to customize system behavior
- You're deploying to production
- You want to optimize performance
- You need to integrate with other systems

#### [API and Database Reference](API_REFERENCE.md)
**What it covers:**
- Database schema and relationships
- Internal API functions and data structures
- Query examples and data export
- Performance considerations

**Read this if:**
- You're developing integrations
- You need to query the database directly
- You're extending the system functionality
- You want to export data for analysis

### 🛠️ Support Documentation

#### [Troubleshooting Guide](TROUBLESHOOTING.md)
**What it covers:**
- Common problems and solutions
- Diagnostic commands and procedures
- Error message explanations
- Prevention and monitoring strategies

**Read this if:**
- Something isn't working correctly
- You're getting error messages
- You want to prevent future issues
- You need to debug system problems

### 🚀 Development Documentation

#### [Contributing Guide](development/CONTRIBUTING.md)
**What it covers:**
- Code contribution guidelines
- Development setup and workflow
- Testing requirements and procedures
- Code style and quality standards

**Read this if:**
- You want to contribute to the project
- You're setting up a development environment
- You need to understand the development process
- You're writing tests or documentation

#### [Development Summary](development/DEVELOPMENT_SUMMARY.md)
**What it covers:**
- Recent development progress
- Feature implementation details
- Technical decisions and rationale
- Development timeline and milestones

**Read this if:**
- You want to understand recent changes
- You're continuing previous development work
- You need context for design decisions
- You're reviewing the development history

#### [Executable Build Guide](development/EXECUTABLE_BUILD.md)
**What it covers:**
- Creating standalone executables
- Build system configuration
- Cross-platform distribution
- GitHub Actions automation

**Read this if:**
- You need to create executable releases
- You're setting up automated builds
- You want to distribute the application
- You're working with the CI/CD pipeline

#### [AI Assistant Notes](development/GEMINI.md)
**What it covers:**
- AI assistant interaction history
- Development context and decisions
- Technical implementation notes
- Collaborative development insights

**Read this if:**
- You're working with AI assistants on the project
- You want to understand previous AI interactions
- You need context for development decisions
- You're continuing AI-assisted development

## Document Navigation

### By User Type

#### **System Administrators**
1. [System Overview](SYSTEM_OVERVIEW.md) - Understand the architecture
2. [Getting Started Guide](GETTING_STARTED.md) - Set up the system
3. [Configuration Reference](CONFIGURATION.md) - Configure for production
4. [Daily Usage Guide](DAILY_USAGE.md) - Maintain the system
5. [Troubleshooting Guide](TROUBLESHOOTING.md) - Handle issues

#### **Developers/Contributors**
1. [System Overview](SYSTEM_OVERVIEW.md) - Architecture and design
2. [API Reference](API_REFERENCE.md) - Technical details
3. [Glicko System](GLICKO_SYSTEM.md) - Rating algorithm
4. [Configuration Reference](CONFIGURATION.md) - All options
5. [Troubleshooting Guide](TROUBLESHOOTING.md) - Debug techniques

#### **End Users/Guild Leaders**
1. [System Overview](SYSTEM_OVERVIEW.md) - What the system does
2. [Getting Started Guide](GETTING_STARTED.md) - How to set it up
3. [Daily Usage Guide](DAILY_USAGE.md) - How to use it
4. [Troubleshooting Guide](TROUBLESHOOTING.md) - Fix common issues

### By Task

#### **Initial Setup**
1. [Getting Started Guide](GETTING_STARTED.md) - Complete walkthrough
2. [Configuration Reference](CONFIGURATION.md) - Available options
3. [Troubleshooting Guide](TROUBLESHOOTING.md) - Setup issues

#### **Adding New Features**
1. [Glicko System](GLICKO_SYSTEM.md) - Rating system details
2. [API Reference](API_REFERENCE.md) - Technical implementation
3. [Configuration Reference](CONFIGURATION.md) - Configuration changes

#### **Production Deployment**
1. [Configuration Reference](CONFIGURATION.md) - Production settings
2. [Daily Usage Guide](DAILY_USAGE.md) - Operational procedures
3. [Troubleshooting Guide](TROUBLESHOOTING.md) - Issue resolution

#### **Problem Solving**
1. [Troubleshooting Guide](TROUBLESHOOTING.md) - Primary resource
2. [API Reference](API_REFERENCE.md) - Technical debugging
3. [Configuration Reference](CONFIGURATION.md) - Settings review

## Related Files

### Main Project Files
- `README.md` - Project overview and quick start
- `parse_logs_enhanced.py` - Log parsing engine
- `glicko_rating_system.py` - Rating calculation system
- `generate_web_ui.py` - Web interface generator
- `sync_logs.py` - Automated log synchronization

### Configuration Files
- `sync_config.json` - Main configuration (created automatically)
- `.gitignore` - Git ignore patterns
- `requirements.txt` - Python dependencies (if exists)

### Generated Files
- `gw2_comprehensive.db` - SQLite database with all data
- `web_ui_*/` - Generated web interface directories
- `extracted_logs/` - Processed log data

## Getting Help

### Documentation Issues
If you find errors or gaps in this documentation:
1. Check if a more recent version exists
2. Verify you're looking at the right document for your task
3. Consult multiple documents for complete context

### System Issues
For problems with the system itself:
1. Start with the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Check the [Configuration Reference](CONFIGURATION.md) for settings
3. Review the [API Reference](API_REFERENCE.md) for technical details

### Feature Requests
For new features or enhancements:
1. Review [Glicko System](GLICKO_SYSTEM.md) for rating system changes
2. Check [System Overview](SYSTEM_OVERVIEW.md) for architectural constraints
3. Consult [API Reference](API_REFERENCE.md) for implementation details

## Contributing to Documentation

### Style Guidelines
- Use clear, concise language
- Include practical examples
- Provide step-by-step procedures
- Cross-reference related documents

### Structure Standards
- Start with purpose and scope
- Include quick reference sections
- Use consistent formatting
- Maintain table of contents

### Content Requirements
- Verify all examples work
- Include troubleshooting sections
- Provide configuration options
- Test procedures on clean systems

## Version Information

This documentation corresponds to the GW2 WvW Leaderboard System as of **July 2025**.

### Recent Updates
- Added down contribution tracking
- Enhanced automated sync capabilities
- Improved web interface with date filtering
- Added comprehensive profession support

### Compatibility
- Python 3.7+ required
- SQLite 3.15+ recommended
- Modern web browsers for UI
- Git for version control (optional)

---

For the most up-to-date information, always refer to the individual documentation files. This index provides navigation guidance but may not reflect the latest changes in each document.