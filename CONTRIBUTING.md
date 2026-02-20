# 🤝 Contributing to OpenCyclo Initiative

Thank you for your interest in contributing to the OpenCyclo Initiative! This project spans hardware, software, fluid dynamics, and biology — we welcome expertise from all domains.

---

## 📋 Before You Start

1. **Read the spec:** Familiarize yourself with [`docs/technical_specifications.md`](docs/technical_specifications.md) and the garage pilot guide [`docs/OPENCYCLO V0.1-ALPHA THE GARAGE HACKER PILOT.md`](docs/OPENCYCLO%20V0.1-ALPHA%20THE%20GARAGE%20HACKER%20PILOT.md).
2. **Check the plan:** Review [`TODO.md`](TODO.md) and [`COMPONENT_MATRIX.md`](COMPONENT_MATRIX.md) to see what's in progress and what's blocked.
3. **Open an issue first** for any non-trivial change to discuss your approach.

---

## 🏗️ Repository Structure

| Directory | License | Contents |
|---|---|---|
| `hardware/cad/` | CERN-OHL-S v2 | CAD files (STEP, STL) |
| `software/opencyclo_os/` | MIT | Python control scripts |
| `physics/openfoam/` | MIT | CFD simulation cases |
| `wetware/protocols/` | OpenMTA | Biological SOPs |

---

## 🐍 Software Conventions

### Python Style
- **Python 3.10+** required
- Follow [PEP 8](https://peps.python.org/pep-0008/) with a line length of 100 characters
- Use type hints for all public function signatures
- Use `async`/`await` for I/O-bound operations
- Docstrings: Google style

### File Naming
- Python modules: `snake_case.py`
- Configuration: `config.py` (single source of truth for constants)
- Tests: `tests/test_<module_name>.py`

### Dependencies
- Pin all versions in `requirements.txt`
- Separate dev dependencies in `requirements-dev.txt`
- Minimize external dependencies — prefer stdlib where possible

### Testing
- Use `pytest` + `pytest-asyncio`
- Mock all hardware I/O in tests (GPIO, I2C, camera)
- Tests must pass without physical hardware connected

---

## ⚙️ Hardware Contributions

- All CAD files must be in **parameterized `.STEP` (AP214)** format
- Include `.STL` exports at 0.05mm chord deviation for 3D-printable parts
- Document material specs and machining notes in the file header or accompanying README
- **Do not use** proprietary formats (`.f3d`, `.sldprt`, etc.) as primary files
- Use **Git LFS** for all binary CAD files (this is configured in `.gitattributes`)

---

## 🌊 CFD Contributions

- OpenFOAM **v2312** is the target version
- Provide complete case directories that run with a single `./Allrun` script
- Include mesh quality metrics in your PR description
- Document any solver changes in `VALIDATION_REPORT.md`

---

## 🧫 Wetware / Protocol Contributions

- Follow the existing SOP numbering scheme (`SOP-1XX`)
- Include safety warnings where relevant (especially for pH shock procedures)
- Protocols should be written for operators **without advanced microbiology degrees**
- Reference strain culture collection IDs (UTEX, CCAP, SAG, etc.)

---

## 🔀 Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Ensure tests pass: `pytest`
5. Update `TODO.md` and `COMPONENT_MATRIX.md` if applicable
6. Submit a Pull Request with a clear description of what changed and why

---

## 📜 Licensing

By contributing, you agree that your contributions will be licensed under:
- **CERN-OHL-S v2** for hardware contributions
- **MIT** for software contributions
- **OpenMTA** for wetware/protocol contributions
