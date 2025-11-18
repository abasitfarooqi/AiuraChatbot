# Others Folder

This folder contains non-essential files that don't affect the project's core functionality.

## Structure

- **documentation/** - All documentation files (.md) except the main README.md
- **reference_data/** - Reference data files (.rtf, .json) used for reference but not loaded by the application
- **test_scripts/** - Test scripts and test files
- **helper_scripts/** - Helper scripts for external integrations (expose tunnels, etc.)

## Note

These files are kept for reference but are not required for the application to run. The core application only needs:
- `backend/` - Backend code
- `frontend/` - Frontend code
- `config/` - Configuration files
- `data/` - Database files
- `models/` - Downloaded models
- `scripts/start.sh`, `scripts/stop.sh`, `scripts/restart.sh` - Essential scripts
- `requirements.txt` - Dependencies
- `rag_knowledge_base.json` - Active knowledge base
- `README.md` - Main documentation

